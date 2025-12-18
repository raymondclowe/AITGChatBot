version = "1.7.0"

# changelog
# 1.1.0 - llama3 using groq
# 1.2.0 - gpt4o support and set to default, increase max tokens to 4K for openai and 8K for Groq
# 1.3.0 - openrouter substring matches
# 1.4.0 - gpt4o-mini support and becomes the default
# 1.5.0 - openrouter buttons
# 1.6.0 - image in and out
# 1.7.0 - kiosk mode for locked-down dedicated instances

import requests
import base64
import os
import json
import hashlib
from datetime import datetime
import time
import configparser
import logging
import argparse
import signal
import sys

# Network exception types for consistent error handling
NETWORK_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.RequestException
)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    print(f"\nReceived signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Parse command line arguments for debug logging configuration
parser = argparse.ArgumentParser(description='AI Telegram Chat Bot')
parser.add_argument('--debug-log-file', type=str, default=None,
                    help='Path to the debug log file (default: ./logs/llm_debug.log)')
parser.add_argument('--debug-log-disabled', action='store_true',
                    help='Disable debug logging')
parser.add_argument('--log-chats', type=str, choices=['off', 'minimum', 'extended'], default=None,
                    help='Enable chat logging: off (no logging), minimum (text only), extended (text + attachments)')
args, _ = parser.parse_known_args()

# Configure debug logging for LLM requests/responses
# Priority: command line args > environment variables > defaults
# Default location is ./logs/llm_debug.log (creates logs/ directory if needed)
DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIR, 'llm_debug.log')

DEBUG_LOG_FILE = args.debug_log_file or os.environ.get('DEBUG_LOG_FILE', DEFAULT_LOG_FILE)
DEBUG_LOG_ENABLED = not args.debug_log_disabled and os.environ.get('DEBUG_LOG_ENABLED', 'true').lower() == 'true'

# Set up a dedicated logger for debug logging
debug_logger = logging.getLogger('llm_debug')
debug_logger.setLevel(logging.DEBUG)

