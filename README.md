# AITGChatBot
An AI LLM powered Telegram ChatBot with switchable backends; supports OpenAI, Mistral, OpenRouter and Groq

## Features

- Multiple AI backends: OpenAI (GPT-3.5, GPT-4, GPT-4o), Anthropic Claude, OpenRouter models, and Groq (Llama 3)
- Image input/output support for vision and image generation models
- Conversation history with configurable max rounds
- **Kiosk Mode** for locked-down, dedicated use cases

## Environment Variables

### Required
- `BOT_KEY` - Telegram bot token
- `API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key (for Claude models)
- `OPENROUTER_API_KEY` - OpenRouter API key
- `GROQ_API_KEY` - Groq API key (for Llama models)

## Kiosk Mode

Kiosk mode provides a locked-down instance ideal for educational environments, public terminals, or dedicated single-purpose bots.

### Configuration

Kiosk mode is configured via `kiosk.conf` file. Copy `kiosk.conf.example` to `kiosk.conf` and modify as needed:

```ini
[kiosk]
# Enable kiosk mode (true/false)
enabled = true

# The model to use in kiosk mode
model = openrouter:google/gemini-2.0-flash-001

# Path to the system prompt file
prompt_file = kiosk_prompt_example.txt

# Inactivity timeout in seconds (0 = disabled)
inactivity_timeout = 3600
```

### Kiosk Mode Restrictions
When kiosk mode is enabled:
- Model selection is locked (users cannot change the model)
- System prompt is loaded from file and cannot be modified
- `/maxrounds` changes are blocked
- `/listopenroutermodels` is disabled
- Only `/start`, `/help`, `/clear`, and `/status` commands are available
- Unrecognized commands display helpful error messages
- Multi-user chats are still supported with separate conversation histories
- Visual indicator (🔒) shows kiosk mode is active

### Example Setup for Educational Use

1. Copy the example config:
```bash
cp kiosk.conf.example kiosk.conf
```

2. Edit `kiosk.conf` with your settings:
```ini
[kiosk]
enabled = true
model = openrouter:google/gemini-2.0-flash-001
prompt_file = kiosk_prompt_example.txt
inactivity_timeout = 3600
```

3. Create or edit your system prompt file (e.g., `kiosk_prompt_example.txt`)

4. Run the bot:
```bash
python ai-tgbot.py
```

## Chat Logging

The bot supports chat logging with separate log levels for user and assistant messages. This provides fine-grained control over what gets logged, which is useful for privacy, auditing, and debugging purposes.

### Configuration

Add a `[logging]` section to your `kiosk.conf` file:

```ini
[logging]
# Separate log levels for user and assistant messages
# Values: off, minimum (text only), extended (text + attachments)
log_user_messages = minimum
log_assistant_messages = extended

# Directory where chat logs are saved
log_directory = ./chat_logs
```

### Log Levels

- `off` - No logging for this role
- `minimum` - Log text messages only
- `extended` - Log text messages and images/attachments

### Use Cases

**Privacy/Auditing**: Log only user messages for audit trails:
```ini
log_user_messages = minimum
log_assistant_messages = off
```

**Debugging**: Log only assistant responses to troubleshoot model behavior:
```ini
log_user_messages = off
log_assistant_messages = extended
```

**Full Logging**: Log everything for comprehensive records:
```ini
log_user_messages = extended
log_assistant_messages = extended
```

### Backward Compatibility

For backward compatibility, you can still use the legacy `log_chats` setting, which applies the same level to both user and assistant messages:

```ini
[logging]
log_chats = minimum
```

## Commands

### Standard Mode
- `/help` - Show help message
- `/clear` - Clear conversation context
- `/status` - Show current chatbot status
- `/maxrounds <n>` - Set max conversation rounds
- `/gpt3`, `/gpt4`, `/gpt4o`, `/gpt4omini` - Switch to OpenAI models
- `/claud3opus`, `/claud3haiku` - Switch to Anthropic Claude models
- `/llama38b`, `/llama370b` - Switch to Groq Llama models
- `/openrouter <model>` - Switch to an OpenRouter model
- `/listopenroutermodels` - List available OpenRouter models

### Kiosk Mode
- `/start` - Show welcome message
- `/help` - Show kiosk mode help
- `/clear` - Clear conversation context
- `/status` - Show current status (with kiosk mode indicator)

## Developer Notes

### Image Generation and Reasoning Field

When using models like Google Gemini via OpenRouter for image generation, the API may return explanatory text in different fields:

- **Standard behavior**: Text content is in the `content` field
- **Image generation (Gemini/OpenRouter)**: When an image is generated, the `content` field may be empty and the explanatory/descriptive text is instead placed in a `reasoning` field

The bot automatically handles this by:
1. Checking the `content` field first (primary source for text)
2. If `content` is empty but images are present, falling back to the `reasoning` field
3. This ensures users see both generated images and the AI's explanation/description

This behavior is logged in debug output when it occurs. See the debug logs (if enabled) for details on response structure.
