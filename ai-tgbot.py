version = "1.0.0"

import requests
import base64
import os
import json
from datetime import datetime

# Get the API keys from the environment variables
API_KEY = os.environ.get('API_KEY')
BOT_KEY = os.environ.get('BOT_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

# Set the URL for the API
OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'
ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'


# list of the possible "model" values:
# gpt-3.5-turbo
# gpt-4-turbo
# claude-3-opus-20240229
# claude-3-haiku-20240307
# openrouter:<model name>


# set starting values
session_data = {}

# default conversation max rounds is 4 which is double the previous version of the bot
DEFAULT_MAX_ROUNDS = 4


def update_model_version(session_id, command):
    if command.lower() == "/gpt3":
        session_data[session_id]["model_version"] = "gpt-3.5-turbo"
    elif command.lower() == "/gpt4":
        session_data[session_id]["model_version"] = "gpt-4-turbo"
    elif command.lower() == "/claud3opus":
        session_data[session_id]["model_version"] = "claude-3-opus-20240229"
    elif command.lower() == "/claud3haiku":
        session_data[session_id]["model_version"] = "claude-3-haiku-20240307"
    elif command.lower().startswith('/openrouter'):
        # look for a second word, that will be the actual model
        session_data[session_id]["model_version"] = "openrouter:" + command.split()[1] 

def clear_context(chat_id):
    session_data[chat_id]['CONVERSATION'] = []



def get_reply(message, image_data_64, session_id):
    if not session_data[session_id]:
        session_data[session_id] = {
            "CONVERSATION": [],
            "tokens_used": 0,
            "model_version": "gpt-4-turbo",
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

    # if an openrouter model then strip of the string "openrouter:" from the beginning
    if model.startswith("openrouter:"):
        model = model[11:]

    payload = {
        "model": model,
        "max_tokens": 3000,
        "messages": session_data[session_id]["CONVERSATION"],
    }

    # Select API based on model_version
    if session_data[session_id]["model_version"].startswith("gpt"):
        raw_response = requests.post(
            OPENAI_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            },
            json=payload,
        )
    elif session_data[session_id]["model_version"].startswith("claud"):  # Assuming "claud"
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
    elif session_data[session_id]["model_version"].startswith("openrouter"):
            raw_response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            },
            json=payload,
        )

    # Handle the response
    raw_json = raw_response.json()
    if "error" in raw_json:
        return f"Error message: {raw_json['error']['message']}", 0

    # Update tokens used and process the response based on the model used
    tokens_used = session_data[session_id]["tokens_used"]
    if session_data[session_id]["model_version"].startswith("gpt") or session_data[session_id]["model_version"].startswith("openrouter"):
        tokens_used += raw_json["usage"]["total_tokens"]
        response_text = (
            raw_json["choices"][0]["message"]["content"].strip()
            if raw_json["choices"]
            else "API error occurred."
        )
    else:  # Assuming "claud"
        tokens_used += (
            raw_json["usage"]["input_tokens"] + raw_json["usage"]["output_tokens"]
        )
        response_text = (
            raw_json["content"][0]["text"].strip()
            if raw_json["content"]
            else "API error occurred."
        )

    # Update the conversation with the assistant response
    assistant_response = [
        {
            "role": "assistant",
            "content": [{"type": "text", "text": response_text}],
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
    model_list = "Model ID : Model Name\n\n"
    for model in openRouterModelList: # include only id and name fields
        model_list += f"{model['id']} : {model['name']}\n"
        
    model_list += "\n\nOr choose from the best ranked at https://openrouter.ai/rankings"
    return model_list

# get list from https://openrouter.ai/api/v1/models
def list_openrouter_models_as_list():
    response = requests.get(f"https://openrouter.ai/api/v1/models")
    openRouterModelList = response.json()['data']
    model_list = []
    for model in openRouterModelList:
        model_list.append(model['id'])
    return model_list



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
            message_text = latest_message['message'].get('text', '')  # Use get() with a default value of ''
            chat_id = latest_message['message']['chat']['id']
            offset = latest_message['update_id'] + 1

            # if the message_text length is near the limit then maybe this is a truncated message
            # so we need to get the rest of the message
            if len(message_text) > 3000:
                # fast loop to look for any additional messages, down side of this is it adds at least one extra second            
                while True:
                    # check with a timeout of 1 seconds to see if there is more data
                    additional_response = requests.get(f"https://api.telegram.org/bot{BOT_KEY}/getUpdates?timeout=1&offset={offset}")
                    if not additional_response.json()['result']:
                        break
                    else:
                        additional_latest_message = additional_response.json()['result'][-1]
                        message_text += additional_latest_message['message'].get('text', '')
                        offset = additional_latest_message['update_id'] + 1
                        # after having got this additional text we loop because there might be more


            # check in the session data if there is a key with this chat_id, if not then initialize an empty one
            if chat_id not in session_data: # doing it now because we may have to accept setting model version
                session_data[chat_id] = {'model_version': "gpt-4-turbo",
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
                reply_text += "/claud3opus - set the model to Claud 3 Opus\n"
                reply_text += "/claud3haiku - set the model to Claud 3 Haiku\n"
                reply_text += "/listopenroutermodels - list all openrouter models\n"
                reply_text += "/openrouter <model id> - set the model to the model with the given id\n"
                reply_text += "/status - get the chatbot status, current model, current max rounds, current conversation length"


                send_message(chat_id, reply_text)
                continue  # Skip the rest of the processing loop                

            if message_text.startswith('/status'):
                reply_text = f"Model: {session_data[chat_id]['model_version']}\n"
                reply_text += f"Max rounds: {session_data[chat_id]['max_rounds']}\n"
                reply_text += f"Conversation length: {len(session_data[chat_id]['CONVERSATION'])}\n"
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
                
            # Check for commands to switch models and set it in the session
            if (
                message_text.startswith("/gpt3")
                or message_text.startswith("/gpt4")
                or message_text.startswith("/claud3")
                or message_text.startswith("/openrouter")
            ):
                if message_text.startswith("/openrouter"):
                    # validate that there is a second word, being the model name
                    if len(message_text.split()) == 1:
                        reply_text = f"Please specify a model name after the command"
                        send_message(chat_id, reply_text)
                        continue
                    # get the model name
                    model_name = message_text.split()[1]
                    # validate this model name is ok by checking against the list of models
                    if model_name not in list_openrouter_models_as_list():
                        reply_text = f"Model name {model_name} not found in list of models"
                        send_message(chat_id, reply_text)
                        continue                    
                update_model_version(chat_id, message_text)
                reply_text = f"Model has been changed to {session_data[chat_id]['model_version']}"
                send_message(chat_id, reply_text)
                continue  # Skip the rest of the processing loop



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
            send_message(chat_id, reply_text )

        except Exception as e:
            print(f"Error getting reply  on line {e.__traceback__.tb_lineno}: {e}")
            continue

# Send a message to user
def send_message(chat_id, text):
    MAX_LENGTH = 4096
    def send_partial_message(chat_id, partial_text):        
        response = requests.post(f"https://api.telegram.org/bot{BOT_KEY}/sendMessage", json={
            "chat_id": chat_id,
            "text": partial_text
        })
        # For error cases, you might want to check if the request was successful:
        if not response.ok:
            # Print the reason for the error status code
            print(f"Error Reason: {response.reason}")


    while text:
        # If the text is shorter than the maximum, send it as is
        if len(text) <= MAX_LENGTH:
            send_partial_message(chat_id, text)
            break
        # If the text is too long, split it into smaller parts
        else:
            # Find the last newline character within the first MAX_LENGTH characters
            split_at = text.rfind('\n', 0, MAX_LENGTH)
            # If no newline is found, split at MAX_LENGTH
            if split_at == -1:
                split_at = MAX_LENGTH
            # Send the first part and shorten the remaining text
            send_partial_message(chat_id, text[:split_at])
            text = text[split_at:]


long_polling()


## Text for BotFather "commands", remove the "#" first

# gpt3 - Use OpenAI gpt3.5-turbo for answers (fastest but dumb)
# gpt4 - Use OpenAI gpt4.0-turbo for answers (medium speed but more intelligent, handles all images)
# claud3opus - Use Anthropic Claud 3 Opus 20240229 for answers (slowest but most intelligent)
# claud3haiku - Use Anthropic Claud 3 Haiku for answers (cheap and fast, for better thank gpt3.5 quality)
# openrouter - Use an OpenRouter.AI model by going /openrouter <model id>
# listopenroutermodels - Get a list of all the OpenRouter.ai models
# clear - Clear the context of the bot
# maxrounds - set the max rounds of conversation with maxround n
# status - current chatbot status
# help - Help