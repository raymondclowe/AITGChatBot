version = "1.7.0"

# changelog
# 1.1.0 - llama3 using groq
# 1.2.0 - gpt4o support and set to default, increase max tokens to 4K for openai and 8K for Groq
# 1.3.0 - openrouter substring matches
# 1.4.0 - gpt4o-mini support and becomes the default
# 1.5.0 - openrouter buttons
# 1.6.0 - image in and out
# 1.7.0 - profile system and LaTeX support

import requests
import base64
import os
import json
from datetime import datetime
import time
import re
import tempfile
from html import escape
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Get the API keys from the environment variables
API_KEY = os.environ.get('API_KEY')
BOT_KEY = os.environ.get('BOT_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

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
    session_data[chat_id]['CONVERSATION'] = []


# Profile management constants and functions
PROFILE_DIR = "./profiles"

def is_valid_model(model_name):
    """Validate that model name is supported."""
    valid_prefixes = ['gpt-', 'claude-', 'llama', 'openrouter:']
    return any(model_name.startswith(prefix) for prefix in valid_prefixes)


def list_available_profiles():
    """List all available profile files."""
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR)
        return []
    
    profiles = []
    for filename in os.listdir(PROFILE_DIR):
        if filename.endswith('.profile'):
            profiles.append(filename)
    
    return sorted(profiles)


def load_profile(profile_name, chat_id):
    """
    Load a profile from file and apply it to the session.
    
    Args:
        profile_name: Name of profile file (with or without .profile extension)
        chat_id: Telegram chat ID to apply profile to
    
    Returns:
        tuple: (success: bool, message: str, greeting: str)
    """
    # Ensure .profile extension
    if not profile_name.endswith('.profile'):
        profile_name += '.profile'
    
    profile_path = os.path.join(PROFILE_DIR, profile_name)
    
    if not os.path.exists(profile_path):
        return False, f"Profile '{profile_name}' not found.", None
    
    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) < 3:
            return False, "Invalid profile format. Needs at least 3 lines (model, greeting, personality).", None
        
        # Parse profile components
        model = lines[0].strip()
        greeting = lines[1].strip()
        personality_name = lines[2].strip()
        if not personality_name:
            personality_name = profile_name.replace('.profile', '')
        system_prompt = ''.join(lines[3:]).strip()
        
        # Validate model name
        if not is_valid_model(model):
            return False, f"Invalid model specified: {model}", None
        
        # Clear existing conversation and apply new profile
        session_data[chat_id]['CONVERSATION'] = []
        session_data[chat_id]['model_version'] = model
        session_data[chat_id]['profile_name'] = profile_name
        session_data[chat_id]['personality_name'] = personality_name
        print(f"Debug: Set profile_name to: {repr(profile_name)} for chat_id: {chat_id}")  # Debug output
        
        # Add system prompt as first message
        session_data[chat_id]['CONVERSATION'].append({
            'role': 'system',
            'content': [{'type': 'text', 'text': system_prompt}]
        })

        activation_message = f"Activating **{personality_name}** ({profile_name})"
        return True, activation_message, greeting
        
    except Exception as e:
        return False, f"Error loading profile: {str(e)}", None


# LaTeX rendering functions
def detect_latex_blocks(text):
    """
    Detect LaTeX blocks in text using multiple patterns.
    Returns list of dicts with 'start', 'end', 'content', 'full_match' keys.
    """
    patterns = [
        r'```latex\s*\n(.*?)\n\s*```',  # Code block format with optional whitespace
        r'\$\$(.*?)\$\$',                # Display math format
        r'\\\[(.*?)\\\]',                # LaTeX display format
    ]
    
    latex_blocks = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            latex_blocks.append({
                'start': match.start(),
                'end': match.end(),
                'content': match.group(1).strip(),
                'full_match': match.group(0)
            })
    
    # Sort by position and remove duplicates
    latex_blocks.sort(key=lambda x: x['start'])
    
    # Remove overlapping blocks (keep first occurrence)
    filtered_blocks = []
    last_end = -1
    for block in latex_blocks:
        if block['start'] >= last_end:
            filtered_blocks.append(block)
            last_end = block['end']
    
    return filtered_blocks


