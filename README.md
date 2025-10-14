# AITGChatBot

An AI LLM powered Telegram ChatBot with switchable backends; supports OpenAI, Anthropic (Claude), OpenRouter and Groq.

## Overview

AITGChatBot is a flexible Telegram bot that provides seamless access to multiple AI language models. Switch between different models on-the-fly, analyze images with vision-capable models, and generate images with AI - all through a simple conversational interface.

### Key Features

- 🤖 **Multiple AI Providers**: OpenAI (GPT-3.5, GPT-4, GPT-4o, GPT-4o-mini), Anthropic (Claude 3), Groq (Llama 3), and 100+ models via OpenRouter
- 🖼️ **Multimodal Support**: Image input (vision analysis) and image output (generation)
- 💬 **Smart Context Management**: Configurable conversation history with automatic context trimming
- 🔘 **Interactive Selection**: Button-based model selection for easy switching
- ⚡ **Fast & Efficient**: Optimized token usage and support for high-speed inference via Groq
- 🎯 **User-Friendly**: Simple commands and intuitive interface

### Quick Start

1. Set up environment variables for your API keys:
   - `BOT_KEY` - Telegram Bot Token
   - `API_KEY` - OpenAI API Key (optional)
   - `ANTHROPIC_API_KEY` - Anthropic API Key (optional)
   - `OPENROUTER_API_KEY` - OpenRouter API Key (optional)
   - `GROQ_API_KEY` - Groq API Key (optional)

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the bot:
   ```bash
   python ai-tgbot.py
   ```

### Available Commands

- `/help` - Show all available commands
- `/gpt4omini` - Use GPT-4o-mini (default, cost-effective)
- `/gpt4o` - Use GPT-4o (advanced reasoning and vision)
- `/claud3opus` - Use Claude 3 Opus (most intelligent)
- `/claud3haiku` - Use Claude 3 Haiku (fast and efficient)
- `/llama38b` / `/llama370b` - Use Llama 3 via Groq (fast, rate-limited)
- `/openrouter <model>` - Use any OpenRouter model
- `/listopenroutermodels` - List all available OpenRouter models
- `/status` - Check current model and settings
- `/clear` - Clear conversation context
- `/maxrounds <n>` - Set conversation history length

### Documentation

- **[Roadmap](roadmap.md)** - Project vision, planned features, and long-term goals
- **[TODO](TODO.md)** - Current work items and known issues
- **[Changelog](changelog.md)** - Version history and changes

### Current Version

**v1.6.0** - Multimodal support with image input and output

### Contributing

Contributions are welcome! Please see the [roadmap](roadmap.md) for planned features and areas where you can help.

### License

This project is open source. Please check the repository for license details.