if DEBUG_LOG_ENABLED:
    try:
        # Create the log directory if it doesn't exist
        log_dir = os.path.dirname(DEBUG_LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create file handler for debug logging
        file_handler = logging.FileHandler(DEBUG_LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        # Create formatter with timestamp
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        debug_logger.addHandler(file_handler)
        print(f"Debug logging enabled: {DEBUG_LOG_FILE}")
    except OSError as e:
        print(f"Warning: Could not set up debug logging to {DEBUG_LOG_FILE}: {e}")
        DEBUG_LOG_ENABLED = False


def truncate_for_debug(obj, max_length=15):
    """
    Truncate JSON values for debug logging.
    Preserves all keys but truncates string values to max_length characters.
    """
    if isinstance(obj, dict):
        return {k: truncate_for_debug(v, max_length) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [truncate_for_debug(v, max_length) for v in obj]
    elif isinstance(obj, str):
        if len(obj) > max_length:
            return obj[:max_length] + "..."
        return obj
    else:
        return obj


def log_debug(direction, endpoint, data):
    """
    Log request/response data to the debug log file.
    
    Args:
        direction: "REQUEST" or "RESPONSE"
        endpoint: The API endpoint URL
        data: The JSON data to log (will be truncated)
    """
    if not DEBUG_LOG_ENABLED:
        return
    
    truncated_data = truncate_for_debug(data)
    log_entry = f"{direction} to {endpoint}:\n{json.dumps(truncated_data, indent=2)}"
    debug_logger.debug(log_entry)

# Get the API keys from the environment variables
API_KEY = os.environ.get('API_KEY')
BOT_KEY = os.environ.get('BOT_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Kiosk mode configuration
# Settings are loaded from kiosk.conf file if it exists
# See kiosk.conf.example for configuration options
KIOSK_MODE = False
KIOSK_MODEL = 'gpt-4o-mini'
KIOSK_PROMPT_FILE = ''
KIOSK_INACTIVITY_TIMEOUT = 0
KIOSK_SYSTEM_PROMPT = ""

# Chat logging configuration
# Settings loaded from kiosk.conf file and command line
CHAT_LOG_LEVEL = 'off'  # off, minimum, extended
CHAT_LOG_DIRECTORY = './chat_logs'

def load_kiosk_config():
    """Load kiosk mode configuration from kiosk.conf file"""
    global KIOSK_MODE, KIOSK_MODEL, KIOSK_PROMPT_FILE, KIOSK_INACTIVITY_TIMEOUT, KIOSK_SYSTEM_PROMPT
    global CHAT_LOG_LEVEL, CHAT_LOG_DIRECTORY
    
    config_file = 'kiosk.conf'
    if not os.path.exists(config_file):
        return  # No config file, kiosk mode disabled
    
    try:
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        
        # Parse settings from [kiosk] section
        KIOSK_MODE = config.get('kiosk', 'enabled', fallback='false').lower() == 'true'
        KIOSK_MODEL = config.get('kiosk', 'model', fallback='gpt-4o-mini')
        KIOSK_PROMPT_FILE = config.get('kiosk', 'prompt_file', fallback='')
        KIOSK_INACTIVITY_TIMEOUT = config.getint('kiosk', 'inactivity_timeout', fallback=0)
        
        # Parse chat logging settings from [logging] section if present
        if config.has_section('logging'):
            CHAT_LOG_LEVEL = config.get('logging', 'log_chats', fallback='off').lower()
            CHAT_LOG_DIRECTORY = config.get('logging', 'log_directory', fallback='./chat_logs')
        
        print(f"Kiosk config: Loaded settings from {config_file}")
        
    except configparser.Error as e:
        print(f"ERROR: Failed to parse kiosk config file: {config_file}")
        print(f"  Error details: {e}")
        return
    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"ERROR: Could not read kiosk config file: {config_file}")
        print(f"  Error details: {e}")
        return

# Load kiosk configuration
load_kiosk_config()

# Apply command-line override for chat logging if provided
if args.log_chats is not None:
    CHAT_LOG_LEVEL = args.log_chats

# Validate and normalize chat log level
if CHAT_LOG_LEVEL not in ['off', 'minimum', 'extended']:
    print(f"WARNING: Invalid chat log level '{CHAT_LOG_LEVEL}', defaulting to 'off'")
    CHAT_LOG_LEVEL = 'off'

# Load system prompt from file if kiosk mode is enabled
if KIOSK_MODE and KIOSK_PROMPT_FILE:
    try:
        with open(KIOSK_PROMPT_FILE, 'r', encoding='utf-8') as f:
            KIOSK_SYSTEM_PROMPT = f.read().strip()
        print(f"Kiosk mode: Loaded system prompt from {KIOSK_PROMPT_FILE} ({len(KIOSK_SYSTEM_PROMPT)} chars)")
    except FileNotFoundError:
        print(f"ERROR: Kiosk prompt file not found: {KIOSK_PROMPT_FILE}")
        print(f"  Please create the file or update prompt_file in kiosk.conf.")
        print(f"  The bot will run without a system prompt until this is fixed.")
    except PermissionError:
        print(f"ERROR: Permission denied reading kiosk prompt file: {KIOSK_PROMPT_FILE}")
        print(f"  Please check file permissions and ensure the bot has read access.")
    except IOError as e:
        print(f"ERROR: Could not read kiosk prompt file: {KIOSK_PROMPT_FILE}")
        print(f"  Error details: {e}")
        print(f"  The bot will run without a system prompt until this is fixed.")

if KIOSK_MODE:
    print(f"🔒 KIOSK MODE ENABLED")
    print(f"   Model: {KIOSK_MODEL}")
    print(f"   System prompt: {'Loaded' if KIOSK_SYSTEM_PROMPT else 'Not set'}")
    print(f"   Inactivity timeout: {KIOSK_INACTIVITY_TIMEOUT}s" if KIOSK_INACTIVITY_TIMEOUT > 0 else "   Inactivity timeout: Disabled")

# Display chat logging status
if CHAT_LOG_LEVEL != 'off':
    print(f"📝 CHAT LOGGING ENABLED")
    print(f"   Level: {CHAT_LOG_LEVEL}")
    print(f"   Directory: {CHAT_LOG_DIRECTORY}")
    print(f"   ⚠️  Users will be notified that chats are being recorded")

# Chat logging helper functions
def get_chat_log_notification():
    """Get the notification message shown to users when logging is active"""
    if CHAT_LOG_LEVEL == 'off':
        return None
    return "⚠️ This chat is being recorded for training and service improvement purposes."

def get_username_for_logging(chat_id):
    """
    Get a sanitized username for logging purposes.
    Uses chat_id which is guaranteed to be a safe integer identifier.
    """
    # Use chat_id as the username - it's always a numeric ID from Telegram
    # Convert to string and use only alphanumeric characters and hyphens
    username = str(chat_id)
    # Additional safety: keep only alphanumeric and underscore (should already be safe)
    sanitized = ''.join(c if c.isalnum() or c in '-_' else '_' for c in username)
    # Ensure it's not empty and not a reserved name
    if not sanitized or sanitized in ('.', '..', 'CON', 'PRN', 'AUX', 'NUL'):
        sanitized = f'user_{sanitized}'
    return sanitized

def ensure_log_directory(chat_id):
    """
    Ensure the log directory for a chat exists and return the path.
    Returns None if logging is disabled or directory creation fails.
    """
    if CHAT_LOG_LEVEL == 'off':
        return None
    
    username = get_username_for_logging(chat_id)
    user_dir = os.path.join(CHAT_LOG_DIRECTORY, username)
    
    try:
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    except OSError as e:
        print(f"ERROR: Could not create chat log directory {user_dir}: {e}")
        return None

def log_chat_message(chat_id, role, text_content, image_data=None):
    """
    Log a chat message to file
    
    Args:
        chat_id: The Telegram chat ID
        role: 'user' or 'assistant'
        text_content: The text content of the message
        image_data: Optional image data (bytes) for extended logging
    """
    if CHAT_LOG_LEVEL == 'off':
        return
    
    try:
        # Ensure log directory exists
        user_dir = ensure_log_directory(chat_id)
        if not user_dir:
            return
        
        # Generate timestamps once for consistency across all operations
        now = datetime.now()
        timestamp_display = now.strftime('%Y-%m-%d %H:%M:%S')  # Human-readable format for log entries
        timestamp_safe = now.strftime('%Y-%m-%dT%H-%M-%S')  # Filesystem-safe format for filenames
        
        # Create a session-based log file (reuse same file for conversation)
        # Store the current log file in session data if session exists
        log_file = None
        if chat_id in session_data and 'log_file' in session_data[chat_id]:
            log_file = session_data[chat_id]['log_file']
        
        # If no log file yet, create a new one
        if not log_file:
            log_file = os.path.join(user_dir, f'chat_{timestamp_safe}.txt')
            # Store in session data if session exists (defensive check)
            if chat_id in session_data:
                session_data[chat_id]['log_file'] = log_file
        
        # Format and append the log entry
        log_entry = f"[{timestamp_display}] {role.upper()}: {text_content}\n"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # Handle image logging in extended mode
        if CHAT_LOG_LEVEL == 'extended' and image_data is not None:
            # Save image with same timestamp, use generic extension to preserve data
            image_filename = os.path.join(user_dir, f'image_{timestamp_safe}_{role}.bin')
            with open(image_filename, 'wb') as img_file:
                img_file.write(image_data)
            
            # Log reference to image file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp_display}] {role.upper()}: [IMAGE: {os.path.basename(image_filename)}]\n")
    
    except Exception as e:
        print(f"ERROR: Failed to log chat message: {e}")

# Set the URL for the API
OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'
ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

# list of the possible "model" values:
# gpt-3.5-turbo
# gpt-4-turbo
# gpt-4o
# gpt-4o-mini  # Add this line
# claude-3-opus-20240229
# claude-3-haiku-20240307
# openrouter:<model name>
# llama3-8b-8192
# llama3-70b-8192 (on groq)

# set starting values
session_data = {}

# default conversation max rounds is 4 which is double the previous version of the bot
DEFAULT_MAX_ROUNDS = 4


def get_default_model():
    """Get the default model based on kiosk mode setting"""
    if KIOSK_MODE:
        return KIOSK_MODEL
    return "gpt-4o-mini"


def initialize_session(chat_id):
    """Initialize a new session with proper defaults for kiosk or normal mode"""
    model = get_default_model()
    session = {
        'model_version': model,
        'CONVERSATION': [],
        'tokens_used': 0,
        'max_rounds': DEFAULT_MAX_ROUNDS,
        'last_activity': time.time()
    }
    
    # Set provider for openrouter models
    if model.startswith("openrouter:"):
        session['provider'] = 'openrouter'
    
    # Add system prompt for kiosk mode
    if KIOSK_MODE and KIOSK_SYSTEM_PROMPT:
        session['CONVERSATION'] = [
            {
                "role": "system",
                "content": [{"type": "text", "text": KIOSK_SYSTEM_PROMPT}]
            }
        ]
    
    # Set flag to show logging notification on first interaction
    session['notification_needed'] = True
    session_data[chat_id] = session
    return session


def check_inactivity_timeout(chat_id):
    """Check if session should be cleared due to inactivity. Returns True if cleared."""
    if not KIOSK_MODE or KIOSK_INACTIVITY_TIMEOUT <= 0:
        return False
    
    if chat_id not in session_data:
        return False
    
    last_activity = session_data[chat_id].get('last_activity', time.time())
    if time.time() - last_activity > KIOSK_INACTIVITY_TIMEOUT:
        # Clear conversation but keep session
        clear_context(chat_id)
        # Reset activity timestamp to prevent immediate re-clearing
        session_data[chat_id]['last_activity'] = time.time()
        return True
    return False


def update_activity(chat_id):
    """Update the last activity timestamp for a session"""
    if chat_id in session_data:
        session_data[chat_id]['last_activity'] = time.time()


def update_model_version(session_id, command):
    if command.lower() == "/gpt3":
        session_data[session_id]["model_version"] = "gpt-3.5-turbo"
    elif command.lower() == "/gpt4":
        session_data[session_id]["model_version"] = "gpt-4-turbo"
    elif command.lower() == "/gpt4o":
        session_data[session_id]["model_version"] = "gpt-4o"
    elif command.lower() == "/gpt4omini":  # Add this line
        session_data[session_id]["model_version"] = "gpt-4o-mini"  # Add this line
    elif command.lower() == "/claud3opus":
        session_data[session_id]["model_version"] = "claude-3-opus-20240229"
    elif command.lower() == "/claud3haiku":
        session_data[session_id]["model_version"] = "claude-3-haiku-20240307"
    elif command.lower().startswith('/openrouter') and len(command.split()) == 2: # Handle single match here
        model_substring = command.split()[1]
        matching_models = get_matching_models(model_substring)
        if len(matching_models) == 1:
            session_data[session_id]["model_version"] = "openrouter:" + matching_models[0]
            session_data[session_id]["provider"] = "openrouter"
    elif command.lower() == "/llama38b":
        session_data[session_id]["model_version"] = "llama3-8b-8192"
    elif command.lower() == "/llama370b":
        session_data[session_id]["model_version"] = "llama3-70b-8192"
    print(f"Debug: Session data after model update: {session_data[session_id]}")


def clear_context(chat_id):
    """Clear conversation context, preserving system prompt in kiosk mode"""
    if KIOSK_MODE and KIOSK_SYSTEM_PROMPT:
        # Preserve the system prompt in kiosk mode
        session_data[chat_id]['CONVERSATION'] = [
            {
                "role": "system",
                "content": [{"type": "text", "text": KIOSK_SYSTEM_PROMPT}]
            }
        ]
    else:
        session_data[chat_id]['CONVERSATION'] = []
    
    # Set flag to show logging notification after context clear
    session_data[chat_id]['notification_needed'] = True


def get_reply(message, image_data_64, session_id):
    note = ""
    response_text = ""
    if not session_data[session_id]:
        initialize_session(session_id)
    has_image = False
    # check the length of the existing conversation, if it is too long (with messages more than double the max rounds, then trim off until it is within the limit of rounds. one round is one user and one assistant text.
    max_messages = session_data[session_id]["max_rounds"] * 2
    conversation = session_data[session_id]["CONVERSATION"]
    
    # When trimming, preserve system prompt if present (kiosk mode)
    if len(conversation) > max_messages:
        # Check if first message is a system prompt
        if conversation and conversation[0].get("role") == "system":
            # Keep system prompt + last max_messages
            session_data[session_id]["CONVERSATION"] = [conversation[0]] + conversation[-(max_messages):]
        else:
            session_data[session_id]["CONVERSATION"] = conversation[-max_messages:]

    # Add the new user message to the conversation
    new_user_message = [
        {
            "role": "user",
            "content": [{"type": "text", "text": message}],
            # "datetime": datetime.now(),
        }
    ]
    user_image_data = None
    if image_data_64:  # If there's a new image, include it in the user's message
        has_image = True
        image_content_item = {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data_64}"},
        }
        new_user_message[0]["content"].append(image_content_item)
        # Store image data for logging
        user_image_data = base64.b64decode(image_data_64)
    
    # Log the user message
    log_chat_message(session_id, 'user', message, user_image_data)
    
    # Update the conversation with the new user message
    session_data[session_id]["CONVERSATION"].extend(new_user_message)

    # Construct the payload with the entire conversation so far
    if not has_image:
        for message in session_data[session_id]["CONVERSATION"]:
            for content_obj in message.get("content", []):
                if content_obj.get("type") == "image_url":
                    has_image = True
                    break

    # print (f"has_image: {has_image}")

    model = session_data[session_id]["model_version"]
    endpoint_url = None  # Track which endpoint is used for response logging



    if model.startswith("gpt"):
        payload = {
            "model": model,
            "max_tokens": 4000,
            "messages": session_data[session_id]["CONVERSATION"],
        }

        endpoint_url = OPENAI_API_URL
        log_debug("REQUEST", endpoint_url, payload)
        raw_response = requests.post(
            OPENAI_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            },
            json=payload,
            timeout=120  # 2 minute timeout for LLM API calls
        )
    elif model.startswith("openrouter"):
        # if an openrouter model then strip of the string "openrouter:" from the beginning
        # model = model[11:]
        payload = {
            "model": model[11:],
            "max_tokens": 4000,
            "messages": session_data[session_id]["CONVERSATION"],
        }

        endpoint_url = OPENROUTER_API_URL
        log_debug("REQUEST", endpoint_url, payload)
        raw_response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/raymondclowe/AITGChatBot",
                "X-Title": "AITGChatBot",
            },
            json=payload,
            timeout=120  # 2 minute timeout for LLM API calls
        )

    elif model.startswith("claud"):
        anthropic_payload = {
            "model": model,
            "max_tokens": 3000,
            "messages": [],
        }

        for message in session_data[session_id]["CONVERSATION"]:
            anthropic_message = {"role": message["role"], "content": []}

            for content in message["content"]:
                if content["type"] == "text":
                    anthropic_message["content"].append({"type": "text", "text": content["text"]})
                elif content["type"] == "image_url":
                    image_url = content["image_url"]["url"]
                    if image_url.startswith("data:image/jpeg;base64,"):
                        image_data_64 = image_url[len("data:image/jpeg;base64,"):]
                    else:
                        # If the image URL is not base64-encoded, you'll need to fetch and encode it
                        try:
                            image_response = requests.get(image_url, timeout=30)
                            image_response.raise_for_status()
                            image_data_64 = base64.b64encode(image_response.content).decode("utf-8")
                        except NETWORK_EXCEPTIONS as e:
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error downloading image from URL: {e}")
                            continue  # Skip this image if download fails

                    anthropic_message["content"].append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data_64
                        }
                    })

            anthropic_payload["messages"].append(anthropic_message)

        endpoint_url = ANTHROPIC_API_URL
        log_debug("REQUEST", endpoint_url, anthropic_payload)
        raw_response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=anthropic_payload,
            timeout=120  # 2 minute timeout for LLM API calls
        )

    elif model.startswith("llama3"):
        if has_image:
            session_data[session_id]["model_version"] = model
            note = " (image included)"
        else:
            note = ""
            
        groq_payload = {
            "model": model,
            "max_tokens": 8000,
            "messages": [],
        }
        groq_messages = []
        for message in session_data[session_id]["CONVERSATION"]:
            groq_message = {}
            groq_message["role"] = message["role"]
            groq_message["content"] = ""
            for content in message["content"]:
                if content["type"] == "text":
                    groq_message["content"] = content["text"]
                    break
            groq_messages.append(groq_message)
            
        groq_payload["messages"] = groq_messages
        
        endpoint_url = GROQ_API_URL
        log_debug("REQUEST", endpoint_url, groq_payload)
        raw_response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": "Bearer " + GROQ_API_KEY,                
                "content-type": "application/json",
            },
            json=groq_payload,
            timeout=120  # 2 minute timeout for LLM API calls
        )

    # Handle the response
    raw_json = raw_response.json()
    
    # Log the response with truncated values
    log_debug("RESPONSE", endpoint_url, raw_json)

    def truncate_json(obj, max_length=500):
        if isinstance(obj, dict):
            return {k: truncate_json(v, max_length) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [truncate_json(v, max_length) for v in obj]
        elif isinstance(obj, str):
            if len(obj) > max_length:
                return obj[:max_length] + "... [truncated] ..."
            else:
                return obj
        else:
            return obj

    print("Raw JSON response from AI backend (truncated):")
    print(json.dumps(truncate_json(raw_json), indent=4 ))

    if "error" in raw_json:
        print("Error detected in AI backend response.")
        error_info = raw_json.get('error', {})
        error_message = error_info.get('message', 'Unknown error')
        error_type = error_info.get('type', '')
        error_code = error_info.get('code', '')
        
        # Build a detailed error message
        error_parts = [f"API Error: {error_message}"]
        if error_type:
            error_parts.append(f"Type: {error_type}")
        if error_code:
            error_parts.append(f"Code: {error_code}")
        
        return "\n".join(error_parts) + note, 0

    # Update tokens used and process the response based on the model used
    tokens_used = session_data[session_id]["tokens_used"]
    images_received = []  # Initialize for all models
    seen_image_hashes = set()  # Track image hashes to avoid duplicates
    seen_image_sizes = []  # Track image sizes for near-duplicate detection

    # Helper function to add image without duplicates
    def add_image_if_unique(image_data, mime_type):
        image_hash = hashlib.sha256(image_data).hexdigest()
        if image_hash in seen_image_hashes:
            return False
        
        # Conservative near-duplicate detection: skip images within 0.1% size of existing ones
        # This catches cases where providers return the same image with slightly different encoding
        # (e.g., 879090 bytes vs 879136 bytes = 0.0052% difference)
        # Using 0.1% threshold to be very conservative - prefer showing too many images
        image_size = len(image_data)
        for seen_size in seen_image_sizes:
            if seen_size > 0:  # Avoid division by zero
                size_diff_ratio = abs(image_size - seen_size) / seen_size
                if size_diff_ratio < 0.001:  # Within 0.1% size difference
                    print(f"Skipped near-duplicate image: {image_size} bytes (similar to {seen_size} bytes, diff={size_diff_ratio:.4%})")
                    return False
        
        seen_image_hashes.add(image_hash)
        seen_image_sizes.append(image_size)
        images_received.append((image_data, mime_type))
        return True
    
    # Helper function to extract and add image from a data URL
    def process_image_url(image_url, source_name):
        """
        Extract and add image from a data URL.
        
        Args:
            image_url: The data URL string (e.g., "data:image/png;base64,...")
            source_name: Description of where the image came from (for logging)
            
        Returns:
            True if image was successfully added, False otherwise
        """
        if not image_url.startswith("data:image/"):
            print(f"Non-data image URL in {source_name}: {image_url}")
            return False
        try:
            header, data = image_url.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
            image_data = base64.b64decode(data)
            if add_image_if_unique(image_data, mime_type):
                print(f"Added image from {source_name}: {len(image_data)} bytes, {mime_type}")
                return True
            else:
                print(f"Skipped duplicate image from {source_name}")
                return False
        except Exception as e:
            print(f"Error processing image from {source_name}: {e}")
            return False
    
    if model.startswith("gpt") or model.startswith("openrouter"):
        tokens_used += raw_json["usage"]["total_tokens"]
        
        # Handle multipart responses (text + images)
        if raw_json["choices"]:
            message = raw_json["choices"][0]["message"]
            message_content = message["content"]
            
            # First, check for images in the dedicated images array (OpenRouter canonical format)
            # Per OpenRouter docs: images should be in a separate "images" array
            # We check this FIRST and prefer it over content array when valid entries exist.
            # 
            # Handle 4 cases for duplicate images from different providers:
            # 1. No image data - show nothing
            # 2. Image data only in images[] - show only those images
            # 3. Image data in another part of response but not in images[] - show that data
            # 4. Images in BOTH parts of response - show only ones from images[] list
            #
            # Note: Some providers (AI Studio) return non-byte-identical copies of the same
            # image in both locations. We prefer images[] when it has valid data URLs to
            # avoid duplicate images, even if they have different byte content/encoding.
            images_from_array = False
            if message.get("images"):
                for image_item in message["images"]:
                    if image_item.get("type") == "image_url" and image_item.get("image_url"):
                        image_url = image_item["image_url"].get("url", "")
                        # Only prefer images[] if it has valid data URLs (starts with data:image/)
                        # This ensures we fall back to content list if images[] has invalid URLs
                        if image_url.startswith("data:image/"):
                            images_from_array = True
                        process_image_url(image_url, "images array")
            
            # Check if content is a list (multipart) or string (text only)
            if isinstance(message_content, list):
                response_parts = []
                
                for part in message_content:
                    if part.get("type") == "text" and part.get("text"):
                        response_parts.append(part["text"])
                    elif part.get("type") == "image_url" and part.get("image_url"):
                        # Only process images from content if we didn't already get images from the images array
                        # This prevents duplicate images when model returns same image in both locations
                        if images_from_array:
                            print(f"Skipping image from content list (already have images from images array)")
                            continue
                        # Handle image responses
                        image_url = part["image_url"].get("url", "")
                        # Add non-data URLs as text links (process_image_url returns False for non-data URLs)
                        if not process_image_url(image_url, "content list") and not image_url.startswith("data:image/"):
                            response_parts.append(f"[Image URL: {image_url}]")
                    elif part.get("inline_data"):
                        # Handle Gemini-style inline data - only if no images from array
                        if images_from_array:
                            print(f"Skipping inline_data (already have images from images array)")
                            continue
                        inline_data = part["inline_data"]
                        mime_type = inline_data.get("mimeType", "unknown")
                        data = inline_data.get("data", "")
                        try:
                            image_data = base64.b64decode(data)
                            if add_image_if_unique(image_data, mime_type):
                                print(f"Added image from inline_data: {len(image_data)} bytes, {mime_type}")
                        except Exception as e:
                            response_parts.append(f"[Unable to process inline data: {e}]")
                
                # Only include actual text content, not placeholder messages
                response_text = "\n".join(response_parts) if response_parts else ""
                    
            else:
                # Simple string response (OpenRouter format: text in content, images in separate array)
                response_text = message_content.strip() if message_content else ""
            
            # Send any images to Telegram
            for image_data, mime_type in images_received:
                send_image_to_telegram(session_id, image_data, mime_type)
        else:
            response_text = "API error: No response choices returned." + note
            
        print(f"Response text for gpt or openrouter model: {response_text}")
    elif model.startswith("claud"):
        tokens_used += (
            raw_json["usage"]["prompt_tokens"] + raw_json["usage"]["completion_tokens"]
        )
        print("Debug: 'choices' field in raw_json:")
        print(raw_json.get("choices"))
        if raw_json.get("choices"):
            print("Debug: First item in 'choices':")
            print(raw_json["choices"][0])
            if raw_json["choices"][0].get("message"):
                print("Debug: 'message' field in first item of 'choices':")
                print(raw_json["choices"][0]["message"])
                if raw_json["choices"][0]["message"].get("content"):
                    print("Debug: 'content' field in 'message':")
                    print(raw_json["choices"][0]["message"]["content"])
        if "choices" in raw_json and "message" in raw_json["choices"][0] and "content" in raw_json["choices"][0]["message"]:
            response_text = (
                raw_json["choices"][0]["message"]["content"].strip() + note
            )
        else:
            response_text = "API error occurred." + note
        print(f"Response text for claud model: {response_text}")
    elif model.startswith("llama3"):
        tokens_used += raw_json["usage"]["total_tokens"]
        response_text = (
            raw_json["choices"][0]["message"]["content"].strip()
            if raw_json["choices"]
            else "API error occurred." + note
        )
        print(f"Response text for llama3 model: {response_text}")

    # Update the conversation with the assistant response
    assistant_content = [{"type": "text", "text": response_text}]
    
    # Add any generated images to the conversation history so they can be referenced
    if images_received:
        for image_data, mime_type in images_received:
            # Convert image back to base64 data URL format for conversation history
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:{mime_type};base64,{image_b64}"
            assistant_content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
    
    assistant_response = [
        {
            "role": "assistant",
            "content": assistant_content,
            # "datetime": datetime.now(),
        }
    ]
    session_data[session_id]["CONVERSATION"].extend(assistant_response)
    session_data[session_id]["tokens_used"] = tokens_used
    
    # Log the assistant response (text first, then images separately)
    log_chat_message(session_id, 'assistant', response_text, None)
    
    # Log all images separately if in extended mode
    if images_received and CHAT_LOG_LEVEL == 'extended':
        for idx, (image_data, mime_type) in enumerate(images_received):
            # Log each image separately with index if multiple
            image_note = f"[Image {idx+1} of {len(images_received)}]" if len(images_received) > 1 else "[Image]"
            log_chat_message(session_id, 'assistant', image_note, image_data)

    # Optional: print the session_data for debugging
    # print(json.dumps(session_data[session_id], indent=4))

    return response_text, tokens_used


# Function to download the image given the file path
def download_image(file_path):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            file_url = f"https://api.telegram.org/file/bot{BOT_KEY}/{file_path}"
            response = requests.get(file_url, timeout=60)  # Timeout for image download
            response.raise_for_status()
            return response.content
        except NETWORK_EXCEPTIONS as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error downloading image (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Failed to download image after {max_retries} attempts")
                return None


# get list from https://openrouter.ai/api/v1/models
def list_openrouter_models_as_message():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(f"https://openrouter.ai/api/v1/models", timeout=30)
            response.raise_for_status()
            openRouterModelList = response.json()['data']
            capabilities = get_openrouter_model_capabilities()
            
            model_list = "Model ID : Model Name : Image Input : Image Output\n\n"
            for model in openRouterModelList:  # include id, name, and image capabilities
                model_id = model['id']
                model_name = model['name']
                caps = capabilities.get(model_id, {})
                
                # Image capability indicators
                img_in = "📷 Yes" if caps.get('image_input', False) else "No"
                img_out = "🎨 Yes" if caps.get('image_output', False) else "No"
                
                model_list += f"{model_id} : {model_name} : {img_in} : {img_out}\n"
            
            model_list += "\n\n📷 = Image input (vision analysis)\n🎨 = Image output (generation)\n"
            model_list += "Or choose from the best ranked at https://openrouter.ai/rankings"
            return model_list
        except NETWORK_EXCEPTIONS as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error fetching OpenRouter models (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                return "⚠️ Failed to fetch model list due to network issues. Please try again later."


# get list from https://openrouter.ai/api/v1/models
def list_openrouter_models_as_list():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(f"https://openrouter.ai/api/v1/models", timeout=30)
            response.raise_for_status()
            openRouterModelList = response.json()['data']
            model_list = []
            for model in openRouterModelList:
                model_list.append(model['id'])
            return model_list
        except NETWORK_EXCEPTIONS as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error fetching OpenRouter models list (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                return []  # Return empty list on failure

# Cache for model capabilities
_model_capabilities_cache = None
_cache_timestamp = 0
CACHE_DURATION = 3600  # 1 hour in seconds

def get_openrouter_model_capabilities():
    """Fetch and cache OpenRouter model capabilities"""
    global _model_capabilities_cache, _cache_timestamp
    
    current_time = time.time()
    
    # Return cached data if still valid
    if _model_capabilities_cache and (current_time - _cache_timestamp) < CACHE_DURATION:
        return _model_capabilities_cache
    
    try:
        # Try with API key first
        api_key = os.environ.get('COPILOT_DEV_KEY') or os.environ.get('OPENROUTER_API_KEY')
        headers = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
            
        response = requests.get('https://openrouter.ai/api/v1/models', headers=headers, timeout=30)
        
        if response.status_code == 200:
            models_data = response.json()
            capabilities = {}
            
            if 'data' in models_data:
                for model in models_data['data']:
                    model_id = model['id']
                    arch = model.get('architecture', {})
                    input_mods = arch.get('input_modalities', [])
                    output_mods = arch.get('output_modalities', [])
                    
                    capabilities[model_id] = {
                        'name': model.get('name', model_id),
                        'description': model.get('description', ''),
                        'image_input': 'image' in input_mods,
                        'image_output': 'image' in output_mods,
                        'context_length': model.get('context_length', 0),
                        'pricing': model.get('pricing', {})
                    }
                
                _model_capabilities_cache = capabilities
                _cache_timestamp = current_time
                return capabilities
        
        # Fallback: pattern matching if API fails
        return get_openrouter_capabilities_fallback()
        
    except NETWORK_EXCEPTIONS as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Network error fetching model capabilities: {e}")
        return get_openrouter_capabilities_fallback()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error fetching model capabilities: {e}")
        return get_openrouter_capabilities_fallback()

def get_openrouter_capabilities_fallback():
    """Fallback to pattern matching when API is unavailable"""
    try:
        response = requests.get('https://openrouter.ai/api/v1/models', timeout=30)
        response.raise_for_status()
        models_data = response.json()
        capabilities = {}
        
        if 'data' in models_data:
            for model in models_data['data']:
                model_id = model['id']
                model_name = model.get('name', '').lower()
                model_desc = model.get('description', '').lower()
                
                # Pattern matching for vision capabilities
                vision_patterns = ['vision', 'image', 'multimodal', 'visual', 'photo', 'picture']
                image_gen_patterns = ['image-preview', 'generate', 'creation']
                
                # Check for vision in name, description, or known model patterns
                has_vision = (
                    any(pattern in model_name for pattern in vision_patterns) or
                    any(pattern in model_desc for pattern in vision_patterns) or
                    any(pattern in model_id.lower() for pattern in [
                        'gpt-4o', 'gpt-4-vision', 'gpt-4-turbo', 'claude-3', 'gemini', 
                        'llava', 'cogvlm', 'qwen-vl', 'internvl', 'minicpm-v'
                    ])
                )
                
                has_image_gen = (
                    any(pattern in model_id.lower() for pattern in image_gen_patterns) or
                    'image-preview' in model_id.lower()
                )
                
                capabilities[model_id] = {
                    'name': model.get('name', model_id),
                    'description': model.get('description', ''),
                    'image_input': has_vision,
                    'image_output': has_image_gen,
                    'context_length': model.get('context_length', 0),
                    'pricing': model.get('pricing', {})
                }
            
            return capabilities
    except NETWORK_EXCEPTIONS as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Network error in fallback pattern matching: {e}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in fallback pattern matching: {e}")
    
    return {}

def get_model_capability_message(model_id):
    """Get image capability message for a model"""
    capabilities = get_openrouter_model_capabilities()
    caps = capabilities.get(model_id, {})
    
    capability_parts = []
    if caps.get('image_input', False):
        capability_parts.append("📷 Image input (vision analysis)")
    if caps.get('image_output', False):
        capability_parts.append("🎨 Image output (generation)")
    
    if capability_parts:
        return f"🖼️ This model supports: {', '.join(capability_parts)}"
    else:
        return ""

def get_matching_models(substring):
    all_models = list_openrouter_models_as_list()
    matching_models = [model for model in all_models if substring in model]
    return matching_models


# Long polling loop
def long_polling():
    offset = 0
    consecutive_errors = 0
    max_backoff = 300  # Maximum backoff time in seconds (5 minutes)
    
    while not shutdown_requested:
        try:
            # Long polling request to get new messages with timeout
            response = requests.get(
                f"https://api.telegram.org/bot{BOT_KEY}/getUpdates?timeout=100&offset={offset}",
                timeout=120  # Add timeout to prevent hanging (100s server timeout + 20s buffer)
            )
            
            # Check for HTTP errors
            response.raise_for_status()

            # presume the response is json and pretty print it with nice colors and formatting
            # print(response.json(), indent=4, sort_dicts=False)

            # Parse and validate response
            response_data = response.json()
            result_list = response_data.get('result', [])
            if not result_list:
                # Reset error counter on successful empty response
                consecutive_errors = 0
                continue

            # Get the latest message and update the offset
            latest_message = result_list[-1]
            offset = latest_message['update_id'] + 1
            
            # Reset error counter on successful message retrieval
            consecutive_errors = 0

        except requests.exceptions.Timeout as e:
            consecutive_errors += 1
            backoff_time = min(2 ** consecutive_errors, max_backoff)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Timeout getting updates (attempt {consecutive_errors}): {e}")
            print(f"Waiting {backoff_time} seconds before retry...")
            time.sleep(backoff_time)
            continue
        except requests.exceptions.ConnectionError as e:
            consecutive_errors += 1
            backoff_time = min(2 ** consecutive_errors, max_backoff)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Network connection error (attempt {consecutive_errors}): {e}")
            print(f"Waiting {backoff_time} seconds before retry...")
            time.sleep(backoff_time)
            continue
        except requests.exceptions.RequestException as e:
            consecutive_errors += 1
            backoff_time = min(2 ** consecutive_errors, max_backoff)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Request error (attempt {consecutive_errors}): {e}")
            print(f"Waiting {backoff_time} seconds before retry...")
            time.sleep(backoff_time)
            continue
        except Exception as e:
            consecutive_errors += 1
            backoff_time = min(2 ** consecutive_errors, max_backoff)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error getting response on line {e.__traceback__.tb_lineno} (attempt {consecutive_errors}): {e}")
            print(f"Waiting {backoff_time} seconds before retry...")
            time.sleep(backoff_time)
            continue

        try:

            # Check if we have a message or callback query
            if 'message' in latest_message:
                message_text = latest_message['message'].get('text', '')  # Use get() with a default value of ''
                chat_id = latest_message['message']['chat']['id']
            elif 'callback_query' in latest_message:
                # Handle callback query from inline keyboard
                callback_query = latest_message['callback_query']
                chat_id = callback_query['message']['chat']['id']
                selected_model = callback_query['data']
                
                # Block model changes in kiosk mode
                if KIOSK_MODE:
                    send_message(chat_id, "🔒 Kiosk mode: Model selection is locked.")
                    try:
                        requests.post(f"https://api.telegram.org/bot{BOT_KEY}/answerCallbackQuery", json={
                            "callback_query_id": callback_query['id']
                        }, timeout=30)
                    except NETWORK_EXCEPTIONS as e:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error answering callback query: {e}")
                    continue
                
                # Update the model version
                session_data[chat_id]["model_version"] = "openrouter:" + selected_model
                session_data[chat_id]["provider"] = "openrouter"
                
                # Send confirmation message with capabilities
                capability_msg = get_model_capability_message(selected_model)
                base_msg = f"Model has been changed to {selected_model}"
                if capability_msg:
                    full_msg = f"{base_msg}\n{capability_msg}"
                else:
                    full_msg = base_msg
                send_message(chat_id, full_msg)
                
                # Acknowledge the callback query
                try:
                    requests.post(f"https://api.telegram.org/bot{BOT_KEY}/answerCallbackQuery", json={
                        "callback_query_id": callback_query['id']
                    }, timeout=30)
                except NETWORK_EXCEPTIONS as e:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error answering callback query: {e}")
                continue
            else:
                continue

            # if the message_text length is near the limit then maybe this is a truncated message
            # so we need to get the rest of the message
            if len(message_text) > 3000:
                # fast loop to look for any additional messages, down side of this is it adds at least one second
                while True:
                    try:
                        additional_response = requests.get(
                            f"https://api.telegram.org/bot{BOT_KEY}/getUpdates?timeout=1&offset={offset}",
                            timeout=5  # Short timeout for additional message check
                        )
                        additional_response.raise_for_status()
                        if not additional_response.json()['result']:
                            break
                        else:
                            additional_latest_message = additional_response.json()['result'][-1]
                            message_text += additional_latest_message['message']['text']
                            offset = additional_latest_message['update_id'] + 1
                            # after having got this additional text we loop because there might be more
                    except NETWORK_EXCEPTIONS as e:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error getting additional message text: {e}")
                        break  # Stop trying to get additional messages on error


            # check in the session data if there is a key with this chat_id, if not then initialize an empty one
            if chat_id not in session_data:  # doing it now because we may have to accept setting model version
                initialize_session(chat_id)
            
            # Update activity timestamp and check for inactivity timeout (kiosk mode)
            if check_inactivity_timeout(chat_id):
                send_message(chat_id, "⏰ Your session was cleared due to inactivity.")
                # Show logging notification after timeout clear
                notification = get_chat_log_notification()
                if notification:
                    send_message(chat_id, notification)

        except Exception as e:
            print(f"Error reading last message on line {e.__traceback__.tb_lineno}: {e}")
            continue

        try:

            # implement a /help command that outputs brief explanation of commands
            if message_text.startswith('/help'):
                if KIOSK_MODE:
                    reply_text = "🔒 KIOSK MODE\n\n"
                    reply_text += "This chatbot is running in kiosk mode with locked settings.\n\n"
                    reply_text += "Available commands:\n"
                    reply_text += "/help - this help message\n"
                    reply_text += "/clear - clear the conversation context\n"
                    reply_text += "/status - view current chatbot status\n\n"
                    reply_text += "All other settings (model, prompt, etc.) are locked by the administrator.\n"
                    reply_text += "Simply type your message or send an image to chat!"
                else:
                    reply_text = "Commands:\n"
                    reply_text += "/help - this help message\n"
                    reply_text += "/clear - clear the context\n"
                    reply_text += "/maxrounds <n> - set the max rounds of conversation\n"
                    reply_text += "/gpt3 - set the model to gpt3\n"
                    reply_text += "/gpt4 - set the model to gpt-4-turbo\n"
                    reply_text += "/gpt4o - set the model to gpt-4o\n"
                    reply_text += "/gpt4omini - set the model to gpt-4o-mini\n"
                    reply_text += "/claud3opus - set the model to Claud 3 Opus\n"
                    reply_text += "/claud3haiku - set the model to Claud 3 Haiku\n"
                    reply_text += "/llama38b - set the model to Llama 3 8B\n"
                    reply_text += "/llama370b - set the model to Llama 3 70B\n"
                    reply_text += "/listopenroutermodels - list all openrouter models with image capabilities\n"
                    reply_text += "/openrouter <model id> - set the model to the model with the given id\n"
                    reply_text += "/status - get the chatbot status, current model, current max rounds, current conversation length\n\n"
                    reply_text += "📷 Image Features:\n"
                    reply_text += "• Send images with text to vision-capable models for analysis\n"
                    reply_text += "• Models with 📷 support image input (vision)\n"
                    reply_text += "• Models with 🎨 support image output (generation)\n"
                    reply_text += "• OpenRouter models automatically support images when capable"

                send_message(chat_id, reply_text)
                continue  # Skip the rest of the processing loop

            if message_text.startswith('/status'):
                current_model = session_data[chat_id]['model_version']
                
                # Show kiosk mode indicator at the top
                if KIOSK_MODE:
                    reply_text = "🔒 KIOSK MODE ACTIVE\n\n"
                else:
                    reply_text = ""
                
                reply_text += f"Model: {current_model}\n"
                reply_text += f"Provider: {session_data[chat_id].get('provider', 'Not set')}\n"
                
                # Show image capabilities for OpenRouter models
                if current_model.startswith("openrouter:"):
                    model_id = current_model[11:]  # Remove "openrouter:" prefix
                    capability_msg = get_model_capability_message(model_id)
                    if capability_msg:
                        reply_text += f"Image capabilities: {capability_msg.replace('🖼️ This model supports: ', '')}\n"
                    else:
                        reply_text += "Image capabilities: None\n"
                elif any(current_model.startswith(prefix) for prefix in ["gpt-4o", "gpt-4-turbo", "claude-3"]):
                    reply_text += "Image capabilities: 📷 Image input (vision)\n"
                else:
                    reply_text += "Image capabilities: None\n"
                
                reply_text += f"Max rounds: {session_data[chat_id]['max_rounds']}\n"
                reply_text += f"Conversation length: {len(session_data[chat_id]['CONVERSATION'])}\n"
                reply_text += f"Chatbot version: {version}\n"
                
                # Show kiosk-specific info
                if KIOSK_MODE:
                    reply_text += "\n🔒 Settings are locked by administrator"
                    if KIOSK_INACTIVITY_TIMEOUT > 0:
                        reply_text += f"\n⏰ Inactivity timeout: {KIOSK_INACTIVITY_TIMEOUT}s"
                
                # Show chat logging status
                if CHAT_LOG_LEVEL != 'off':
                    reply_text += f"\n\n📝 Chat logging: {CHAT_LOG_LEVEL}"
                
                send_message(chat_id, reply_text)
                
                # Show logging notification if active
                notification = get_chat_log_notification()
                if notification:
                    send_message(chat_id, notification)
                continue

            if message_text.startswith('/maxrounds'):
                # Block maxrounds changes in kiosk mode (but allow viewing)
                if len(message_text.split()) == 1:
                    reply_text = f"Max rounds is currently set to {session_data[chat_id]['max_rounds']}" 
                    send_message(chat_id, reply_text)
                    continue
                
                if KIOSK_MODE:
                    send_message(chat_id, "🔒 Kiosk mode: Max rounds setting is locked.")
                    continue

                max_rounds = DEFAULT_MAX_ROUNDS
                try:
                    if len(message_text.split()) > 1:
                        max_rounds = int(message_text.split()[1])
                except ValueError:
                    max_rounds = DEFAULT_MAX_ROUNDS
                
                if max_rounds < 1:
                    max_rounds = DEFAULT_MAX_ROUNDS
                
                session_data[chat_id]['max_rounds'] = max_rounds
                reply_text = f"Max rounds set to {max_rounds}"
                send_message(chat_id, reply_text)
                continue  

            # Check for command to clear context
            if message_text.startswith('/clear'):
                clear_context(chat_id)
                reply_text = f"Context cleared"
                send_message(chat_id, reply_text)
                # Show logging notification after clear
                notification = get_chat_log_notification()
                if notification:
                    send_message(chat_id, notification)
                continue  # Skip the rest of the processing loop

            # Handle listopenroutermodels command, query live list from https://openrouter.ai/api/v1/models and respond in a text format message
            if message_text.startswith('/listopenroutermodels'):
                if KIOSK_MODE:
                    send_message(chat_id, "🔒 Kiosk mode: Model listing is not available.")
                    continue
                reply_text = list_openrouter_models_as_message()
                send_message(chat_id, reply_text)
                continue  # Skip the rest of the processing loop
                
            # Handle /openrouter command in long_polling
            if message_text.startswith("/openrouter"):
                if KIOSK_MODE:
                    send_message(chat_id, "🔒 Kiosk mode: Model selection is locked.")
                    continue
                if len(message_text.split()) == 1:
                    send_message(chat_id, "Please specify a model name after the command")
                    continue
                model_substring = message_text.split()[1]
                matching_models = get_matching_models(model_substring)
                if len(matching_models) == 0:
                    send_message(chat_id, f"Model name {model_substring} not found in list of models")
                    continue
                elif len(matching_models) == 1:
                    model_id = matching_models[0]
                    session_data[chat_id]["model_version"] = "openrouter:" + model_id
                    session_data[chat_id]["provider"] = "openrouter"
                    
                    # Send confirmation message with capabilities
                    capability_msg = get_model_capability_message(model_id)
                    base_msg = f"Model has been changed to {session_data[chat_id]['model_version']}"
                    if capability_msg:
                        full_msg = f"{base_msg}\n{capability_msg}"
                    else:
                        full_msg = base_msg
                    send_message(chat_id, full_msg)
                    continue
                else:
                    keyboard = [[{'text': model, 'callback_data': model}] for model in matching_models]
                    reply_markup = {'inline_keyboard': keyboard}
                    # print(f'Keybord {keyboard}')
                    send_message(chat_id, "Multiple models found, please select one:", reply_markup=reply_markup)
                    continue

            # Check for other commands to switch models (excluding /openrouter here)
            elif message_text.startswith("/gpt3") or message_text.startswith("/gpt4") or message_text.startswith("/claud3") or message_text.startswith("/llama3"):
                if KIOSK_MODE:
                    send_message(chat_id, "🔒 Kiosk mode: Model selection is locked.")
                    continue
                update_model_version(chat_id, message_text)
                reply_text = f"Model has been changed to {session_data[chat_id]['model_version']}"
                send_message(chat_id, reply_text)
                continue



        except Exception as e:
            print(f"Error handling commands on line {e.__traceback__.tb_lineno}: {e}")
            continue

        try:            
            # Get the image and caption if they exist
            message_photo = None
            message_caption = None
            image_data = None
            image_data_base64 = None

            if 'photo' in latest_message['message']:
                # If the message has a photo, find the largest photo that meets the size criteria
                photos = latest_message['message']['photo']
                max_allowed_size = 2048

                for photo in reversed(photos):
                    if all(dimension <= max_allowed_size for dimension in (photo['width'], photo['height'])):
                        message_photo = photo['file_id']
                        break
                    
            if message_photo:
                # Retrieve the file path of the image with retry logic
                max_retries = 3
                file_path = None
                for attempt in range(max_retries):
                    try:
                        file_info_response = requests.get(
                            f"https://api.telegram.org/bot{BOT_KEY}/getFile?file_id={message_photo}",
                            timeout=30  # Timeout for file info request
                        )
                        file_info_response.raise_for_status()
                        file_info = file_info_response.json()
                        file_path = file_info['result']['file_path']
                        break  # Success
                    except NETWORK_EXCEPTIONS as e:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error getting file info (attempt {attempt + 1}/{max_retries}): {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        else:
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Failed to get file info after {max_retries} attempts")
                
                # Download the image only if we got the file path
                if file_path:
                    image_data = download_image(file_path)
                    
                    # Base64 encode the image data
                    if image_data is not None:
                        image_data_base64 = base64.b64encode(image_data).decode('utf-8')
                    else:
                        image_data_base64 = None
                        send_message(chat_id, "⚠️ Failed to download the image due to network issues. Please try again.")
                else:
                    send_message(chat_id, "⚠️ Failed to retrieve image information due to network issues. Please try again.")

            if 'caption' in latest_message['message']:
                # If the message has a caption, get the caption text
                message_caption = latest_message['message']['caption']
                
                message_text = message_text + " \n\n " + message_caption

        except Exception as e:
            print(
                f"Error dealing with photo or caption on line {e.__traceback__.tb_lineno}: {e}")
            continue


        try:
            # Show logging notification if needed (first interaction or after context clear)
            if session_data[chat_id].get('notification_needed', False):
                notification = get_chat_log_notification()
                if notification:
                    send_message(chat_id, notification)
                session_data[chat_id]['notification_needed'] = False
            
            # Get reply from OpenAI and send it back to the user
            reply_text, tokens_used = get_reply(message_text, image_data_base64, chat_id)
            # Update activity timestamp after successful interaction
            update_activity(chat_id)
            # Only send text message if there's actual content to send
            if reply_text and reply_text.strip():
                send_message(chat_id, reply_text)

        except Exception as e:
            print(f"Error getting reply  on line {e.__traceback__.tb_lineno}: {e}")
            continue

# Send a message to user
def send_message(chat_id, text, reply_markup=None):
    print(f'send_message to {chat_id} text length {len(text)} ')
    print(f'text {text[:50]}...')  # print first 50 characters of text
    print(f'reply_markup {reply_markup} ')
    MAX_LENGTH = 4096
    def send_partial_message(chat_id, partial_text, reply_markup=None):        
        message_data = {
            "chat_id": chat_id,
            "text": partial_text
        }
        if reply_markup:
            message_data["reply_markup"] = reply_markup
        print(f'message_data {message_data} ')
    #    print(message_data)
        
        # Retry logic for sending messages
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"https://api.telegram.org/bot{BOT_KEY}/sendMessage", 
                    json=message_data,
                    timeout=30  # Add timeout for send operations
                )
                # For error cases, you might want to check if the request was successful:
                if not response.ok:
                    # Print the reason for the error status code
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error sending message (attempt {attempt + 1}/{max_retries}): {response.reason}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                else:
                    return  # Success, exit the function
            except NETWORK_EXCEPTIONS as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Network error sending message (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Failed to send message after {max_retries} attempts")
                    return


    while text:
        # If the text is shorter than the maximum, send it as is
        if len(text) <= MAX_LENGTH:
            send_partial_message(chat_id, text, reply_markup=reply_markup)
            break
        # If the text is too long, split it into smaller parts
        else:
            # Find the last newline character within the first MAX_LENGTH characters
            split_at = text.rfind('\n', 0, MAX_LENGTH)
            # If no newline is found, split at MAX_LENGTH
            if split_at == -1:
                split_at = MAX_LENGTH
            # Send the first part and shorten the remaining text
            send_partial_message(chat_id, text[:split_at], reply_markup=reply_markup)
            text = text[split_at:]


def send_image_to_telegram(chat_id, image_data, mime_type):
    """Send an image to Telegram"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Determine file extension from MIME type
            ext_map = {
                'image/jpeg': 'jpg',
                'image/jpg': 'jpg', 
                'image/png': 'png',
                'image/gif': 'gif',
                'image/webp': 'webp'
            }
            ext = ext_map.get(mime_type, 'jpg')
            
            # Prepare the photo data
            files = {
                'photo': (f'generated_image.{ext}', image_data, mime_type)
            }
            data = {
                'chat_id': chat_id,
                'caption': f'Generated image ({len(image_data)} bytes, {mime_type})'
            }
            
            # Send the photo
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_KEY}/sendPhoto",
                files=files,
                data=data,
                timeout=60  # Longer timeout for image uploads
            )
            
            if not response.ok:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error sending image (attempt {attempt + 1}/{max_retries}): {response.reason}")
                # Fallback: send as document if photo fails
                files = {
                    'document': (f'generated_image.{ext}', image_data, mime_type)
                }
                data = {
                    'chat_id': chat_id,
                    'caption': f'Generated image ({len(image_data)} bytes, {mime_type})'
                }
                response = requests.post(
                    f"https://api.telegram.org/bot{BOT_KEY}/sendDocument",
                    files=files,
                    data=data,
                    timeout=60
                )
                if not response.ok:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error sending image as document: {response.reason}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                else:
                    return  # Success
            else:
                return  # Success
                    
        except NETWORK_EXCEPTIONS as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Network error sending image (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Exception sending image (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
    
    # All retries failed - send text message as fallback
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Failed to send image after {max_retries} attempts")
    try:
        send_message(chat_id, f"⚠️ {len(image_data)} bytes of image data ({mime_type}) were received but couldn't be displayed due to network issues.")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Failed to send fallback message: {e}")
        pass  # Even the fallback failed, but don't crash


if __name__ == "__main__":
    try:
        print("Starting AI Telegram Bot...")
        print("Press Ctrl+C to stop gracefully")
        long_polling()
        print("Bot stopped gracefully.")
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received, shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        print("AI Telegram Bot shutdown complete.")


## Text for BotFather "commands", remove the "#" first

# gpt3 - Use OpenAI gpt3.5-turbo for answers (fastest but dumb)
# gpt4 - Use OpenAI gpt4.0-turbo for answers (medium speed but more intelligent, handles all images)
# gpt4o - Use OpenAI gpt4o for answers (fast speed almost as intelligent, handles all images)
# gpt4omini - Use OpenAI gpt4o mini for answers (fast, cheap, intelligent, can handle images)
# claud3opus - Use Anthropic Claud 3 Opus 20240229 for answers (slowest but most intelligent)
# claud3haiku - Use Anthropic Claud 3 Haiku for answers (cheap and fast, for better thank gpt3.5 quality)
# llama38b - Use Llama3-8b via Groq for answers  (fast but rate limited)
# llama370b - Use Llama3-70b via Groq for answers (fast but rate limited)
# openrouter - Use an OpenRouter.AI model by going /openrouter <model id>, partial match works
# listopenroutermodels - Get a list of all the OpenRouter.ai models
# clear - Clear the context of the bot
# maxrounds - set the max rounds of conversation with maxround n
# status - current chatbot status
# help - Help