def render_latex_to_image(latex_code, output_path):
    """
    Render LaTeX code to an image using matplotlib.
    
    Args:
        latex_code: LaTeX expression to render
        output_path: Path to save the PNG image
    
    Returns:
        bool: True if rendering succeeded, False otherwise
    """
    try:
        # Create figure with black background for dark mode
        fig = plt.figure(figsize=(10, 2))
        fig.patch.set_facecolor('black')
        
        # Render LaTeX with white text
        text = fig.text(0.5, 0.5, f'${latex_code}$', 
                       horizontalalignment='center',
                       verticalalignment='center',
                       fontsize=10, color='white')
        
        # Save with tight bounding box
        plt.savefig(output_path, bbox_inches='tight', 
                   pad_inches=0.1, facecolor='black', dpi=150)
        plt.close(fig)
        
        return True
        
    except Exception as e:
        print(f"LaTeX rendering failed: {e}")
        try:
            plt.close('all')
        except:
            pass
        return False


def send_photo_to_telegram(chat_id, image_path, caption=None):
    """Send a photo file to Telegram."""
    try:
        with open(image_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_KEY}/sendPhoto",
                files=files,
                data=data
            )
            
            return response.ok
    except Exception as e:
        print(f"Error sending photo: {e}")
        return False


def convert_inline_latex_to_telegram(text):
    """Convert inline LaTeX expressions to Telegram HTML formatting."""
    inline_latex_pattern = r'\\+\(\s*(.*?)\s*\\+\)'
    simple_var_pattern = r'^[a-zA-Z][a-zA-Z0-9]*(_[a-zA-Z0-9]+)*$'
    var_pattern = re.compile(r'\b([a-zA-Z](?:[a-zA-Z0-9]*)?)\b')
    common_words = {
        'a', 'an', 'the', 'is', 'are', 'and', 'or', 'of', 'in', 'to', 'for',
        'with', 'by', 'at', 'on', 'as', 'if', 'it'
    }

    result = []
    last_end = 0

    for match in re.finditer(inline_latex_pattern, text):
        # Append the text before the inline LaTeX expression, HTML-escaped
        result.append(escape(text[last_end:match.start()]))

        content = match.group(1).strip()

        if re.match(simple_var_pattern, content):
            # Simple variable name -> underline
            result.append(f'<u>{escape(content)}</u>')
        else:
            formatted_parts = []
            sub_last = 0
            for var_match in var_pattern.finditer(content):
                # Add text before the variable, escaped
                if var_match.start() > sub_last:
                    formatted_parts.append(escape(content[sub_last:var_match.start()]))

                var_name = var_match.group(1)
                if var_name.lower() in common_words and len(var_name) > 1:
                    formatted_parts.append(escape(var_name))
                else:
                    formatted_parts.append(f'<i>{escape(var_name)}</i>')

                sub_last = var_match.end()

            if sub_last < len(content):
                formatted_parts.append(escape(content[sub_last:]))

            if formatted_parts:
                result.append(''.join(formatted_parts))
            else:
                result.append(escape(content))

        last_end = match.end()

    # Append any remaining text after the last match
    result.append(escape(text[last_end:]))

    return ''.join(result)


