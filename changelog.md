# Changelog

## [1.8.0] - 2025-12-21
### Added
- Enhanced kiosk mode to ensure image-capable models always return both image and text
  - Added `model_supports_image_output()` function to detect image generation capabilities
  - System prompts in kiosk mode are now automatically enhanced with instructions to provide both image and explanatory text
  - User prompts requesting images are enhanced to explicitly request both visual and text components
  - Added warning logging when images are generated without accompanying text
  - Ensures compliance with accessibility and clarity requirements for educational use cases

### Improved
- Better handling of multimodal responses in kiosk mode
- More robust detection of image request keywords in user messages
- Enhanced system prompt preservation during context clearing

## [1.7.1] - 2025-12-21
### Fixed
- Fixed missing text description when images are generated via Google Gemini/OpenRouter
  - Added fallback to `reasoning` field when `content` is empty but `reasoning` contains explanatory text
  - This ensures users see both the generated image and the AI's explanation/description

### Removed
- Removed legacy ai-tgbot150.py (outdated implementation)
