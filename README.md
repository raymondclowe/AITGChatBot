# AITGChatBot
An AI LLM powered Telegram ChatBot with switchable backends; supports OpenAI, Mistral, OpenRouter and Groq

## Features

### 🎭 Profile System (New in v1.7.0)
Switch between different AI personalities and configurations using profile files. Perfect for creating specialized assistants for different use cases.

**Available Commands:**
- `/activate <profile>` - Activate a profile
- `/listprofiles` - Show all available profiles  
- `/currentprofile` - Show current active profile
- `/deactivate` - Return to default configuration

**Included Profiles:**
- **pirate** - A fun pirate-themed assistant that speaks in pirate slang
- **tutor_ib** - An IB Math and Physics tutor using Socratic method

**Profile Format:**
Create your own `.profile` files in the `profiles/` directory:
```
Line 1: Model name (e.g., gpt-4o-mini, openrouter:anthropic/claude-3-opus)
Line 2: Greeting message
Line 3+: System prompt (can span multiple lines)
```

### 📐 LaTeX Support (New in v1.7.0)
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

The bot will automatically detect LaTeX in AI responses, render them as PNG images using matplotlib, and send them to Telegram with the original LaTeX as a caption.

### 🤖 Model Selection
Switch between different AI models on the fly:
- `/gpt3` - OpenAI GPT-3.5 Turbo
- `/gpt4` - OpenAI GPT-4 Turbo
- `/gpt4o` - OpenAI GPT-4o
- `/gpt4omini` - OpenAI GPT-4o Mini (default)
- `/claud3opus` - Anthropic Claude 3 Opus
- `/claud3haiku` - Anthropic Claude 3 Haiku
- `/llama38b` - Llama 3 8B via Groq
- `/llama370b` - Llama 3 70B via Groq
- `/openrouter <model>` - Any OpenRouter model
- `/listopenroutermodels` - List all available OpenRouter models

### 📷 Image Support
- Send images with text to vision-capable models for analysis
- Models with 📷 support image input (vision)
- Models with 🎨 support image output (generation)

### 💬 Conversation Management
- `/clear` - Clear conversation context
- `/maxrounds <n>` - Set maximum conversation rounds
- `/status` - Show current bot status
- `/help` - Display all available commands

## Installation

### Requirements
```bash
pip install -r requirements.txt
```

### Environment Variables
Set the following environment variables:
```bash
export BOT_KEY="your-telegram-bot-token"
export API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"  # Optional
export OPENROUTER_API_KEY="your-openrouter-api-key"  # Optional
export GROQ_API_KEY="your-groq-api-key"  # Optional
```

### Running the Bot
```bash
python3 ai-tgbot.py
```

## Testing

Run the test suite:
```bash
python3 tests/test_profiles.py
python3 tests/test_latex.py
```

## Version History
- **1.7.0** - Profile system and LaTeX support
- **1.6.0** - Image in and out
- **1.5.0** - OpenRouter buttons
- **1.4.0** - GPT-4o-mini support and becomes the default
- **1.3.0** - OpenRouter substring matches
- **1.2.0** - GPT-4o support and set to default, increase max tokens
- **1.1.0** - Llama3 using Groq