def process_ai_response(response_text, chat_id):
    """
    Process AI response, extract LaTeX, render to images, and send messages.
    Also converts inline LaTeX expressions to Telegram formatting.
    
    Args:
        response_text: The text response from the AI
        chat_id: Telegram chat ID to send messages to
    """
    latex_blocks = detect_latex_blocks(response_text)

    if not latex_blocks:
        formatted_text = convert_inline_latex_to_telegram(response_text)
        send_message(chat_id, formatted_text, parse_mode="HTML")
        return
    
    # Split text around LaTeX blocks and send sequentially
    last_pos = 0

    for i, block in enumerate(latex_blocks):
        # Send text before this LaTeX block
        if block['start'] > last_pos:
            text_before_raw = response_text[last_pos:block['start']]
            if text_before_raw.strip():
                formatted_text = convert_inline_latex_to_telegram(text_before_raw)
                if formatted_text:
                    send_message(chat_id, formatted_text, parse_mode="HTML")
        
        # Render and send LaTeX as image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            image_path = tmp.name
        
        try:
            if render_latex_to_image(block['content'], image_path):
                # Send the image
                caption = "LaTeX"
                if send_photo_to_telegram(chat_id, image_path, caption):
                    print(f"Successfully sent LaTeX image for block {i}")
                else:
                    # Fallback: send as code block if image sending fails
                    escaped_content = escape(block['content'])
                    fallback_message = f"<pre language=\"latex\">{escaped_content}</pre>"
                    send_message(chat_id, fallback_message, parse_mode="HTML")
            else:
                # Fallback: send as code block if rendering fails
                escaped_content = escape(block['content'])
                fallback_message = f"<pre language=\"latex\">{escaped_content}</pre>"
                send_message(chat_id, fallback_message, parse_mode="HTML")
        finally:
            # Clean up temp file
            try:
                os.remove(image_path)
            except:
                pass
        
        last_pos = block['end']
    
    # Send any remaining text after last LaTeX block
    if last_pos < len(response_text):
        text_after_raw = response_text[last_pos:]
        if text_after_raw.strip():
            formatted_text = convert_inline_latex_to_telegram(text_after_raw)
            if formatted_text:
                send_message(chat_id, formatted_text, parse_mode="HTML")


