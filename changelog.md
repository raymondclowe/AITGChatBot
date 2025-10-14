# Changelog

All notable changes to AITGChatBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2025

### Added
- Image input support (vision analysis) for compatible models
- Image output support (generation) for compatible models
- Model capability detection for OpenRouter models
- Display of image capabilities in model listings
- Image support indicators (📷 for input, 🎨 for output)

### Changed
- Enhanced `/listopenroutermodels` to show image capabilities
- Improved `/status` command to display image capabilities
- Updated help text to include image feature documentation

## [1.5.0] - 2024

### Added
- Interactive button-based selection for OpenRouter models
- Improved model disambiguation with inline keyboards

### Changed
- `/openrouter` command now presents buttons when multiple models match
- Better UX for selecting from multiple matching models

### Fixed
- Issue with selecting models that are substrings of other model names

## [1.4.0] - 2024

### Added
- GPT-4o-mini support
- `/gpt4omini` command

### Changed
- Set GPT-4o-mini as the default model (cost-effective option)

## [1.3.0] - 2024

### Added
- OpenRouter substring matching
- Partial model name matching for easier selection

### Changed
- Improved model discovery and selection
- More flexible `/openrouter` command

## [1.2.0] - 2024

### Added
- GPT-4o support
- `/gpt4o` command

### Changed
- Set GPT-4o as default model
- Increased max tokens to 4K for OpenAI
- Increased max tokens to 8K for Groq
- Better token limit management

## [1.1.0] - 2024

### Added
- Llama3 support via Groq API
- `/llama38b` and `/llama370b` commands
- Fast inference with Groq backend

### Changed
- Added Groq as a supported backend

## [1.0.0] - 2024

### Added
- Initial release
- Telegram bot integration
- OpenAI GPT-3.5-turbo and GPT-4-turbo support
- Anthropic Claude 3 Opus and Haiku support
- OpenRouter integration for 100+ models
- Conversation context management
- `/help`, `/status`, `/clear` commands
- `/maxrounds` for configurable conversation history
- Model switching commands
- Session-based conversation tracking

---

For upcoming features and long-term plans, see [roadmap.md](roadmap.md)
