# AITGChatBot
An AI LLM powered Telegram ChatBot with switchable backends; supports OpenAI, Mistral, OpenRouter and Groq

## Features

- Multiple AI backends: OpenAI (GPT-3.5, GPT-4, GPT-4o), Anthropic Claude, OpenRouter models, and Groq (Llama 3)
- Image input/output support for vision and image generation models
- Conversation history with configurable max rounds
- **Kiosk Mode** for locked-down, dedicated use cases
- **Extensible Plugin System** (v1.9.0+) for AI-powered customization in kiosk mode

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
- Only `/start`, `/help`, `/clear`, `/status`, and `/format` commands are available
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

**Example Interaction:**
```
Student: "Draw a diagram of the water cycle"
Bot Response: 
  [Generated image of water cycle]
  "This diagram shows the water cycle with four main stages: evaporation 
   from bodies of water, condensation in clouds, precipitation as rain, 
   and collection back into water bodies."
```

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

## Plugin System (v1.9.0+)

The plugin system enables powerful, AI-driven customization of kiosk mode through a flexible hook architecture. Plugins can transform messages, add features, and integrate external services.

### Overview

The plugin system provides:
- **10 fine-grained hooks** for message transformation at every stage
- **AI helper utilities** for calling vision models, expanding captions, etc.
- **Robust error handling** with timeouts and automatic plugin disabling on failures
- **Rich context** passed to every hook with session data, history, metadata
- **Easy development** with base class, comprehensive docs, and examples

### Quick Start

1. **Enable plugins** in `kiosk.conf`:
```ini
[PluginConfig]
enabled = true
timeout = 5.0
max_failures = 3
debug = false
```

2. **Create your plugin** (`kiosk-custom.py`):
```python
from kiosk_plugin_base import KioskPlugin

class MyPlugin(KioskPlugin):
    def pre_user_text(self, text, context):
        # Transform user input before processing
        return text.strip().lower()
    
    def post_assistant_text(self, text, context):
        # Modify bot responses before sending
        return text + "\n\nPowered by AI"
    
    # Implement all 10 hooks (can be pass-through)
    def post_user_text(self, text, context): return text
    def pre_user_images(self, images, text, context): return images
    def post_user_images(self, images, text, context): return images
    def pre_assistant_text(self, text, context): return text
    def pre_assistant_images(self, images, text, context): return images
    def post_assistant_images(self, images, text, context): return images
    def on_session_start(self, context): pass
    def on_message_complete(self, context): pass
```

3. **Restart the bot** to load the plugin

### Hook Reference

All hooks receive a `context` dict with:
- `session_data` - Full session data (use carefully!)
- `chat_id` - Current chat/session ID
- `history` - Conversation history
- `metadata` - Plugin-specific metadata dict (for storing state)
- `ai_helper` - PluginAIHelper instance for AI calls
- `model` - Current model name
- `kiosk_mode` - Always True (plugins only work in kiosk mode)

#### Text Processing Hooks

**`pre_user_text(text, context) -> str`**
- Called: Immediately after receiving user message
- Use for: Input validation, profanity filtering, preprocessing

**`post_user_text(text, context) -> str`**
- Called: After prompt enhancement, before sending to AI
- Use for: Adding context, modifying prompts

**`pre_assistant_text(text, context) -> str`**
- Called: Immediately after receiving AI response
- Use for: Detecting patterns (LaTeX, code blocks), metadata extraction

**`post_assistant_text(text, context) -> str`**
- Called: Before sending response to user
- Use for: Formatting, adding disclaimers, replacing placeholders

#### Image Processing Hooks

**`pre_user_images(images: List[str], text, context) -> List[str]`**
- Called: After receiving images, before adding to message
- Images are base64-encoded strings
- Use for: AI-powered caption expansion, image validation

**`post_user_images(images, text, context) -> List[str]`**
- Called: After adding images to message, before sending to AI
- Use for: Image preprocessing, adding watermarks

**`pre_assistant_images(images, text, context) -> List[str]`**
- Called: Immediately after receiving AI-generated images
- Use for: Rendering LaTeX formulas as images, adding visualizations

**`post_assistant_images(images, text, context) -> List[str]`**
- Called: Before sending images to user
- Use for: Adding generated images (syntax highlighting), postprocessing

#### Lifecycle Hooks

**`on_session_start(context) -> None`**
- Called: When a new session is initialized
- Use for: Setup, initialization, welcome logic, analytics

**`on_message_complete(context) -> None`**
- Called: After complete user+assistant exchange
- Use for: Logging, analytics, cleanup, state updates

### Custom Slash Commands

Plugins can register custom slash commands that execute arbitrary code. Commands work in both kiosk and regular modes.