def get_reply(message, image_data_64, session_id):
    note = ""
    response_text = ""
    if not session_data[session_id]:
        session_data[session_id] = {
            "CONVERSATION": [],
            "tokens_used": 0,
            "model_version": "gpt-4o-mini",
            "max_rounds": DEFAULT_MAX_ROUNDS,
            "personality_name": None
        }
    # Ensure session has all required keys without overwriting existing ones
    if "profile_name" not in session_data[session_id]:
        session_data[session_id]["profile_name"] = None
    if "personality_name" not in session_data[session_id]:
        session_data[session_id]["personality_name"] = None
    has_image = False
    # check the length of the existing conversation, if it is too long (with messages more than double the max rounds, then trim off until it is within the limit of rounds. one round is one user and one assistant text.
    max_messages = session_data[session_id]["max_rounds"] * 2
    if len(session_data[session_id]["CONVERSATION"]) > max_messages:
        session_data[session_id]["CONVERSATION"] = session_data[session_id]["CONVERSATION"][-max_messages:]

    # Add the new user message to the conversation
    new_user_message = [
        {
            "role": "user",
            "content": [{"type": "text", "text": message}],
            # "datetime": datetime.now(),
        }
    ]
    if image_data_64:  # If there's a new image, include it in the user's message
        has_image = True
        image_content_item = {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data_64}"},
        }
        new_user_message[0]["content"].append(image_content_item)
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



    if model.startswith("gpt"):
        payload = {
            "model": model,
            "max_tokens": 4000,
            "messages": session_data[session_id]["CONVERSATION"],
        }

        raw_response = requests.post(
            OPENAI_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            },
            json=payload,
        )
    elif model.startswith("openrouter"):
        # if an openrouter model then strip of the string "openrouter:" from the beginning
        # model = model[11:]
        payload = {
            "model": model[11:],
            "max_tokens": 4000,
            "messages": session_data[session_id]["CONVERSATION"],
        }

        raw_response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            },
            json=payload,
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
                        image_response = requests.get(image_url)
                        image_data_64 = base64.b64encode(image_response.content).decode("utf-8")

                    anthropic_message["content"].append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data_64
                        }
                    })

            anthropic_payload["messages"].append(anthropic_message)

        raw_response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=anthropic_payload,
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
        
        raw_response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": "Bearer " + GROQ_API_KEY,                
                "content-type": "application/json",
            },
            json=groq_payload
        )

    # Handle the response
    raw_json = raw_response.json()

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
        return f"Error message: {raw_json['error']['message']}" + note, 0

    # Update tokens used and process the response based on the model used
    tokens_used = session_data[session_id]["tokens_used"]
    images_received = []  # Initialize for all models
    
    if model.startswith("gpt") or model.startswith("openrouter"):
        tokens_used += raw_json["usage"]["total_tokens"]
        
        # Handle multipart responses (text + images)
        if raw_json["choices"]:
            message = raw_json["choices"][0]["message"]
            message_content = message["content"]
            
            # Check if content is a list (multipart) or string (text only)
            if isinstance(message_content, list):
                response_parts = []
                
                for part in message_content:
                    if part.get("type") == "text" and part.get("text"):
                        response_parts.append(part["text"])
                    elif part.get("type") == "image_url" and part.get("image_url"):
                        # Handle image responses
                        image_url = part["image_url"].get("url", "")
                        if image_url.startswith("data:image/"):
                            # Extract base64 data
                            try:
                                header, data = image_url.split(",", 1)
                                mime_type = header.split(":")[1].split(";")[0]
                                image_data = base64.b64decode(data)
                                images_received.append((image_data, mime_type))
                                response_parts.append(f"[Image generated: {len(image_data)} bytes, {mime_type}]")
                            except Exception as e:
                                response_parts.append(f"[Unable to process image: {e}]")
                        else:
                            response_parts.append(f"[Image URL: {image_url}]")
                    elif part.get("inline_data"):
                        # Handle Gemini-style inline data
                        inline_data = part["inline_data"]
                        mime_type = inline_data.get("mimeType", "unknown")
                        data = inline_data.get("data", "")
                        try:
                            image_data = base64.b64decode(data)
                            images_received.append((image_data, mime_type))
                            response_parts.append(f"[Image generated: {len(image_data)} bytes, {mime_type}]")
                        except Exception as e:
                            response_parts.append(f"[Unable to process inline data: {e}]")
                
                response_text = "\n".join(response_parts) if response_parts else "No text content received."
                    
            else:
                # Simple string response (OpenRouter format: text in content, images in separate array)
                response_text = message_content.strip() if message_content else "API error occurred." + note
                
            # Check for images in separate images array (OpenRouter format)
            if message.get("images"):
                for image_item in message["images"]:
                    if image_item.get("type") == "image_url" and image_item.get("image_url"):
                        image_url = image_item["image_url"].get("url", "")
                        if image_url.startswith("data:image/"):
                            # Extract base64 data
                            try:
                                header, data = image_url.split(",", 1)
                                mime_type = header.split(":")[1].split(";")[0]
                                image_data = base64.b64decode(data)
                                images_received.append((image_data, mime_type))
                                print(f"Found image in separate images array: {len(image_data)} bytes, {mime_type}")
                            except Exception as e:
                                print(f"Error processing image from images array: {e}")
                        else:
                            print(f"Non-data image URL in images array: {image_url}")
            
            # Send any images to Telegram
            for image_data, mime_type in images_received:
                send_image_to_telegram(session_id, image_data, mime_type)
        else:
            response_text = "API error occurred." + note
            
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

    # Optional: print the session_data for debugging
    # print(json.dumps(session_data[session_id], indent=4))

    return response_text, tokens_used


# Function to download the image given the file path
def download_image(file_path):
    file_url = f"https://api.telegram.org/file/bot{BOT_KEY}/{file_path}"
    response = requests.get(file_url)
    return response.content


