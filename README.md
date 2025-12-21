# AITGChatBot
An AI LLM powered Telegram ChatBot with switchable backends; supports OpenAI, Mistral, OpenRouter and Groq

## Features

- Multiple AI backends: OpenAI (GPT-3.5, GPT-4, GPT-4o), Anthropic Claude, OpenRouter models, and Groq (Llama 3)
- Image input/output support for vision and image generation models
- Conversation history with configurable max rounds
- **Profile System** for switching between AI personalities
- **LaTeX Support** for rendering mathematical equations
- **Kiosk Mode** for locked-down, dedicated use cases

## Profile System

Switch between different AI personalities and configurations using profile files. Perfect for creating specialized assistants for different use cases.

### Profile Commands
- `/activate <profile>` - Activate a profile
- `/listprofiles` - Show all available profiles  
- `/currentprofile` - Show current active profile
- `/deactivate` - Return to default configuration

### Profile Format
Create your own `.profile` files in the `profiles/` directory:
```
Line 1: Model name (e.g., gpt-4o-mini, openrouter:anthropic/claude-3-opus)
Line 2: Greeting message
Line 3: Personality name
Line 4+: System prompt (can span multiple lines)
```

### Included Profiles
- **eec** - Emergency Education Chatbot for IB Math and Physics
- **ib_tutor** - IB Math and Physics tutor using Socratic method
- **pirate** - A fun pirate-themed assistant

## LaTeX Support

Automatically detects and renders mathematical equations in LaTeX format as images.

**Supported Formats:**
- Display math: `$$E = mc^2$$`
- Code blocks:
  ````
  ```latex
  \frac{d}{dx}(x^2) = 2x
  ```
  ````
- LaTeX display: `\[integral equation\]`

The bot will automatically detect LaTeX in AI responses, render them as PNG images using matplotlib, and send them to Telegram.

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

### Image-Capable Models in Kiosk Mode

When using image-capable models (e.g., Gemini models with image generation) in kiosk mode, the bot automatically ensures responses include **both** images and explanatory text:

**Automatic Enhancements:**
1. **System Prompt Enhancement**: The system prompt is automatically enhanced with instructions to always provide both image and text
2. **User Prompt Enhancement**: When users request images (using keywords like "draw", "diagram", "illustrate"), their prompts are enhanced to explicitly request both components
3. **Response Validation**: If a model returns only an image without text, a fallback description is provided
4. **Reasoning Field Fallback**: Text explanations from the `reasoning` field (used by some models like Gemini) are automatically extracted

**Benefits for Educational Use:**
- Students receive visual aids with clear explanations
- Improves accessibility for all learning styles
- Ensures context is never lost when images are generated
- Supports the Socratic teaching method with visual + verbal guidance

## Installation

```bash
pip install -r requirements.txt
python3 ai-tgbot.py
```

## Testing

Run the test suite:
```bash
python3 tests/test_profiles.py
python3 tests/test_latex.py
python3 tests/test_integration.py
```

## Chat Logging

The bot supports chat logging with separate log levels for user and assistant messages. Add a `[logging]` section to your `kiosk.conf` file:

```ini
[logging]
# Values: off, minimum (text only), extended (text + attachments)
log_user_messages = minimum
log_assistant_messages = extended
log_directory = ./chat_logs
```

## Version History
- **1.9.0** - Profile system and LaTeX support merged with kiosk mode
- **1.8.0** - Ensure image-capable models in kiosk mode return both image and text
- **1.7.1** - Fix missing text description when image is generated
- **1.7.0** - Kiosk mode for locked-down dedicated instances
- **1.6.0** - Image in and out
- **1.5.0** - OpenRouter buttons
- **1.4.0** - GPT-4o-mini support and becomes the default
