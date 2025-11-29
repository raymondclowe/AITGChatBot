version = "1.6.1"

# changelog
# 1.1.0 - llama3 using groq
# 1.2.0 - gpt4o support and set to default, increase max tokens to 4K for openai and 8K for Groq
# 1.3.0 - openrouter substring matches
# 1.4.0 - gpt4o-mini support and becomes the default
# 1.5.0 - openrouter buttons
# 1.6.0 - image in and out

import requests
import base64
import os
import json
import hashlib
from datetime import datetime
import time

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


def get_reply(message, image_data_64, session_id):
    note = ""
    response_text = ""
    if not session_data[session_id]:
        session_data[session_id] = {
            "CONVERSATION": [],
            "tokens_used": 0,
            "model_version": "gpt-4o-mini",
            "max_rounds": DEFAULT_MAX_ROUNDS
        }
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
                "HTTP-Referer": "https://github.com/raymondclowe/AITGChatBot",
                "X-Title": "AITGChatBot",
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
    seen_image_sizes = []  # Track image sizes to detect near-duplicate images

    # Helper function to add image without duplicates
    def add_image_if_unique(image_data, mime_type):
        image_hash = hashlib.sha256(image_data).hexdigest()
        if image_hash in seen_image_hashes:
            return False
        
        # Check for near-duplicate images (same visual content with different encoding)
        # Some providers return the same image with slightly different compression/metadata
        # If an image size is within 1% of an already-seen image, treat as duplicate
        image_size = len(image_data)
        for seen_size in seen_image_sizes:
            # Use max of both sizes to avoid division issues with very small images
            max_size = max(seen_size, image_size, 1)
            size_diff_ratio = abs(image_size - seen_size) / max_size
            if size_diff_ratio < 0.01:  # Within 1% size difference
                print(f"Skipped near-duplicate image: {image_size} bytes (similar to {seen_size} bytes)")
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
            # We check this FIRST and only fall back to content array if no images found
            images_from_array = False
            if message.get("images"):
                for image_item in message["images"]:
                    if image_item.get("type") == "image_url" and image_item.get("image_url"):
                        image_url = image_item["image_url"].get("url", "")
                        if process_image_url(image_url, "images array"):
                            images_from_array = True
            
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

    # Optional: print the session_data for debugging
    # print(json.dumps(session_data[session_id], indent=4))

    return response_text, tokens_used


# Function to download the image given the file path
def download_image(file_path):
    file_url = f"https://api.telegram.org/file/bot{BOT_KEY}/{file_path}"
    response = requests.get(file_url)
    return response.content


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
                                        "max_rounds": DEFAULT_MAX_ROUNDS
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
                reply_text += "• OpenRouter models automatically support images when capable"

                send_message(chat_id, reply_text)
                continue  # Skip the rest of the processing loop

            if message_text.startswith('/status'):
                current_model = session_data[chat_id]['model_version']
                reply_text = f"Model: {current_model}\n"
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
        response = requests.post(f"https://api.telegram.org/bot{BOT_KEY}/sendMessage", json=message_data)
        # For error cases, you might want to check if the request was successful:
        if not response.ok:
            # Print the reason for the error status code
            print(f"Error Reason: {response.reason}")


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