# Function to send image to Telegram
def send_image_to_telegram(chat_id, base64_data):
    try:
        # Decode base64 data
        image_data = base64.b64decode(base64_data)
        
        # Send as photo to Telegram
        files = {'photo': ('image.png', image_data, 'image/png')}
        data = {'chat_id': chat_id}
        
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_KEY}/sendPhoto",
            files=files,
            data=data
        )
        
        if response.ok:
            print(f"Successfully sent generated image to chat {chat_id}")
        else:
            print(f"Failed to send image: {response.text}")
            
    except Exception as e:
        print(f"Error sending image to Telegram: {e}")


# get list from https://openrouter.ai/api/v1/models
def list_openrouter_models_as_message():
    response = requests.get(f"https://openrouter.ai/api/v1/models")
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


# get list from https://openrouter.ai/api/v1/models
def list_openrouter_models_as_list():
    response = requests.get(f"https://openrouter.ai/api/v1/models")
    openRouterModelList = response.json()['data']
    model_list = []
    for model in openRouterModelList:
        model_list.append(model['id'])
    return model_list

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
            
        response = requests.get('https://openrouter.ai/api/v1/models', headers=headers)
        
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
        
    except Exception as e:
        print(f"Error fetching model capabilities: {e}")
        return get_openrouter_capabilities_fallback()