**`get_commands() -> Dict[str, Dict[str, Any]]`**
- Returns: Dictionary mapping command names to command info
- Called: Once during plugin initialization

```python
def get_commands(self):
    return {
        'generate-worksheets': {
            'description': 'Generate practice worksheets',
            'handler': self.handle_generate_worksheets,
            'available_in_kiosk': True
        }
    }

def handle_generate_worksheets(self, chat_id, context):
    # Send initial status message
    self.send_message(chat_id, "📝 Generating... Please wait.", context)
    
    # Use AI to generate content
    ai_helper = context['ai_helper']
    worksheet = ai_helper.quick_call(
        system="Create educational worksheets",
        user="Generate 5 math problems"
    )
    
    # Create HTML document
    html_content = f"<html><body>{worksheet}</body></html>"
    html_bytes = html_content.encode('utf-8')
    
    # Send as downloadable file
    self.send_document(
        chat_id, 
        html_bytes,
        'worksheet.html',
        '✅ Here is your worksheet!',
        context
    )
```

**Helper methods for commands:**
- `send_message(chat_id, text, context)` - Send text messages
- `send_document(chat_id, data, filename, caption, context)` - Send files/documents

Commands automatically appear in `/help` and are available immediately after plugin loads.

### AI Helper API

The `ai_helper` object provides utilities for plugin development:

```python
# Call AI with text and/or images
response = context['ai_helper'].call_ai(
    prompt="Describe this image",
    model="gpt-4o-mini",  # Optional, defaults to gpt-4o-mini
    max_tokens=500,
    images=["base64_img_data"]  # Optional list
)

# Quick system+user message call
response = context['ai_helper'].quick_call(
    system="You are a helpful assistant",
    user="What is 2+2?",
    model="gpt-4o-mini"  # Optional
)

# Convert between PIL and base64 (requires Pillow)
pil_image = context['ai_helper'].base64_to_pil(base64_string)
base64_string = context['ai_helper'].pil_to_base64(pil_image, format='PNG')
```

### Example: Caption Expansion Plugin

```python
from kiosk_plugin_base import KioskPlugin

class CaptionExpander(KioskPlugin):
    def pre_user_images(self, images, text, context):
        """Auto-expand brief captions using AI vision"""
        if images and len(text.strip()) < 20:
            ai_helper = context['ai_helper']
            description = ai_helper.call_ai(
                prompt="Describe this image briefly (1-2 sentences)",
                model="gpt-4o-mini",
                max_tokens=150,
                images=[images[0]]
            )
            if description:
                # Store for later use
                context['metadata']['ai_caption'] = description
                print(f"[Plugin] Generated caption: {description[:50]}...")
        return images
    
    # ... implement other hooks as pass-through ...
```

### Example Plugin Features

See `kiosk-custom.py.example` for a full-featured plugin demonstrating:

1. **AI Vision Caption Expansion** - Auto-describe images with brief/no text
2. **LaTeX Rendering** - Detect `$formula$` and render to images
3. **Syntax Highlighting** - Render code blocks as highlighted images
4. **Profanity Filter** - Basic word filtering on user input
5. **Analytics** - Track message counts and usage in metadata
6. **Custom Commands** - `/generate-worksheets` and `/summary` commands that:
   - Send multiple progress messages
   - Use AI to analyze conversation history
   - Generate and send HTML documents
   - Work in both kiosk and regular modes

All features gracefully degrade if dependencies (matplotlib, pygments) are missing.

### Configuration

```ini
[PluginConfig]
# Enable/disable plugin system
enabled = true

# Maximum hook execution time (seconds)
timeout = 5.0

# Max failures before auto-disable
max_failures = 3

# Debug logging for plugin execution
debug = false
```

### Testing

Run the comprehensive test suite:
```bash
python test_kiosk_plugin.py
```

Tests cover:
- Plugin base class structure
- Hook invocation and data transformation
- Error handling and timeout behavior
- AI helper utilities
- Health monitoring
- Context building
- Full pipeline integration

### Security & Best Practices

1. **Timeout Protection** - All hooks have 5s default timeout to prevent hanging
2. **Error Isolation** - Plugin errors won't crash the bot; original data passes through
3. **Health Monitoring** - Plugins auto-disable after repeated failures
4. **No Arbitrary Imports** - Plugin file is loaded directly, not via exec()
5. **Context Immutability** - Avoid mutating session_data directly; use metadata dict
6. **Graceful Degradation** - Handle missing dependencies cleanly

### Advanced Usage

**Using Metadata for State:**
```python
def on_session_start(self, context):
    context['metadata']['message_count'] = 0
    context['metadata']['images_processed'] = 0

def on_message_complete(self, context):
    context['metadata']['message_count'] += 1
```

