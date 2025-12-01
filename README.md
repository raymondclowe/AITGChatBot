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

### Kiosk Mode (Optional)
Kiosk mode provides a locked-down instance ideal for educational environments, public terminals, or dedicated single-purpose bots.

- `KIOSK_MODE` - Set to `true` to enable kiosk mode
- `KIOSK_MODEL` - The model to use (e.g., `gpt-4o`, `openrouter:google/gemini-2.0-flash-001`)
- `KIOSK_PROMPT_FILE` - Path to a text file containing the system prompt (supports multi-line prompts)
- `KIOSK_INACTIVITY_TIMEOUT` - Seconds of inactivity before auto-clearing conversation (0 = disabled)

#### Kiosk Mode Restrictions
When kiosk mode is enabled:
- Model selection is locked (users cannot change the model)
- System prompt is loaded from file and cannot be modified
- `/maxrounds` changes are blocked
- `/listopenroutermodels` is disabled
- Only `/help`, `/clear`, and `/status` commands are available
- Multi-user chats are still supported with separate conversation histories
- Visual indicator (🔒) shows kiosk mode is active

#### Example Setup for Educational Use

1. Create a system prompt file (`education_prompt.txt`):
```
You are an educational tutor for IB Math and Physics. Help students understand concepts deeply.
Use the Socratic method: ask guiding questions rather than giving direct answers.
Always encourage the student and celebrate their progress.
```

2. Set environment variables:
```bash
export KIOSK_MODE=true
export KIOSK_MODEL=openrouter:google/gemini-2.0-flash-001
export KIOSK_PROMPT_FILE=/path/to/education_prompt.txt
export KIOSK_INACTIVITY_TIMEOUT=3600  # Clear after 1 hour of inactivity
```

3. Run the bot as usual:
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