def get_openrouter_capabilities_fallback():
    """Fallback to pattern matching when API is unavailable"""
    try:
        response = requests.get('https://openrouter.ai/api/v1/models')
        if response.status_code == 200:
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
    except Exception as e:
        print(f"Error in fallback pattern matching: {e}")
    
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
    while True:
        try:
            # Long polling request to get new messages
            response = requests.get(f"https://api.telegram.org/bot{BOT_KEY}/getUpdates?timeout=100&offset={offset}")

            # presume the response is json and pretty print it with nice colors and formatting
            # print(response.json(), indent=4, sort_dicts=False)

            # If there is no response then continue the loop
            if not response.json()['result']:
                continue


        except Exception as e:
            print(f"Error getting response on line {e.__traceback__.tb_lineno}: {e}")
            continue

        try:

            # Get the latest message and update the offset
            latest_message = response.json()['result'][-1]
            offset = latest_message['update_id'] + 1

            # Check if we have a message or callback query
            if 'message' in latest_message:
                message_text = latest_message['message'].get('text', '')  # Use get() with a default value of ''
                chat_id = latest_message['message']['chat']['id']
            elif 'callback_query' in latest_message:
                # Handle callback query from inline keyboard
                callback_query = latest_message['callback_query']
                chat_id = callback_query['message']['chat']['id']
                selected_model = callback_query['data']
                
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
                requests.post(f"https://api.telegram.org/bot{BOT_KEY}/answerCallbackQuery", json={
                    "callback_query_id": callback_query['id']
                })
                continue
            else:
                continue

            # if the message_text length is near the limit then maybe this is a truncated message
            # so we need to get the rest of the message
            if len(message_text) > 3000:
                # fast loop to look for any additional messages, down side of this is it adds at least one second
                while True:
                    additional_response = requests.get(f"https://api.telegram.org/bot{BOT_KEY}/getUpdates?timeout=1&offset={offset}")
                    if not additional_response.json()['result']:
                        break
                    else:
                        additional_latest_message = additional_response.json()['result'][-1]
                        message_text += additional_latest_message['message']['text']
                        offset = additional_latest_message['update_id'] + 1
                        # after having got this additional text we loop because there might be more


            # check in the session data if there is a key with this chat_id, if not then initialize an empty one
            if chat_id not in session_data:  # doing it now because we may have to accept setting model version
                session_data[chat_id] = {'model_version': "gpt-4o-mini",
                                        'CONVERSATION': [],
                                        'tokens_used': 0,
                                        "max_rounds": DEFAULT_MAX_ROUNDS,
                                        "profile_name": None,
                                        "personality_name": None
                                        }

        except Exception as e:
            print(f"Error reading last message on line {e.__traceback__.tb_lineno}: {e}")
            continue

        try:

            # implement a /help command that outputs brief explanation of commands
            if message_text.startswith('/help'):
                reply_text = "Commands:\n"
                reply_text += "/help - this help message\n"
                reply_text += "/clear - clear the context\n"
                reply_text += "/maxrounds <n> - set the max rounds of conversation\n"
                reply_text += "/gpt3 - set the model to gpt3\n"
                reply_text += "/gpt4 - set the model to gpt-4-turbo\n"
                reply_text += "/gpt4o - set the model to gpt-4o\n"
                reply_text += "/gpt4omini - set the model to gpt-4o-mini\n"  # Add this line
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
                reply_text += "• OpenRouter models automatically support images when capable\n\n"
                reply_text += "🎭 Profile Features:\n"
                reply_text += "/activate <profile> - activate a profile\n"
                reply_text += "/listprofiles - show all available profiles\n"
                reply_text += "/currentprofile - show current active profile\n"
                reply_text += "/deactivate - return to default configuration"

                send_message(chat_id, reply_text)
                continue  # Skip the rest of the processing loop

            if message_text.startswith('/status'):
                current_model = session_data[chat_id]['model_version']
                reply_text = f"Model: {current_model}\n"
                reply_text += f"Provider: {session_data[chat_id].get('provider', 'Not set')}\n"

                # Show active profile
                profile_name = session_data[chat_id].get('profile_name', None)
                personality_name = session_data[chat_id].get('personality_name', None)
                print(f"Debug: profile_name from session: {repr(profile_name)}")  # Debug output
                if profile_name and personality_name:
                    reply_text += f"Active profile: {profile_name} ({personality_name})\n"
                elif profile_name:
                    reply_text += f"Active profile: {profile_name}\n"
                else:
                    reply_text += "Active profile: None (default)\n"

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
                send_message(chat_id, reply_text)
                continue

            if message_text.startswith('/maxrounds'):
                if len(message_text.split()) == 1:
                    reply_text = f"Max rounds is currently set to {session_data[chat_id]['max_rounds']}" 
                    send_message(chat_id, reply_text)
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
                continue  # Skip the rest of the processing loop

            # Handle profile activation
            if message_text.startswith('/activate'):
                parts = message_text.split(maxsplit=1)
                
                if len(parts) < 2:
                    # List available profiles
                    profiles = list_available_profiles()
                    if profiles:
                        reply = "Available profiles:\n"
                        reply += "\n".join([f"• {p.replace('.profile', '')}" for p in profiles])
                        reply += "\n\nUse: /activate <profile_name>"
                    else:
                        reply = "No profiles available."
                    send_message(chat_id, reply)
                    continue
                
                profile_name = parts[1]
                success, message, greeting = load_profile(profile_name, chat_id)
                
                send_message(chat_id, message)
                if success and greeting:
                    send_message(chat_id, greeting)
                continue

            # Handle list profiles command
            if message_text.startswith('/listprofiles'):
                profiles = list_available_profiles()
                if profiles:
                    reply = "📋 Available profiles:\n\n"
                    for p in profiles:
                        profile_name = p.replace('.profile', '')
                        reply += f"• {profile_name}\n"
                    reply += "\nUse /activate <profile_name> to activate a profile"
                else:
                    reply = "No profiles available."
                send_message(chat_id, reply)
                continue

            # Handle current profile command
            if message_text.startswith('/currentprofile'):
                profile_name = session_data[chat_id].get('profile_name', None)
                personality_name = session_data[chat_id].get('personality_name', None)
                if profile_name:
                    if personality_name:
                        reply = f"Current profile: {profile_name} ({personality_name})\n"
                    else:
                        reply = f"Current profile: {profile_name}\n"
                    reply += f"Model: {session_data[chat_id]['model_version']}"
                else:
                    reply = "No profile activated. Using default configuration."
                send_message(chat_id, reply)
                continue

            # Handle deactivate profile command
            if message_text.startswith('/deactivate'):
                session_data[chat_id]['CONVERSATION'] = []
                session_data[chat_id]['model_version'] = "gpt-4o-mini"
                session_data[chat_id]['profile_name'] = None
                session_data[chat_id]['personality_name'] = None
                reply = "Profile deactivated. Returned to default configuration."
                send_message(chat_id, reply)
                continue

            # Handle listopenroutermodels command, query live list from https://openrouter.ai/api/v1/models and respond in a text format message
            if message_text.startswith('/listopenroutermodels'):
                reply_text = list_openrouter_models_as_message()
                send_message(chat_id, reply_text)
                continue  # Skip the rest of the processing loop
                
            # Handle /openrouter command in long_polling
            if message_text.startswith("/openrouter"):
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
                # Retrieve the file path of the image
                file_info_response = requests.get(f"https://api.telegram.org/bot{BOT_KEY}/getFile?file_id={message_photo}")
                file_info = file_info_response.json()
                file_path = file_info['result']['file_path']

                # Download the image
                image_data = download_image(file_path)
                
                # Base64 encode the image data
                if image_data is not None:
                    image_data_base64 = base64.b64encode(image_data).decode('utf-8')
                else:
                    image_data_base64 = None

            if 'caption' in latest_message['message']:
                # If the message has a caption, get the caption text
                message_caption = latest_message['message']['caption']
                
                message_text = message_text + " \n\n " + message_caption

        except Exception as e:
            print(
                f"Error dealing with photo or caption on line {e.__traceback__.tb_lineno}: {e}")
            continue


        try:            
           # Get reply from OpenAI and send it back to the user
            reply_text, tokens_used = get_reply(message_text, image_data_base64, chat_id)
            # Process response for LaTeX and send
            process_ai_response(reply_text, chat_id)

        except Exception as e:
            print(f"Error getting reply  on line {e.__traceback__.tb_lineno}: {e}")
            continue