**Chaining Transformations:**
```python
def pre_assistant_text(self, text, context):
    # Detect LaTeX formulas
    context['metadata']['has_latex'] = '$$' in text
    return text

def pre_assistant_images(self, images, text, context):
    # Render formulas if detected
    if context['metadata'].get('has_latex'):
        rendered = self._render_latex_formulas(text)
        images.extend(rendered)
    return images
```

**Conditional Processing:**
```python
def post_user_text(self, text, context):
    # Only process for certain users or sessions
    if context['chat_id'] in self.premium_users:
        return self.enhance_premium(text)
    return text
```

### Troubleshooting

**Plugin not loading:**
- Check file is named exactly `kiosk-custom.py`
- Ensure plugin class inherits from `KioskPlugin`
- Verify all 10 methods are implemented
- Check console for error messages

**Plugin disabled automatically:**
- Check logs for error messages
- Verify hooks don't exceed timeout
- Ensure no uncaught exceptions
- Increase `max_failures` if needed

**AI helper not working:**
- Verify `OPENROUTER_API_KEY` is set
- Check network connectivity
- Review debug logs for API errors

## Commands

### Standard Mode
- `/help` - Show help message
- `/clear` - Clear conversation context
- `/status` - Show current chatbot status
- `/format <modality> [aspect_ratio] [image_size]` - Control what model generates (see below)
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
- `/format <modality> [aspect_ratio] [image_size]` - Control what model generates (see below)

### Format Command - Controlling Model Output

The `/format` command controls **what you ask the model to generate** via the OpenRouter API's `modalities` and `image_config` parameters. The user always sees everything the model returns (except duplicates).

**Modalities** (what to request from the model):
- `auto` (default) - Let the model decide
- `text` - Request text-only responses
- `image` - Request image-only responses  
- `text+image` - Request both text and image

**Aspect Ratios** (optional, for Gemini models):
- `1:1`, `16:9`, `9:16`, `4:3`, `3:4`

**Image Sizes** (optional, for Gemini models):
- `SD`, `HD`, `4K`

**Example Usage:**
```
/format text+image          # Request both text and image
/format image 16:9 4K       # Request 4K image with 16:9 aspect ratio
/format text+image 1:1 HD   # Request both, with 1:1 HD image
/format auto                # Let model decide
```

Use `/format` without arguments to see current settings.
Use `/status` to see your current format configuration.

## Developer Notes

### Image Generation and Multimodal Responses

#### Text + Image Response Enforcement (v1.8.0+)

When using image-capable models (models that can generate images) in **kiosk mode**, the bot automatically ensures that responses always include both images and explanatory text:

**Implementation Details:**

1. **Model Detection**: The `model_supports_image_output()` function checks if a model supports image generation by querying the OpenRouter API capabilities cache.

2. **System Prompt Enhancement**: When initializing a session with an image-capable model in kiosk mode, the system prompt is automatically enhanced with explicit instructions:
   ```
   **IMPORTANT**: When generating images, always provide BOTH:
   1. A generated image that directly addresses the request
   2. A clear text explanation (1-3 sentences) describing what the image shows
   Never generate only an image without accompanying text explanation.
   ```

3. **User Prompt Enhancement**: When users request images (detected via keywords like "draw", "diagram", "illustrate"), their prompts are automatically enhanced with:
   ```
   (Please provide both a visual representation AND a text explanation.)
   ```

4. **Response Parsing**:
   - Primary: Extract text from `content` field
   - If no text in content but images exist, only images are shown
   - In kiosk mode with image-capable models, if images exist but no text, provide placeholder: "(Image generated without text description)"
   - Note: The `reasoning` field (which contains internal model thinking) is intentionally NOT used

5. **Image Request Keywords**: The following keywords trigger user prompt enhancement:
   - `draw`, `sketch`, `diagram`, `illustrate`, `visualize`, `show me`
   - `picture`, `image`, `graph`, `chart`, `plot`, `create`
   - `generate`, `make`, `design`

**Testing**: Run `python test_image_text_kiosk.py` to validate the implementation.

#### Image Generation Response Handling

When using image-capable models like Google Gemini via OpenRouter for image generation, the API returns responses in the following format:

- **Text responses**: Text content is in the `content` field
- **Image responses**: Images are returned in a separate array, with text description in the `content` field
- **Internal reasoning**: Some models include a `reasoning` field with internal thinking - this is NOT shown to users

The bot handles responses by:
1. Extracting text from the `content` field (primary source)
2. Extracting images from the dedicated images array
3. In kiosk mode, providing a placeholder if images exist without text description
4. Never displaying the `reasoning` field (which contains internal model thinking, not user-facing content)

This ensures users see the actual response content without being confused by internal model reasoning.
