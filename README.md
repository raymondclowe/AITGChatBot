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
- Only `/help`, `/clear`, and `/status` commands are available
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
- `/help` - Show kiosk mode help
- `/clear` - Clear conversation context
- `/status` - Show current status (with kiosk mode indicator)