# Send a message to user
def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    print(f'send_message to {chat_id} text length {len(text)} ')
    print(f'text {text[:50]}...')  # print first 50 characters of text
    print(f'reply_markup {reply_markup} ')
    MAX_LENGTH = 4096
    use_parse_mode = parse_mode if parse_mode and len(text) <= MAX_LENGTH else None

    def send_partial_message(chat_id, partial_text, reply_markup=None, parse_mode=None):        
        message_data = {
            "chat_id": chat_id,
            "text": partial_text
        }
        if reply_markup:
            message_data["reply_markup"] = reply_markup
        if parse_mode:
            message_data["parse_mode"] = parse_mode
        print(f'message_data {message_data} ')
    #    print(message_data)
        response = requests.post(f"https://api.telegram.org/bot{BOT_KEY}/sendMessage", json=message_data)
        # For error cases, you might want to check if the request was successful:
        if not response.ok:
            # Print the reason for the error status code
            print(f"Error Reason: {response.reason}")


    while text:
        # If the text is shorter than the maximum, send it as is
        if len(text) <= MAX_LENGTH:
            send_partial_message(chat_id, text, reply_markup=reply_markup, parse_mode=use_parse_mode)
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
            data=data
        )
        
        if not response.ok:
            print(f"Error sending image: {response.reason}")
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
                data=data
            )
            if not response.ok:
                print(f"Error sending image as document: {response.reason}")
                
    except Exception as e:
        print(f"Exception sending image: {e}")
        # Send text message as fallback
        send_message(chat_id, f"⚠️ {len(image_data)} bytes of image data ({mime_type}) were received but couldn't be displayed.")


long_polling()


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
