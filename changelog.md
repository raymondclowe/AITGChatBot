# Changelog

## [1.7.1] - 2025-12-21
### Fixed
- Fixed missing text description when images are generated via Google Gemini/OpenRouter
  - Added fallback to `reasoning` field when `content` is empty but `reasoning` contains explanatory text
  - This ensures users see both the generated image and the AI's explanation/description

### Removed
- Removed legacy ai-tgbot150.py (outdated implementation)
