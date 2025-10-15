
# AITGChatBot Roadmap

## 1. LaTeX Support for Math Formulas

### Overview
Enable the chatbot to detect, parse, and render mathematical formulas written in LaTeX notation, providing visual output for complex equations.

### Features

- **Detect and Render LaTeX:**
  - When the AI outputs LaTeX formulas, recognize them and wrap them in distinct markdown code blocks (```) or XML tags.
  - Example:
    ```latex
    E = mc^2
    ```
  - Ensure the block stands alone for clear rendering.

- **System Image Rendering:**
  - Parse LaTeX blocks, render them to images, and output the image as a new chat message.
  - After the image, continue with the rest of the text (and handle multiple LaTeX blocks per message).

### Implementation Details

**LaTeX Detection Pattern:**
```python
import re

def detect_latex_blocks(text):
    """
    Detect LaTeX blocks in text using multiple patterns.
    Returns list of tuples: (start_pos, end_pos, latex_content)
    """
    patterns = [
        r'```latex\n(.*?)\n```',  # Code block format
        r'\$\$(.*?)\$\$',          # Display math format
        r'\\\[(.*?)\\\]',          # LaTeX display format
    ]
    
    latex_blocks = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            latex_blocks.append({
                'start': match.start(),
                'end': match.end(),
                'content': match.group(1).strip(),
                'full_match': match.group(0)
            })
    
    # Sort by position
    latex_blocks.sort(key=lambda x: x['start'])
    return latex_blocks

# Example usage:
response_text = "The equation is: ```latex\nE = mc^2\n``` and momentum is $$p = mv$$"
blocks = detect_latex_blocks(response_text)
```

**Rendering LaTeX to Images:**
```python
import subprocess
import tempfile
import os
from PIL import Image

def render_latex_to_image(latex_code, output_path, dpi=300):
    """
    Render LaTeX code to PNG image using matplotlib or external tools.
    
    Args:
        latex_code: The LaTeX mathematical expression
        output_path: Where to save the rendered image
        dpi: Resolution of the output image
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Method 1: Using matplotlib (simpler, included in requirements)
        import matplotlib.pyplot as plt
        import matplotlib as mpl
        
        mpl.rcParams['mathtext.fontset'] = 'cm'
        mpl.rcParams['mathtext.rm'] = 'serif'
        
        fig = plt.figure(figsize=(10, 2))
        fig.patch.set_facecolor('white')
        text = fig.text(0.5, 0.5, f'${latex_code}$', 
                       fontsize=20, ha='center', va='center')
        
        # Adjust figure size to fit text
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                   pad_inches=0.1, facecolor='white')
        plt.close(fig)
        return True
        
    except Exception as e:
        print(f"Error rendering LaTeX: {e}")
        return False

# Alternative Method 2: Using LaTeX and dvipng (more powerful but requires system LaTeX)
def render_latex_advanced(latex_code, output_path):
    """
    Render using actual LaTeX engine (requires latex and dvipng installed).
    More accurate for complex formulas.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, 'equation.tex')
            
            # Create complete LaTeX document
            tex_content = r"""\documentclass[12pt]{article}
\usepackage{amsmath}
\usepackage{amssymb}
\pagestyle{empty}
\begin{document}
\begin{displaymath}
""" + latex_code + r"""
\end{displaymath}
\end{document}"""
            
            with open(tex_file, 'w') as f:
                f.write(tex_content)
            
            # Compile LaTeX to DVI
            subprocess.run(['latex', '-interaction=nonstopmode', 'equation.tex'],
                         cwd=tmpdir, capture_output=True, check=True)
            
            # Convert DVI to PNG
            subprocess.run(['dvipng', '-D', '300', '-T', 'tight', 
                          '-o', output_path, 'equation.dvi'],
                         cwd=tmpdir, capture_output=True, check=True)
            
            return True
    except Exception as e:
        print(f"Advanced LaTeX rendering failed: {e}")
        return False
```

**Integration with Bot Message Flow:**
```python
def process_ai_response(response_text, chat_id):
    """
    Process AI response, extract LaTeX, render to images, and send messages.
    """
    latex_blocks = detect_latex_blocks(response_text)
    
    if not latex_blocks:
        # No LaTeX, send as normal text
        send_message(chat_id, response_text)
        return
    
    # Split text around LaTeX blocks and send sequentially
    last_pos = 0
    
    for i, block in enumerate(latex_blocks):
        # Send text before this LaTeX block
        if block['start'] > last_pos:
            text_before = response_text[last_pos:block['start']].strip()
            if text_before:
                send_message(chat_id, text_before)
        
        # Render and send LaTeX as image
        image_path = f"/tmp/latex_{chat_id}_{i}.png"
        if render_latex_to_image(block['content'], image_path):
            send_photo(chat_id, image_path)
            # Optionally send the LaTeX code as caption or separate message
            send_message(chat_id, f"```latex\n{block['content']}\n```")
            os.remove(image_path)
        else:
            # Fallback: send as code block if rendering fails
            send_message(chat_id, f"```latex\n{block['content']}\n```")
        
        last_pos = block['end']
    
    # Send any remaining text after last LaTeX block
    if last_pos < len(response_text):
        text_after = response_text[last_pos:].strip()
        if text_after:
            send_message(chat_id, text_after)
```

### Watch Points & Considerations

1. **LaTeX Syntax Errors:**
   - Invalid LaTeX will cause rendering to fail
   - Implement error handling and fallback to display raw LaTeX code
   - Consider validation before rendering: basic syntax check

2. **Performance Concerns:**
   - Rendering LaTeX can be slow (200ms - 2s per image)
   - Use async rendering to avoid blocking the bot
   - Cache rendered equations if the same formula appears multiple times
   - Implement timeout (5 seconds max) for rendering operations

3. **Security:**
   - LaTeX can execute system commands in some configurations
   - Sanitize LaTeX input to prevent injection attacks
   - Use restricted LaTeX mode or sandbox the rendering process
   - Blacklist dangerous commands: `\input`, `\write`, `\immediate`, `\openout`

4. **System Dependencies:**
   - matplotlib method: Only requires Python packages (simpler)
   - Advanced method: Requires LaTeX distribution (`texlive`, `dvipng`)
   - Document installation requirements clearly
   - Provide graceful degradation if dependencies missing

5. **Telegram-Specific Considerations:**
   - Image size limits: Keep under 10MB
   - Use appropriate DPI (300 recommended, 600 for complex formulas)
   - Consider using PNG for transparency
   - Set proper MIME types when sending images

6. **User Experience:**
   - Show "Rendering equation..." status while processing
   - Include original LaTeX as image caption for reference
   - Handle multiple equations in single message correctly
   - Preserve message order (text before, image, text after)

7. **Edge Cases:**
   - Empty LaTeX blocks
   - Nested or overlapping patterns
   - Very long equations (split or scale appropriately)
   - Unicode characters in LaTeX

### Required Dependencies

Add to `requirements.txt`:
```
matplotlib>=3.5.0
Pillow>=9.0.0
numpy>=1.21.0
```

Optional for advanced rendering:
```bash
# Ubuntu/Debian
sudo apt-get install texlive texlive-latex-extra dvipng

# MacOS
brew install --cask mactex
brew install dvipng
```

### Testing Strategy

```python
# Test cases to implement
test_cases = [
    # Simple equation
    ("E = mc^2", True),
    
    # Fraction
    (r"\frac{a}{b}", True),
    
    # Integral
    (r"\int_0^1 x^2 dx", True),
    
    # Matrix
    (r"\begin{matrix} 1 & 2 \\ 3 & 4 \end{matrix}", True),
    
    # Invalid LaTeX (should fail gracefully)
    (r"\invalid{command}", False),
    
    # Multiple equations in text
    ("First $$x^2$$ then $$y^3$$", True),
]
```

## 2. Profile Activation via Command

### Overview
Allow users to switch between different AI personalities and configurations using profile files, enabling use cases like educational tutors, technical assistants, or entertainment bots.

### Features

- **/activate Command:**
  - Implement a `/activate <filename>` command to load a profile from a text file.
  - The file format:
    1. **First line:** OpenRouter model name (e.g., gpt-3.5-turbo)
    2. **Second line:** Initial greeting
    3. **Third line onward:** System prompt (can be multiple lines)

- **Profile Management:**
  - Save loaded profiles as `<profile name>.profile`.
  - Switching profiles loads corresponding model and prompt.

### Implementation Details

**Profile File Format Example:**

`pirate.profile`:
```
gpt-4o-mini
Ahoy matey! I be yer friendly AI pirate! What can I help ye with today?
You are a helpful AI assistant who speaks like a pirate. Use pirate slang and terminology in all your responses. Be playful and entertaining while still providing accurate information. End responses with "Arrr!" when appropriate.
```

`tutor.profile`:
```
openrouter:anthropic/claude-3-opus
Hello! I'm your IB Math and Physics tutor. How can I help you today?
You are an experienced IB (International Baccalaureate) Math and Physics tutor. Your role is to:
- Help students understand complex concepts by breaking them down
- Guide them through problem-solving rather than just giving answers
- Identify and address gaps in understanding
- Use analogies and examples appropriate for high school level
- Encourage critical thinking and mathematical reasoning
- Be patient and supportive
When a student asks a question, first assess their understanding, then guide them step by step.
```

**Profile Loader Implementation:**
```python
import os

PROFILE_DIR = "./profiles"  # Directory to store profile files

def load_profile(profile_name, chat_id):
    """
    Load a profile from file and apply it to the session.
    
    Args:
        profile_name: Name of profile file (with or without .profile extension)
        chat_id: Telegram chat ID to apply profile to
    
    Returns:
        tuple: (success: bool, message: str, greeting: str)
    """
    # Ensure .profile extension
    if not profile_name.endswith('.profile'):
        profile_name += '.profile'
    
    profile_path = os.path.join(PROFILE_DIR, profile_name)
    
    if not os.path.exists(profile_path):
        return False, f"Profile '{profile_name}' not found.", None
    
    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if len(lines) < 3:
            return False, "Invalid profile format. Needs at least 3 lines.", None
        
        # Parse profile components
        model = lines[0].strip()
        greeting = lines[1].strip()
        system_prompt = ''.join(lines[2:]).strip()
        
        # Validate model name
        if not is_valid_model(model):
            return False, f"Invalid model specified: {model}", None
        
        # Clear existing conversation and apply new profile
        session_data[chat_id]['CONVERSATION'] = []
        session_data[chat_id]['model_version'] = model
        session_data[chat_id]['profile_name'] = profile_name
        
        # Add system prompt as first message
        session_data[chat_id]['CONVERSATION'].append({
            'role': 'system',
            'content': [{'type': 'text', 'text': system_prompt}]
        })
        
        return True, f"Profile '{profile_name}' activated successfully.", greeting
        
    except Exception as e:
        return False, f"Error loading profile: {str(e)}", None

def is_valid_model(model_name):
    """Validate that model name is supported."""
    valid_prefixes = ['gpt-', 'claude-', 'llama', 'openrouter:']
    return any(model_name.startswith(prefix) for prefix in valid_prefixes)

def list_available_profiles():
    """List all available profile files."""
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR)
        return []
    
    profiles = []
    for filename in os.listdir(PROFILE_DIR):
        if filename.endswith('.profile'):
            profiles.append(filename)
    
    return sorted(profiles)

def create_profile(profile_name, model, greeting, system_prompt):
    """
    Create a new profile file.
    
    Args:
        profile_name: Name for the profile
        model: Model identifier
        greeting: Initial greeting message
        system_prompt: System prompt (can be multi-line)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not os.path.exists(PROFILE_DIR):
        os.makedirs(PROFILE_DIR)
    
    if not profile_name.endswith('.profile'):
        profile_name += '.profile'
    
    profile_path = os.path.join(PROFILE_DIR, profile_name)
    
    if os.path.exists(profile_path):
        return False, f"Profile '{profile_name}' already exists."
    
    try:
        with open(profile_path, 'w', encoding='utf-8') as f:
            f.write(f"{model}\n")
            f.write(f"{greeting}\n")
            f.write(f"{system_prompt}\n")
        
        return True, f"Profile '{profile_name}' created successfully."
    except Exception as e:
        return False, f"Error creating profile: {str(e)}"
```

**Bot Command Integration:**
```python
def long_polling():
    # ... existing polling code ...
    
    # Add to command handling section
    if message_text.startswith('/activate'):
        parts = message_text.split(maxsplit=1)
        
        if len(parts) < 2:
            # List available profiles
            profiles = list_available_profiles()
            if profiles:
                reply = "Available profiles:\n"
                reply += "\n".join([f"• {p.replace('.profile', '')}" for p in profiles])
                reply += "\n\nUse: /activate <profile_name>"
            else:
                reply = "No profiles available. Create one using /createprofile"
            send_message(chat_id, reply)
            continue
        
        profile_name = parts[1]
        success, message, greeting = load_profile(profile_name, chat_id)
        
        send_message(chat_id, message)
        if success and greeting:
            send_message(chat_id, greeting)
        continue
    
    if message_text.startswith('/listprofiles'):
        profiles = list_available_profiles()
        if profiles:
            reply = "📋 Available profiles:\n\n"
            for profile in profiles:
                name = profile.replace('.profile', '')
                reply += f"• {name}\n"
            reply += "\n💡 Use: /activate <profile_name>"
        else:
            reply = "No profiles found. Create one using /createprofile"
        send_message(chat_id, reply)
        continue
    
    if message_text.startswith('/currentprofile'):
        profile_name = session_data[chat_id].get('profile_name', 'None')
        model = session_data[chat_id].get('model_version', 'Unknown')
        reply = f"Current Profile: {profile_name}\n"
        reply += f"Model: {model}"
        send_message(chat_id, reply)
        continue
```

**Profile Creation Wizard:**
```python
# Add to session data
session_data[chat_id]['creating_profile'] = {
    'state': None,  # 'awaiting_name', 'awaiting_model', 'awaiting_greeting', 'awaiting_prompt'
    'data': {}
}

def handle_profile_creation(chat_id, message_text):
    """Handle multi-step profile creation process."""
    state_data = session_data[chat_id]['creating_profile']
    
    if state_data['state'] == 'awaiting_name':
        state_data['data']['name'] = message_text
        state_data['state'] = 'awaiting_model'
        send_message(chat_id, 
            "Enter the model name (e.g., gpt-4o-mini, openrouter:anthropic/claude-3-opus):")
        
    elif state_data['state'] == 'awaiting_model':
        if not is_valid_model(message_text):
            send_message(chat_id, 
                "Invalid model. Please enter a valid model name:")
            return
        state_data['data']['model'] = message_text
        state_data['state'] = 'awaiting_greeting'
        send_message(chat_id, "Enter the greeting message:")
        
    elif state_data['state'] == 'awaiting_greeting':
        state_data['data']['greeting'] = message_text
        state_data['state'] = 'awaiting_prompt'
        send_message(chat_id, 
            "Enter the system prompt (can be multiple paragraphs). "
            "Send /done when finished:")
        state_data['data']['prompt_lines'] = []
        
    elif state_data['state'] == 'awaiting_prompt':
        if message_text == '/done':
            # Create the profile
            success, msg = create_profile(
                state_data['data']['name'],
                state_data['data']['model'],
                state_data['data']['greeting'],
                '\n'.join(state_data['data']['prompt_lines'])
            )
            send_message(chat_id, msg)
            state_data['state'] = None
        else:
            state_data['data']['prompt_lines'].append(message_text)
            send_message(chat_id, "Prompt recorded. Continue or send /done to finish.")
```

### Watch Points & Considerations

1. **File System Security:**
   - Validate profile names to prevent directory traversal (e.g., `../../../etc/passwd`)
   - Use whitelist for allowed characters: `[a-zA-Z0-9_-]`
   - Store profiles in dedicated directory with restricted permissions
   - Never execute or eval() content from profile files

2. **Profile Validation:**
   - Check model exists and is available before activation
   - Validate greeting and prompt aren't empty
   - Enforce maximum length limits (prompt < 4000 chars)
   - Handle malformed UTF-8 encoding gracefully

3. **Session State Management:**
   - Clear conversation history when switching profiles to avoid context confusion
   - Store current profile name in session for reference
   - Handle case where user switches profiles mid-conversation
   - Preserve profile choice across bot restarts (optional persistence)

4. **User Experience:**
   - Provide clear feedback when profile loads successfully
   - Show greeting message immediately after activation
   - Display current profile in `/status` command
   - Allow easy switching between profiles without data loss concerns

5. **System Prompt Injection:**
   - System prompts are powerful - users could create profiles that override safety guidelines
   - Consider admin-only profile creation or approval system
   - Monitor for prompts that attempt jailbreaks or inappropriate behavior
   - Document acceptable use policy for profiles

6. **Model Compatibility:**
   - Not all models support system messages (some only support user/assistant)
   - Handle gracefully when model doesn't support system role
   - Convert system message to user message with special formatting if needed

7. **Profile Naming Conflicts:**
   - Handle duplicate profile names
   - Provide versioning or overwrite confirmation
   - Case-sensitive vs case-insensitive file systems

8. **Memory and Resource Usage:**
   - Long system prompts consume token budget
   - Account for system prompt tokens in max_rounds calculation
   - Consider caching profile data in memory vs reading from disk each time

### Commands to Implement

```python
# Add to help text
reply_text += "/activate <profile> - activate a profile\n"
reply_text += "/listprofiles - show all available profiles\n"
reply_text += "/currentprofile - show current active profile\n"
reply_text += "/createprofile - start profile creation wizard (admin only)\n"
reply_text += "/deactivate - return to default configuration\n"
```

### Testing Strategy

```python
# Test cases
def test_profile_loading():
    # Test valid profile
    success, msg, greeting = load_profile("test.profile", "test_chat")
    assert success == True
    
    # Test non-existent profile
    success, msg, greeting = load_profile("nonexistent.profile", "test_chat")
    assert success == False
    
    # Test malformed profile
    # Test profile with invalid model
    # Test profile with special characters
    # Test profile switching mid-conversation
```

## 3. Dynamic Model Selection Based on Constraints

### Overview
Automatically select the optimal AI model based on specified constraints and requirements, allowing intelligent model switching based on task requirements, budget, and capabilities.

### Features

- **Profile-based Model Rules:**
  - For each profile, allow an associated `.ai` file that specifies constraints for model selection, e.g.:
    - Must support image input
    - Top by popularity
    - Cost per token < $0.10
  - Use these constraints to automatically choose the best model from OpenRouter's available list for that profile.

### Implementation Details

**Constraint File Format (`.ai` files):**

`tutor.ai`:
```json
{
  "constraints": {
    "capabilities": {
      "image_input": true,
      "context_length_min": 8000
    },
    "cost": {
      "max_prompt_cost": 0.10,
      "max_completion_cost": 0.30,
      "currency": "USD_per_1M_tokens"
    },
    "performance": {
      "min_tokens_per_second": 50
    },
    "quality": {
      "sort_by": "popularity",
      "min_context_length": 8000
    }
  },
  "preferences": {
    "provider_preference": ["anthropic", "openai", "google"],
    "model_preference": ["claude", "gpt-4"],
    "avoid_models": ["gpt-3.5-turbo"]
  },
  "fallback": {
    "model": "gpt-4o-mini",
    "on_error": "use_default"
  }
}
```

**Simpler YAML Format Alternative:**

`pirate.ai`:
```yaml
# AI Model Constraints for Pirate Profile
capabilities:
  image_input: false
  image_output: false
  min_context_length: 4000

cost:
  max_cost_per_1m_tokens: 5.00  # USD
  prefer_cheaper: true

quality:
  sort_by: "quality"  # or "speed", "popularity", "cost"
  prefer_newer_models: true

preferences:
  providers: [openai, anthropic]
  avoid_models: []

fallback:
  model: gpt-4o-mini
```

**Model Selector Implementation:**
```python
import json
import requests
from typing import Dict, List, Optional

class ModelSelector:
    """Select optimal model based on constraints."""
    
    def __init__(self):
        self.models_cache = None
        self.cache_timestamp = None
        self.CACHE_TTL = 3600  # 1 hour
    
    def get_available_models(self) -> List[Dict]:
        """Fetch available models from OpenRouter."""
        import time
        
        # Check cache
        if (self.models_cache and self.cache_timestamp and 
            time.time() - self.cache_timestamp < self.CACHE_TTL):
            return self.models_cache
        
        try:
            response = requests.get(
                'https://openrouter.ai/api/v1/models',
                timeout=10
            )
            if response.status_code == 200:
                self.models_cache = response.json()['data']
                self.cache_timestamp = time.time()
                return self.models_cache
        except Exception as e:
            print(f"Error fetching models: {e}")
        
        return []
    
    def load_constraints(self, profile_name: str) -> Optional[Dict]:
        """Load constraint file for a profile."""
        ai_file = f"./profiles/{profile_name}.ai"
        
        if not os.path.exists(ai_file):
            return None
        
        try:
            with open(ai_file, 'r') as f:
                if ai_file.endswith('.json'):
                    return json.load(f)
                elif ai_file.endswith('.yaml'):
                    import yaml
                    return yaml.safe_load(f)
                else:
                    # Try JSON first
                    return json.load(f)
        except Exception as e:
            print(f"Error loading constraints: {e}")
            return None
    
    def filter_by_capabilities(self, models: List[Dict], 
                              constraints: Dict) -> List[Dict]:
        """Filter models by capability requirements."""
        if 'capabilities' not in constraints:
            return models
        
        caps = constraints['capabilities']
        filtered = []
        
        for model in models:
            # Check image input capability
            if caps.get('image_input'):
                modalities = model.get('architecture', {}).get('modality', '')
                if 'image' not in modalities.lower():
                    continue
            
            # Check context length
            min_context = caps.get('context_length_min', 0)
            if model.get('context_length', 0) < min_context:
                continue
            
            # Check image output capability
            if caps.get('image_output'):
                # Check if model supports image generation
                if not model.get('supports_image_output', False):
                    continue
            
            filtered.append(model)
        
        return filtered
    
    def filter_by_cost(self, models: List[Dict], 
                      constraints: Dict) -> List[Dict]:
        """Filter models by cost constraints."""
        if 'cost' not in constraints:
            return models
        
        cost_constraints = constraints['cost']
        max_prompt = cost_constraints.get('max_prompt_cost', float('inf'))
        max_completion = cost_constraints.get('max_completion_cost', float('inf'))
        
        filtered = []
        for model in models:
            pricing = model.get('pricing', {})
            
            # Convert pricing to per 1M tokens
            prompt_cost = float(pricing.get('prompt', 0)) * 1_000_000
            completion_cost = float(pricing.get('completion', 0)) * 1_000_000
            
            if prompt_cost <= max_prompt and completion_cost <= max_completion:
                filtered.append(model)
        
        return filtered
    
    def apply_preferences(self, models: List[Dict], 
                         constraints: Dict) -> List[Dict]:
        """Apply preference ordering to models."""
        if 'preferences' not in constraints:
            return models
        
        prefs = constraints['preferences']
        
        # Filter out avoided models
        avoid_models = prefs.get('avoid_models', [])
        if avoid_models:
            models = [m for m in models 
                     if not any(avoid in m['id'] for avoid in avoid_models)]
        
        # Sort by provider preference
        provider_pref = prefs.get('provider_preference', [])
        if provider_pref:
            def provider_score(model):
                model_id = model['id']
                for idx, provider in enumerate(provider_pref):
                    if provider in model_id:
                        return idx
                return len(provider_pref)
            
            models = sorted(models, key=provider_score)
        
        return models
    
    def rank_by_quality(self, models: List[Dict], 
                       constraints: Dict) -> List[Dict]:
        """Rank models by quality metrics."""
        quality = constraints.get('quality', {})
        sort_by = quality.get('sort_by', 'popularity')
        
        if sort_by == 'popularity':
            # Use OpenRouter's ranking/popularity
            models = sorted(models, 
                          key=lambda m: m.get('top_provider', {}).get('max_completion_tokens', 0),
                          reverse=True)
        elif sort_by == 'context_length':
            models = sorted(models, 
                          key=lambda m: m.get('context_length', 0),
                          reverse=True)
        elif sort_by == 'cost':
            # Sort by cheapest
            models = sorted(models, 
                          key=lambda m: float(m.get('pricing', {}).get('prompt', 1)))
        
        return models
    
    def select_model(self, profile_name: str) -> Optional[str]:
        """
        Select the best model for a profile based on constraints.
        
        Args:
            profile_name: Name of profile (without .profile extension)
        
        Returns:
            Model ID string or None if no suitable model found
        """
        constraints = self.load_constraints(profile_name)
        
        if not constraints:
            print(f"No constraints file for {profile_name}, using profile default")
            return None
        
        # Get available models
        models = self.get_available_models()
        if not models:
            print("Could not fetch models from OpenRouter")
            return constraints.get('fallback', {}).get('model')
        
        # Apply filters
        models = self.filter_by_capabilities(models, constraints)
        print(f"After capability filter: {len(models)} models")
        
        models = self.filter_by_cost(models, constraints)
        print(f"After cost filter: {len(models)} models")
        
        models = self.apply_preferences(models, constraints)
        print(f"After preferences: {len(models)} models")
        
        models = self.rank_by_quality(models, constraints)
        
        # Return best model
        if models:
            selected = models[0]
            print(f"Selected model: {selected['id']}")
            return selected['id']
        
        # No models match - use fallback
        fallback = constraints.get('fallback', {}).get('model', 'gpt-4o-mini')
        print(f"No models match constraints, using fallback: {fallback}")
        return fallback

# Global instance
model_selector = ModelSelector()
```

**Integration with Profile Loading:**
```python
def load_profile_with_auto_model(profile_name, chat_id):
    """
    Load profile and automatically select best model based on constraints.
    """
    # Load the base profile
    success, message, greeting = load_profile(profile_name, chat_id)
    
    if not success:
        return success, message, greeting
    
    # Try to apply model constraints
    profile_base = profile_name.replace('.profile', '')
    selected_model = model_selector.select_model(profile_base)
    
    if selected_model:
        # Override model from profile with auto-selected one
        session_data[chat_id]['model_version'] = f"openrouter:{selected_model}"
        message += f"\n🤖 Auto-selected model: {selected_model}"
    
    return success, message, greeting
```

**Model Comparison Tool:**
```python
def compare_models(constraints_file: str, top_n: int = 5) -> str:
    """Generate comparison report of top N models matching constraints."""
    selector = ModelSelector()
    
    # Parse constraints
    with open(constraints_file, 'r') as f:
        constraints = json.load(f)
    
    models = selector.get_available_models()
    models = selector.filter_by_capabilities(models, constraints)
    models = selector.filter_by_cost(models, constraints)
    models = selector.apply_preferences(models, constraints)
    models = selector.rank_by_quality(models, constraints)
    
    # Format report
    report = "🔍 Model Comparison Report\n\n"
    
    for i, model in enumerate(models[:top_n], 1):
        pricing = model.get('pricing', {})
        report += f"{i}. {model['id']}\n"
        report += f"   Context: {model.get('context_length', 'N/A')} tokens\n"
        report += f"   Cost: ${float(pricing.get('prompt', 0)) * 1_000_000:.2f}/"
        report += f"${float(pricing.get('completion', 0)) * 1_000_000:.2f} per 1M tokens\n"
        report += f"   Modality: {model.get('architecture', {}).get('modality', 'text')}\n\n"
    
    return report
```

### Watch Points & Considerations

1. **Model Availability Changes:**
   - OpenRouter models can be added/removed dynamically
   - Implement caching with reasonable TTL (1 hour)
   - Handle case where selected model becomes unavailable
   - Fallback mechanism is critical

2. **Pricing Fluctuations:**
   - Model pricing can change over time
   - Cache pricing data but refresh periodically
   - Cost constraints should have some buffer/tolerance
   - Log when model selection changes due to pricing

3. **API Rate Limits:**
   - Fetching model list counts against rate limits
   - Cache aggressively to minimize API calls
   - Handle rate limit errors gracefully
   - Implement exponential backoff

4. **Constraint Conflicts:**
   - Some constraint combinations may have no matching models
   - Prioritize constraints (capabilities > cost > preferences)
   - Provide clear error messages explaining why no model matches
   - Always have fallback model defined

5. **Performance Impact:**
   - Model selection should happen at profile activation, not per message
   - Pre-compute and cache selections when possible
   - Don't block message sending on model selection
   - Timeout model selection after 5 seconds

6. **Testing Challenges:**
   - Model list changes frequently
   - Need mock data for unit tests
   - Integration tests should use real API occasionally
   - Validate constraint logic with known model sets

7. **User Transparency:**
   - Show which model was selected and why
   - Allow users to override auto-selection
   - Provide `/modelinfo` command to see selection reasoning
   - Log selection decisions for debugging

8. **Security:**
   - Validate constraint files to prevent injection
   - Limit max file size for constraint files (10KB)
   - Sanitize model IDs before use
   - No code execution from constraint files

9. **Complex Constraint Logic:**
   - Boolean combinations (AND/OR/NOT)
   - Weighted scoring vs hard filters
   - Multi-objective optimization
   - Consider keeping it simple initially

### Commands to Implement

```python
# Add to help text
reply_text += "/automodel - toggle automatic model selection\n"
reply_text += "/modelinfo - show current model selection reasoning\n"
reply_text += "/testconstraints <profile> - test model selection for profile\n"
reply_text += "/comparemodels - compare top models matching current constraints\n"
```

### Testing Strategy

```python
def test_model_selection():
    """Test model selection with various constraints."""
    selector = ModelSelector()
    
    # Test 1: Image capability requirement
    constraints = {
        'capabilities': {'image_input': True},
        'fallback': {'model': 'gpt-4o-mini'}
    }
    # Should select vision-capable model
    
    # Test 2: Cost constraint
    constraints = {
        'cost': {'max_prompt_cost': 1.0},
        'fallback': {'model': 'gpt-4o-mini'}
    }
    # Should exclude expensive models
    
    # Test 3: No matches
    constraints = {
        'capabilities': {'context_length_min': 1000000},
        'cost': {'max_prompt_cost': 0.01},
        'fallback': {'model': 'gpt-4o-mini'}
    }
    # Should return fallback
    
    # Test 4: Provider preference
    constraints = {
        'preferences': {'provider_preference': ['anthropic']},
        'fallback': {'model': 'gpt-4o-mini'}
    }
    # Should prefer Claude models
```

## 4. Text-to-Speech (TTS) Responses

### Overview
Convert AI text responses to natural-sounding speech, enabling audio-based interaction for accessibility, multitasking, or user preference.

### Features

- **TTS Integration (Replicate.com):**
  - Add option to render AI responses as audio files using Replicate's TTS.
  - User can toggle between:
    - Text only
    - Speech only
    - Both speech and text

### Implementation Details

**TTS Provider Setup (Replicate):**

```python
import replicate
import os

# Set up Replicate API
REPLICATE_API_TOKEN = os.environ.get('REPLICATE_API_TOKEN')

class TTSManager:
    """Manage text-to-speech operations."""
    
    def __init__(self):
        self.client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        # Recommended TTS models on Replicate
        self.models = {
            'coqui': 'coqui/xtts-v2',  # Multi-lingual, voice cloning
            'bark': 'suno-ai/bark',     # Expressive, with emotions
            'tortoise': 'afiaka87/tortoise-tts'  # High quality, slower
        }
        self.default_model = 'coqui'
    
    def text_to_speech(self, text: str, 
                      voice: str = 'default',
                      language: str = 'en',
                      model: str = None) -> Optional[str]:
        """
        Convert text to speech using Replicate.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID or preset
            language: Language code (en, es, fr, etc.)
            model: TTS model to use
        
        Returns:
            URL to audio file or None on error
        """
        if not model:
            model = self.default_model
        
        try:
            if model == 'coqui':
                output = self.client.run(
                    self.models['coqui'],
                    input={
                        "text": text,
                        "language": language,
                        "speaker_wav": None,  # Or URL to voice sample
                    }
                )
            elif model == 'bark':
                output = self.client.run(
                    self.models['bark'],
                    input={
                        "prompt": text,
                        "text_temp": 0.7,
                        "waveform_temp": 0.7,
                    }
                )
            
            # output is usually a URL to the audio file
            if isinstance(output, str):
                return output
            elif isinstance(output, list) and len(output) > 0:
                return output[0]
            
            return None
            
        except Exception as e:
            print(f"TTS error: {e}")
            return None
    
    def download_audio(self, audio_url: str, output_path: str) -> bool:
        """Download audio file from URL."""
        try:
            response = requests.get(audio_url, timeout=30)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            print(f"Audio download error: {e}")
        return False

# Global TTS manager
tts_manager = TTSManager()
```

**Session Settings for TTS:**

```python
# Add to session_data initialization
session_data[chat_id]['tts_mode'] = 'text_only'  # or 'speech_only', 'both'
session_data[chat_id]['tts_voice'] = 'default'
session_data[chat_id]['tts_language'] = 'en'
session_data[chat_id]['tts_enabled'] = False

def update_tts_settings(chat_id, mode=None, voice=None, language=None):
    """Update TTS settings for a session."""
    if mode and mode in ['text_only', 'speech_only', 'both']:
        session_data[chat_id]['tts_mode'] = mode
        session_data[chat_id]['tts_enabled'] = (mode != 'text_only')
    
    if voice:
        session_data[chat_id]['tts_voice'] = voice
    
    if language:
        session_data[chat_id]['tts_language'] = language
```

**Integration with Message Sending:**

```python
def send_ai_response(chat_id, response_text):
    """
    Send AI response with optional TTS.
    Handles text, speech, or both based on user settings.
    """
    tts_mode = session_data[chat_id].get('tts_mode', 'text_only')
    
    # Always send text if mode is text_only or both
    if tts_mode in ['text_only', 'both']:
        send_message(chat_id, response_text)
    
    # Generate and send speech if enabled
    if tts_mode in ['speech_only', 'both']:
        # Show "recording audio" status
        send_chat_action(chat_id, 'record_audio')
        
        # Limit text length for TTS (max ~4000 chars)
        tts_text = response_text[:4000] if len(response_text) > 4000 else response_text
        
        # Generate speech
        audio_url = tts_manager.text_to_speech(
            tts_text,
            voice=session_data[chat_id].get('tts_voice', 'default'),
            language=session_data[chat_id].get('tts_language', 'en')
        )
        
        if audio_url:
            # Download audio file
            audio_path = f"/tmp/tts_{chat_id}_{int(time.time())}.wav"
            if tts_manager.download_audio(audio_url, audio_path):
                # Send as voice message
                send_voice(chat_id, audio_path)
                os.remove(audio_path)
            else:
                # Fallback to text if download fails
                if tts_mode == 'speech_only':
                    send_message(chat_id, response_text)
                send_message(chat_id, "⚠️ Audio generation failed, showing text.")
        else:
            # Fallback if TTS fails
            if tts_mode == 'speech_only':
                send_message(chat_id, response_text)
            send_message(chat_id, "⚠️ Text-to-speech unavailable.")

def send_voice(chat_id, audio_path):
    """Send audio file as voice message via Telegram."""
    url = f"https://api.telegram.org/bot{BOT_KEY}/sendVoice"
    
    with open(audio_path, 'rb') as audio_file:
        files = {'voice': audio_file}
        data = {'chat_id': chat_id}
        
        response = requests.post(url, data=data, files=files)
        return response.json()

def send_chat_action(chat_id, action):
    """Send chat action (typing, recording, etc.)."""
    url = f"https://api.telegram.org/bot{BOT_KEY}/sendChatAction"
    data = {'chat_id': chat_id, 'action': action}
    requests.post(url, data=data)
```

**Bot Commands for TTS Control:**

```python
def long_polling():
    # ... existing code ...
    
    if message_text.startswith('/tts'):
        parts = message_text.split()
        
        if len(parts) == 1:
            # Show current settings
            mode = session_data[chat_id].get('tts_mode', 'text_only')
            voice = session_data[chat_id].get('tts_voice', 'default')
            lang = session_data[chat_id].get('tts_language', 'en')
            
            reply = f"🔊 TTS Settings:\n"
            reply += f"Mode: {mode}\n"
            reply += f"Voice: {voice}\n"
            reply += f"Language: {lang}\n\n"
            reply += f"Commands:\n"
            reply += f"/tts text - text only (disable TTS)\n"
            reply += f"/tts speech - speech only\n"
            reply += f"/tts both - text and speech\n"
            reply += f"/tts voice <name> - set voice\n"
            reply += f"/tts lang <code> - set language (en, es, fr, etc.)\n"
            
            send_message(chat_id, reply)
            continue
        
        command = parts[1].lower()
        
        if command in ['text', 'speech', 'both']:
            mode = f"{command}_only" if command != 'both' else 'both'
            if command == 'text':
                mode = 'text_only'
            elif command == 'speech':
                mode = 'speech_only'
            
            update_tts_settings(chat_id, mode=mode)
            send_message(chat_id, f"✅ TTS mode set to: {mode}")
            continue
        
        elif command == 'voice' and len(parts) > 2:
            voice = parts[2]
            update_tts_settings(chat_id, voice=voice)
            send_message(chat_id, f"✅ Voice set to: {voice}")
            continue
        
        elif command == 'lang' and len(parts) > 2:
            language = parts[2]
            update_tts_settings(chat_id, language=language)
            send_message(chat_id, f"✅ Language set to: {language}")
            continue
    
    if message_text == '/ttson':
        update_tts_settings(chat_id, mode='both')
        send_message(chat_id, "🔊 TTS enabled (text + speech)")
        continue
    
    if message_text == '/ttsoff':
        update_tts_settings(chat_id, mode='text_only')
        send_message(chat_id, "🔇 TTS disabled (text only)")
        continue
```

**Chunking Long Responses:**

```python
def split_text_for_tts(text: str, max_length: int = 4000) -> List[str]:
    """
    Split long text into chunks suitable for TTS.
    Tries to split on sentence boundaries.
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences
    sentences = text.replace('? ', '?|').replace('! ', '!|').replace('. ', '.|').split('|')
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def send_ai_response_chunked(chat_id, response_text):
    """Send long responses as multiple TTS chunks."""
    tts_mode = session_data[chat_id].get('tts_mode', 'text_only')
    
    if tts_mode == 'text_only':
        send_message(chat_id, response_text)
        return
    
    chunks = split_text_for_tts(response_text)
    
    for i, chunk in enumerate(chunks):
        if tts_mode in ['text_only', 'both']:
            send_message(chat_id, chunk)
        
        if tts_mode in ['speech_only', 'both']:
            send_chat_action(chat_id, 'record_audio')
            # Generate and send audio for this chunk
            audio_url = tts_manager.text_to_speech(chunk)
            if audio_url:
                audio_path = f"/tmp/tts_{chat_id}_{i}.wav"
                if tts_manager.download_audio(audio_url, audio_path):
                    send_voice(chat_id, audio_path)
                    os.remove(audio_path)
```

### Watch Points & Considerations

1. **API Costs:**
   - TTS can be expensive (~$0.015 per 1000 characters)
   - Monitor usage and implement rate limits
   - Consider monthly budget limits per user
   - Log costs for billing/monitoring

2. **Generation Time:**
   - TTS can take 5-30 seconds depending on text length
   - Show "recording audio" status to user
   - Consider async processing for long texts
   - Implement timeout (60 seconds max)

3. **Audio File Management:**
   - Clean up temporary audio files immediately
   - Set disk space limits for audio generation
   - Use /tmp directory with automatic cleanup
   - Consider streaming instead of file download

4. **Language Support:**
   - Different TTS models support different languages
   - Validate language codes before sending to API
   - Provide clear error messages for unsupported languages
   - Auto-detect language from response text (optional)

5. **Voice Quality:**
   - Different voices have different characteristics
   - Allow users to test voices before selecting
   - Provide voice samples or previews
   - Consider voice cloning for custom personas

6. **Rate Limiting:**
   - Replicate has rate limits
   - Implement retry logic with exponential backoff
   - Queue TTS requests if rate limited
   - Show waiting status to user

7. **Telegram Limitations:**
   - Voice messages limited to 50MB
   - Audio duration affects file size
   - Consider compression for long audio
   - Fallback to text if audio too large

8. **Accessibility:**
   - TTS is critical for visually impaired users
   - Never force TTS-only mode without user choice
   - Provide clear controls for enabling/disabling
   - Test with screen readers

9. **Content Filtering:**
   - Some TTS models refuse certain content
   - Handle rejection gracefully
   - Provide fallback to text
   - Don't expose raw API errors to users

### Required Dependencies

Add to `requirements.txt`:
```
replicate>=0.15.0
pydub>=0.25.0  # For audio processing
```

### Commands to Implement

```python
reply_text += "/tts - configure text-to-speech settings\n"
reply_text += "/ttson - enable TTS (text + speech)\n"
reply_text += "/ttsoff - disable TTS (text only)\n"
reply_text += "/tts speech - speech only mode\n"
reply_text += "/tts voice <name> - change voice\n"
reply_text += "/tts lang <code> - change language\n"
reply_text += "/voices - list available voices\n"
```

### Testing Strategy

```python
def test_tts():
    """Test TTS functionality."""
    manager = TTSManager()
    
    # Test 1: Basic TTS
    url = manager.text_to_speech("Hello, this is a test.")
    assert url is not None
    
    # Test 2: Different languages
    url = manager.text_to_speech("Bonjour le monde", language='fr')
    assert url is not None
    
    # Test 3: Long text chunking
    long_text = "This is a test. " * 500
    chunks = split_text_for_tts(long_text, max_length=1000)
    assert all(len(chunk) <= 1000 for chunk in chunks)
    
    # Test 4: Error handling
    url = manager.text_to_speech("", language='invalid')
    # Should handle gracefully
```

## 5. Voice Input (Speech-to-Text)

### Overview
Enable users to send voice messages that are automatically transcribed to text, allowing hands-free interaction with the chatbot.

### Features

- **Voice Input via Whisper Fast (Replicate):**
  - Allow user to send voice messages, convert them to text using Replicate's Whisper Fast.
  - If model supports direct voice input, forward audio; otherwise, transcribe to text first.

### Implementation Details

**Speech-to-Text Provider Setup:**

```python
import replicate
import os

class STTManager:
    """Manage speech-to-text operations."""
    
    def __init__(self):
        self.client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        self.models = {
            'whisper_fast': 'openai/whisper',
            'whisper_large': 'incredibly-fast-whisper',
        }
        self.default_model = 'whisper_fast'
    
    def speech_to_text(self, audio_file_path: str, 
                      language: str = None,
                      translate: bool = False) -> Optional[Dict]:
        """
        Convert speech to text using Whisper.
        
        Args:
            audio_file_path: Path to audio file
            language: Optional language hint (en, es, fr, etc.)
            translate: If True, translate to English
        
        Returns:
            Dict with 'text', 'language', and 'segments' or None
        """
        try:
            with open(audio_file_path, 'rb') as audio_file:
                output = self.client.run(
                    self.models[self.default_model],
                    input={
                        "audio": audio_file,
                        "language": language,
                        "translate": translate,
                        "temperature": 0,
                        "transcription": "plain text",
                    }
                )
            
            # Parse output
            if isinstance(output, dict):
                return {
                    'text': output.get('transcription', ''),
                    'language': output.get('detected_language', language),
                    'segments': output.get('segments', [])
                }
            elif isinstance(output, str):
                return {
                    'text': output,
                    'language': language,
                    'segments': []
                }
            
            return None
            
        except Exception as e:
            print(f"STT error: {e}")
            return None
    
    def download_telegram_voice(self, file_id: str, output_path: str) -> bool:
        """Download voice message from Telegram."""
        try:
            # Get file path from Telegram
            url = f"https://api.telegram.org/bot{BOT_KEY}/getFile"
            response = requests.get(url, params={'file_id': file_id})
            
            if response.status_code == 200:
                file_path = response.json()['result']['file_path']
                
                # Download file
                file_url = f"https://api.telegram.org/file/bot{BOT_KEY}/{file_path}"
                file_response = requests.get(file_url)
                
                if file_response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(file_response.content)
                    return True
            
            return False
            
        except Exception as e:
            print(f"Download error: {e}")
            return False

# Global STT manager
stt_manager = STTManager()
```

**Handling Voice Messages:**

```python
def handle_voice_message(update):
    """Process incoming voice messages."""
    chat_id = update['message']['chat']['id']
    
    # Check if voice input is enabled for this session
    if not session_data[chat_id].get('voice_input_enabled', True):
        send_message(chat_id, "Voice input is disabled. Use /voiceon to enable.")
        return
    
    voice = update['message'].get('voice')
    if not voice:
        return
    
    file_id = voice['file_id']
    duration = voice.get('duration', 0)
    
    # Limit voice message duration (e.g., 5 minutes)
    if duration > 300:
        send_message(chat_id, 
            "⚠️ Voice message too long. Maximum 5 minutes.")
        return
    
    # Show processing status
    send_message(chat_id, "🎤 Transcribing your voice message...")
    send_chat_action(chat_id, 'typing')
    
    # Download voice message
    audio_path = f"/tmp/voice_{chat_id}_{int(time.time())}.ogg"
    
    if not stt_manager.download_telegram_voice(file_id, audio_path):
        send_message(chat_id, "❌ Failed to download voice message.")
        return
    
    # Convert to text
    result = stt_manager.speech_to_text(audio_path)
    
    # Clean up audio file
    os.remove(audio_path)
    
    if not result or not result['text']:
        send_message(chat_id, 
            "❌ Could not transcribe audio. Please try again or type your message.")
        return
    
    transcribed_text = result['text']
    detected_language = result.get('language', 'unknown')
    
    # Show transcription to user for confirmation
    confirmation_msg = f"📝 Transcribed ({detected_language}):\n\n{transcribed_text}\n\n"
    confirmation_msg += "Processing your message..."
    send_message(chat_id, confirmation_msg)
    
    # Process as normal text message
    process_user_message(chat_id, transcribed_text)

def process_user_message(chat_id, message_text, image_data=None):
    """Unified message processing for text and voice input."""
    # Get AI response
    ai_response, images_received = get_reply(message_text, image_data, chat_id)
    
    # Send response (with TTS if enabled)
    send_ai_response(chat_id, ai_response)
    
    # Handle any images received
    for image_data, mime_type in images_received:
        send_image(chat_id, image_data, mime_type)
```

**Voice Input Settings:**

```python
# Add to session_data initialization
session_data[chat_id]['voice_input_enabled'] = True
session_data[chat_id]['auto_translate_voice'] = False  # Translate to English
session_data[chat_id]['show_transcription'] = True  # Show transcription before processing

def update_voice_settings(chat_id, enabled=None, auto_translate=None, 
                         show_transcription=None):
    """Update voice input settings."""
    if enabled is not None:
        session_data[chat_id]['voice_input_enabled'] = enabled
    
    if auto_translate is not None:
        session_data[chat_id]['auto_translate_voice'] = auto_translate
    
    if show_transcription is not None:
        session_data[chat_id]['show_transcription'] = show_transcription
```

**Bot Commands for Voice Control:**

```python
def long_polling():
    # ... existing code ...
    
    if message_text.startswith('/voice'):
        parts = message_text.split()
        
        if len(parts) == 1:
            # Show settings
            enabled = session_data[chat_id].get('voice_input_enabled', True)
            translate = session_data[chat_id].get('auto_translate_voice', False)
            show_trans = session_data[chat_id].get('show_transcription', True)
            
            reply = f"🎤 Voice Input Settings:\n"
            reply += f"Enabled: {'✅' if enabled else '❌'}\n"
            reply += f"Auto-translate to English: {'✅' if translate else '❌'}\n"
            reply += f"Show transcription: {'✅' if show_trans else '❌'}\n\n"
            reply += f"Commands:\n"
            reply += f"/voiceon - enable voice input\n"
            reply += f"/voiceoff - disable voice input\n"
            reply += f"/voice translate on/off - toggle auto-translation\n"
            reply += f"/voice transcription on/off - toggle showing transcription\n"
            
            send_message(chat_id, reply)
            continue
    
    if message_text == '/voiceon':
        update_voice_settings(chat_id, enabled=True)
        send_message(chat_id, "🎤 Voice input enabled")
        continue
    
    if message_text == '/voiceoff':
        update_voice_settings(chat_id, enabled=False)
        send_message(chat_id, "🔇 Voice input disabled")
        continue
```

**Audio Format Conversion:**

```python
from pydub import AudioSegment

def convert_audio_format(input_path: str, output_path: str, 
                        target_format: str = 'wav') -> bool:
    """
    Convert audio to format suitable for STT.
    Whisper prefers WAV or MP3.
    """
    try:
        audio = AudioSegment.from_file(input_path)
        
        # Convert to mono if stereo
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Resample to 16kHz (optimal for Whisper)
        audio = audio.set_frame_rate(16000)
        
        # Export
        audio.export(output_path, format=target_format)
        return True
        
    except Exception as e:
        print(f"Audio conversion error: {e}")
        return False
```

### Watch Points & Considerations

1. **Transcription Accuracy:**
   - Accuracy depends on audio quality, accent, background noise
   - Provide user feedback when confidence is low
   - Allow users to correct transcription
   - Consider showing confidence scores

2. **Audio Quality:**
   - Telegram voice messages are compressed (OGG/OPUS)
   - Background noise significantly impacts accuracy
   - Short messages (<2 seconds) may not transcribe well
   - Consider audio preprocessing (noise reduction)

3. **Language Detection:**
   - Whisper auto-detects language but can be wrong
   - Allow users to specify language hint
   - Show detected language to user
   - Handle code-switching (multiple languages in one message)

4. **API Costs & Speed:**
   - Whisper is relatively fast (2-10 seconds for 1 minute audio)
   - Cost is ~$0.006 per minute
   - Consider caching transcriptions
   - Implement rate limiting for voice messages

5. **Privacy Concerns:**
   - Voice data is sent to external API (Replicate/OpenAI)
   - Inform users in privacy policy
   - Don't log or store voice data unnecessarily
   - Comply with GDPR and data protection laws

6. **File Size Limits:**
   - Telegram limits voice messages to 20MB
   - Long messages may hit Whisper limits (25MB)
   - Implement file size checks before processing
   - Provide clear error messages

7. **Multimodal Models:**
   - Some models (GPT-4o Audio) support direct audio input
   - Skip transcription if model supports native audio
   - Preserve audio nuances (tone, emotion) when possible
   - Check model capabilities before transcription

8. **User Experience:**
   - Always show transcription before processing
   - Allow users to cancel/edit transcription
   - Provide visual feedback during processing
   - Handle network errors gracefully

9. **Edge Cases:**
   - Empty/silent audio files
   - Non-speech audio (music, noise)
   - Multiple speakers
   - Accented or non-native speech

### Required Dependencies

Add to `requirements.txt`:
```
replicate>=0.15.0
pydub>=0.25.0
ffmpeg-python>=0.2.0
```

System dependencies:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# MacOS
brew install ffmpeg
```

### Commands to Implement

```python
reply_text += "/voice - configure voice input settings\n"
reply_text += "/voiceon - enable voice message transcription\n"
reply_text += "/voiceoff - disable voice message transcription\n"
reply_text += "/voice translate on - auto-translate to English\n"
reply_text += "/voice transcription off - hide transcription text\n"
```

### Testing Strategy

```python
def test_stt():
    """Test speech-to-text functionality."""
    manager = STTManager()
    
    # Test 1: English audio
    result = manager.speech_to_text("test_audio_en.wav")
    assert result is not None
    assert len(result['text']) > 0
    
    # Test 2: Different language
    result = manager.speech_to_text("test_audio_es.wav", language='es')
    assert result['language'] == 'es'
    
    # Test 3: Translation
    result = manager.speech_to_text("test_audio_es.wav", translate=True)
    # Should be in English
    
    # Test 4: Audio format conversion
    success = convert_audio_format("test.ogg", "test.wav")
    assert success
    
    # Test 5: Error handling - invalid file
    result = manager.speech_to_text("nonexistent.wav")
    assert result is None
```

## 6. Example Profiles

### Overview
Provide ready-to-use profile examples demonstrating different use cases and personality types for the chatbot.

### Features

- **Profile Example 1: "Talk Like a Pirate"**
  - Fun/joke profile for demonstration.
  - Simple prompt: "Speak in pirate slang and give playful answers."

- **Profile Example 2: "EEC Educational Chatbot"**
  - For serious educational use.
  - Prompt: "Act as a knowledgeable tutor for IB Math and IB Physics. Help students understand concepts, coach them through problem-solving, and address gaps in understanding."

### Implementation Details

**Example Profile Files:**

**1. Pirate Profile (`pirate.profile`):**
```
gpt-4o-mini
Ahoy there, matey! I be Captain ChatBot, ready to help ye navigate the seven seas of knowledge! What treasure of information be ye seeking today? ⚓🏴‍☠️
You are Captain ChatBot, a jovial pirate who speaks in traditional pirate slang. 

Your personality:
- Use pirate terminology: "ahoy", "matey", "arr", "ye", "aye", "shiver me timbers"
- Refer to yourself as a captain or old sea dog
- Make nautical references when explaining things
- Be enthusiastic and theatrical
- End many sentences with "Arr!" or similar pirate exclamations
- Use maritime metaphors (e.g., "let's set sail on this problem", "anchor down this concept")

Despite the pirate persona, you still:
- Provide accurate, helpful information
- Give clear, understandable explanations
- Take questions seriously (while staying in character)
- Are respectful and friendly

Example phrases:
- "That be a fine question, matey!"
- "Let me chart a course through this problem fer ye"
- "Arr! Here be the treasure ye seek"
- "By Blackbeard's beard, that's a tricky one!"
```

**Pirate Constraints (`pirate.ai`):**
```json
{
  "constraints": {
    "cost": {
      "max_prompt_cost": 5.0,
      "max_completion_cost": 15.0
    },
    "capabilities": {
      "image_input": false,
      "min_context_length": 4000
    },
    "quality": {
      "sort_by": "cost"
    }
  },
  "preferences": {
    "model_preference": ["gpt-4o-mini", "gpt-3.5"],
    "provider_preference": ["openai"]
  },
  "fallback": {
    "model": "gpt-4o-mini"
  }
}
```

**2. Educational Tutor Profile (`tutor_ib.profile`):**
```
openrouter:anthropic/claude-3-opus
Hello! I'm your IB Math and Physics tutor. I'm here to help you understand concepts deeply, not just memorize formulas. What would you like to work on today? 📚
You are an experienced International Baccalaureate (IB) tutor specializing in IB Math (Analysis and Approaches / Applications and Interpretation) and IB Physics.

Your teaching philosophy:
- Socratic method: Ask guiding questions rather than giving direct answers
- Conceptual understanding over memorization
- Connect topics to real-world applications
- Identify and address misconceptions
- Build on student's existing knowledge
- Encourage mathematical reasoning and critical thinking

When helping students:
1. First assess their current understanding
2. Break complex problems into manageable steps
3. Use analogies and visual descriptions
4. Relate concepts to IB exam expectations
5. Provide practice problems similar to IB questions
6. Highlight common mistakes and how to avoid them
7. Reference IB command terms (define, explain, derive, etc.)

For math problems:
- Guide step-by-step without solving directly
- Ask "Why?" questions to check understanding
- Use multiple representations (algebraic, graphic, numeric)
- Connect to relevant IB Math topics

For physics problems:
- Emphasize understanding of underlying principles
- Help with unit analysis and dimensional reasoning
- Encourage drawing diagrams and free body diagrams
- Connect theory to experimental design (IB IA)
- Reference IB Physics topics and paper formats

Maintain a supportive, patient tone. Celebrate progress and encourage effort.
```

**Tutor Constraints (`tutor_ib.ai`):**
```json
{
  "constraints": {
    "capabilities": {
      "image_input": true,
      "min_context_length": 16000
    },
    "cost": {
      "max_prompt_cost": 15.0,
      "max_completion_cost": 50.0
    },
    "quality": {
      "sort_by": "quality"
    }
  },
  "preferences": {
    "model_preference": ["claude-3", "gpt-4"],
    "provider_preference": ["anthropic", "openai"]
  },
  "fallback": {
    "model": "gpt-4o"
  }
}
```

**3. Code Review Assistant (`code_reviewer.profile`):**
```
openrouter:anthropic/claude-3.5-sonnet
Hi! I'm your code review assistant. Share your code and I'll provide constructive feedback on quality, security, performance, and best practices. 💻
You are an expert code reviewer with deep knowledge of multiple programming languages, design patterns, and software engineering best practices.

Your review approach:
- Constructive and educational (not just critical)
- Focus on correctness, readability, maintainability, performance, security
- Suggest specific improvements with examples
- Explain the "why" behind recommendations
- Prioritize issues (critical, important, minor, nitpick)
- Acknowledge good practices when present

Areas to examine:
1. **Correctness**: Logic errors, edge cases, potential bugs
2. **Security**: SQL injection, XSS, authentication issues, sensitive data handling
3. **Performance**: Inefficient algorithms, unnecessary operations, memory usage
4. **Readability**: Clear naming, comments, code organization
5. **Maintainability**: DRY principle, modularity, coupling/cohesion
6. **Best Practices**: Language idioms, design patterns, error handling
7. **Testing**: Test coverage, testability, edge cases

Format your reviews:
```
## Summary
Brief overview of code quality

## Critical Issues (🔴)
[Issues that must be fixed]

## Important Improvements (🟡)
[Significant improvements to consider]

## Minor Suggestions (🔵)
[Nice-to-have improvements]

## What's Done Well (✅)
[Positive feedback]

## Example Refactoring
[Show improved version if major changes suggested]
```

Be specific, provide examples, and always be respectful.
```

**4. Creative Writing Assistant (`writer.profile`):**
```
openrouter:anthropic/claude-3-opus
Hello! I'm your creative writing companion. Whether you need help brainstorming, drafting, or editing, I'm here to help bring your stories to life! ✍️
You are a creative writing assistant helping authors, screenwriters, and storytellers develop compelling narratives.

Your role:
- Brainstorm ideas for characters, plots, settings, themes
- Provide feedback on story structure, pacing, character development
- Suggest improvements for dialogue, descriptions, and prose style
- Help overcome writer's block
- Offer constructive critique on drafts
- Discuss narrative techniques and literary devices

When helping with writing:
1. **Brainstorming**: Ask questions to understand the writer's vision, offer diverse ideas
2. **Character Development**: Explore motivations, backstory, arcs, relationships
3. **Plot Structure**: Discuss setup, conflict, climax, resolution; identify pacing issues
4. **Prose Style**: Comment on voice, tone, word choice, rhythm
5. **Dialogue**: Ensure it sounds natural and reveals character
6. **Show vs Tell**: Encourage sensory details and subtext
7. **Themes**: Help identify and strengthen thematic elements

Provide feedback that:
- Balances praise with constructive criticism
- Offers specific suggestions with examples
- Respects the author's voice and vision
- Asks questions to clarify intent
- Considers genre conventions and audience

For creative exercises:
- Offer writing prompts
- Suggest character or scene-building exercises
- Provide examples from literature when helpful

Be encouraging and supportive while maintaining high standards.
```

**5. Technical Documentation Assistant (`tech_docs.profile`):**
```
gpt-4o
Hello! I'm specialized in creating clear, comprehensive technical documentation. Let's make your documentation user-friendly and effective! 📖
You are a technical documentation specialist helping create clear, accurate, and user-friendly documentation for software, APIs, and technical products.

Your expertise includes:
- API documentation (REST, GraphQL, etc.)
- User guides and tutorials
- README files and getting started guides
- Architecture documentation
- Code comments and inline documentation
- Release notes and changelogs

Documentation principles:
1. **Clarity**: Use simple language, avoid jargon, define terms
2. **Completeness**: Cover all necessary information
3. **Accuracy**: Ensure technical correctness
4. **Organization**: Logical structure, easy navigation
5. **Examples**: Provide code samples and use cases
6. **Accessibility**: Consider diverse audiences and skill levels

When helping with documentation:

For API docs:
- Clear endpoint descriptions
- Request/response examples
- Error codes and handling
- Authentication details
- Rate limits and constraints

For user guides:
- Step-by-step instructions
- Screenshots or diagrams (descriptions)
- Common pitfalls and troubleshooting
- Prerequisites and requirements

For code documentation:
- Clear function/method descriptions
- Parameter explanations
- Return value documentation
- Usage examples
- Edge cases and limitations

Best practices:
- Use active voice
- Include real-world examples
- Maintain consistent formatting
- Version documentation appropriately
- Consider SEO for discoverability

Always verify technical accuracy and suggest improvements for clarity.
```

### Profile Creation Script

```python
#!/usr/bin/env python3
"""
Script to create example profiles.
Run: python create_example_profiles.py
"""

import os

PROFILES_DIR = "./profiles"

profiles = {
    "pirate.profile": """gpt-4o-mini
Ahoy there, matey! I be Captain ChatBot, ready to help ye navigate the seven seas of knowledge! What treasure of information be ye seeking today? ⚓🏴‍☠️
You are Captain ChatBot, a jovial pirate who speaks in traditional pirate slang. 

Your personality:
- Use pirate terminology: "ahoy", "matey", "arr", "ye", "aye", "shiver me timbers"
- Refer to yourself as a captain or old sea dog
- Make nautical references when explaining things
- Be enthusiastic and theatrical
- End many sentences with "Arr!" or similar pirate exclamations
- Use maritime metaphors (e.g., "let's set sail on this problem", "anchor down this concept")

Despite the pirate persona, you still:
- Provide accurate, helpful information
- Give clear, understandable explanations
- Take questions seriously (while staying in character)
- Are respectful and friendly

Example phrases:
- "That be a fine question, matey!"
- "Let me chart a course through this problem fer ye"
- "Arr! Here be the treasure ye seek"
- "By Blackbeard's beard, that's a tricky one!"
""",

    "tutor_ib.profile": """openrouter:anthropic/claude-3-opus
Hello! I'm your IB Math and Physics tutor. I'm here to help you understand concepts deeply, not just memorize formulas. What would you like to work on today? 📚
You are an experienced International Baccalaureate (IB) tutor specializing in IB Math and IB Physics.

Your teaching philosophy:
- Socratic method: Ask guiding questions rather than giving direct answers
- Conceptual understanding over memorization
- Connect topics to real-world applications
- Identify and address misconceptions
- Build on student's existing knowledge
- Encourage mathematical reasoning and critical thinking

When helping students:
1. First assess their current understanding
2. Break complex problems into manageable steps
3. Use analogies and visual descriptions
4. Relate concepts to IB exam expectations
5. Provide practice problems similar to IB questions
6. Highlight common mistakes and how to avoid them
7. Reference IB command terms (define, explain, derive, etc.)

Maintain a supportive, patient tone. Celebrate progress and encourage effort.
""",
}

def create_profiles():
    """Create example profile files."""
    os.makedirs(PROFILES_DIR, exist_ok=True)
    
    for filename, content in profiles.items():
        filepath = os.path.join(PROFILES_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created {filename}")

if __name__ == "__main__":
    create_profiles()
    print(f"\n🎉 Example profiles created in {PROFILES_DIR}/")
    print("Use /activate <profile_name> to load them!")
```

### Watch Points & Considerations

1. **Profile Maintenance:**
   - Profiles may become outdated as models evolve
   - Review and update prompts regularly
   - Test profiles periodically to ensure quality
   - Version control profile files

2. **System Prompt Effectiveness:**
   - Different models respond differently to same prompt
   - Test profiles with multiple models
   - Adjust prompt style for model capabilities
   - Some models ignore system prompts better than others

3. **User Expectations:**
   - Clear profile descriptions prevent confusion
   - Preview profiles before full activation
   - Allow easy switching without losing context
   - Provide examples of profile behavior

4. **Profile Discovery:**
   - Make profiles easy to find and understand
   - Provide categories (educational, entertainment, professional)
   - Include usage examples in descriptions
   - Consider profile ratings/reviews

5. **Educational Use Cases:**
   - Ensure tutor profiles encourage learning, not cheating
   - Balance guidance with independent thinking
   - Don't just give answers to homework
   - Align with educational standards

6. **Character Consistency:**
   - Profiles should maintain personality throughout conversation
   - Test with various types of questions
   - Handle edge cases (e.g., pirate discussing serious topics)
   - Balance character with functionality

7. **Constraint Files:**
   - Keep constraints reasonable and achievable
   - Test that constraints actually match available models
   - Update constraints as model landscape changes
   - Provide fallbacks for all profiles

8. **Content Safety:**
   - Profile prompts should not override safety guidelines
   - Monitor for inappropriate profile usage
   - Implement content filtering regardless of profile
   - Review user-created profiles if allowed

### Testing Example Profiles

```python
def test_profiles():
    """Test example profiles."""
    test_cases = {
        'pirate': [
            ("What is 2+2?", "pirate language", "arr or matey"),
            ("Explain Python", "nautical metaphors", "sea references"),
        ],
        'tutor_ib': [
            ("What is calculus?", "socratic questions", "asking about understanding"),
            ("Solve x^2 = 4", "guiding steps", "not direct answer"),
        ],
    }
    
    for profile, tests in test_cases.items():
        print(f"\nTesting {profile} profile:")
        # Load profile
        success, msg, greeting = load_profile(profile, 'test_chat')
        assert success, f"Failed to load {profile}"
        
        # Test each case
        for question, should_contain, description in tests:
            response = get_reply(question, None, 'test_chat')
            # Check response matches expected style
            print(f"  Q: {question}")
            print(f"  A: {response[:100]}...")
            print(f"  ✓ Contains {description}")
```

---

# Next Steps

## Detailed Implementation Plan

### Phase 1: Foundation (Weeks 1-2)

**Week 1: Profile System**
- [ ] Create profiles directory structure
- [ ] Implement profile file parser
- [ ] Add `/activate` command handler
- [ ] Implement profile listing and switching
- [ ] Add profile validation and error handling
- [ ] Create example profile files (pirate, tutor)
- [ ] Test profile loading with different models
- [ ] Document profile file format

**Week 2: LaTeX Support**
- [ ] Install matplotlib and required dependencies
- [ ] Implement LaTeX detection regex patterns
- [ ] Create basic LaTeX rendering function (matplotlib)
- [ ] Integrate rendering into message flow
- [ ] Handle multiple LaTeX blocks in single message
- [ ] Add error handling and fallback for failed renders
- [ ] Test with various LaTeX expressions
- [ ] Optimize image generation performance

### Phase 2: Advanced Features (Weeks 3-4)

**Week 3: Dynamic Model Selection**
- [ ] Design constraint file format (JSON)
- [ ] Implement constraint file parser
- [ ] Build model fetching and caching system
- [ ] Create capability filtering functions
- [ ] Implement cost filtering
- [ ] Add preference and ranking logic
- [ ] Integrate with profile activation
- [ ] Create example constraint files
- [ ] Test with various constraint combinations

**Week 4: Audio Features (Part 1 - TTS)**
- [ ] Set up Replicate API integration
- [ ] Implement TTSManager class
- [ ] Add TTS settings to session data
- [ ] Create `/tts` command handlers
- [ ] Integrate TTS with response sending
- [ ] Implement text chunking for long messages
- [ ] Add audio file cleanup
- [ ] Test with various text lengths and languages

### Phase 3: Audio & Polish (Weeks 5-6)

**Week 5: Audio Features (Part 2 - STT)**
- [ ] Implement STTManager class
- [ ] Add voice message download from Telegram
- [ ] Create audio format conversion utilities
- [ ] Integrate Whisper transcription
- [ ] Add `/voice` command handlers
- [ ] Handle voice message events in bot
- [ ] Show transcription before processing
- [ ] Test with various audio qualities and languages

**Week 6: Testing & Documentation**
- [ ] Write comprehensive test suite
- [ ] Test all commands and features
- [ ] Test profile switching scenarios
- [ ] Test with multiple concurrent users
- [ ] Write user documentation
- [ ] Create tutorial/walkthrough
- [ ] Document API dependencies
- [ ] Create installation guide
- [ ] Write developer documentation

### Phase 4: Deployment & Monitoring (Week 7)

**Week 7: Production Readiness**
- [ ] Set up logging and monitoring
- [ ] Implement usage tracking
- [ ] Add cost monitoring for API calls
- [ ] Configure rate limiting
- [ ] Set up error alerting
- [ ] Create backup/restore for profiles
- [ ] Performance optimization
- [ ] Security audit
- [ ] Deploy to production
- [ ] Monitor initial usage

## Implementation Guidelines

### Code Organization

```
AITGChatBot/
├── ai-tgbot.py              # Main bot file
├── profiles/                # Profile files
│   ├── pirate.profile
│   ├── pirate.ai
│   ├── tutor_ib.profile
│   └── tutor_ib.ai
├── modules/                 # Feature modules
│   ├── latex_renderer.py    # LaTeX detection & rendering
│   ├── profile_manager.py   # Profile loading & management
│   ├── model_selector.py    # Dynamic model selection
│   ├── tts_manager.py       # Text-to-speech
│   └── stt_manager.py       # Speech-to-text
├── utils/                   # Utility functions
│   ├── file_utils.py
│   └── validation.py
├── tests/                   # Test suite
│   ├── test_profiles.py
│   ├── test_latex.py
│   ├── test_model_selection.py
│   └── test_audio.py
├── docs/                    # Documentation
│   ├── USER_GUIDE.md
│   ├── DEVELOPER.md
│   └── API.md
├── requirements.txt
└── README.md
```

### Development Best Practices

1. **Version Control:**
   - Create feature branches for each roadmap item
   - Commit frequently with clear messages
   - Tag releases with version numbers
   - Document breaking changes

2. **Testing:**
   - Write tests before implementing features (TDD)
   - Maintain >80% code coverage
   - Test with real API calls periodically
   - Use mocks for unit tests

3. **Error Handling:**
   - Never crash the bot - catch all exceptions
   - Log errors with context
   - Provide helpful error messages to users
   - Implement graceful degradation

4. **Performance:**
   - Profile slow operations
   - Cache expensive API calls
   - Use async operations where possible
   - Monitor memory usage

5. **Security:**
   - Validate all user inputs
   - Sanitize file paths
   - Never execute user-provided code
   - Keep API keys secure
   - Rate limit expensive operations

6. **Documentation:**
   - Document all functions with docstrings
   - Keep README up to date
   - Provide usage examples
   - Explain complex algorithms

### Monitoring & Maintenance

**Metrics to Track:**
- API call counts and costs
- Error rates by feature
- Response times
- User engagement (commands used)
- Profile activation frequency
- TTS/STT usage statistics

**Regular Maintenance:**
- Weekly: Review error logs
- Monthly: Update dependencies
- Quarterly: Review and update profiles
- Annually: Security audit

### Success Criteria

Each feature is considered complete when:
- [ ] Implementation matches specification
- [ ] All tests pass
- [ ] Documentation is written
- [ ] Code review approved
- [ ] No critical bugs
- [ ] Performance acceptable
- [ ] User feedback positive

### Risk Mitigation

**Technical Risks:**
- API changes → Use versioned APIs, monitor announcements
- Rate limits → Implement caching, queue requests
- Cost overruns → Set budget alerts, implement usage caps
- Performance issues → Profile code, optimize hot paths

**User Risks:**
- Confusion → Clear documentation, intuitive commands
- Misuse → Content filtering, rate limiting, monitoring
- Data loss → Regular backups, error recovery

**External Dependencies:**
- OpenRouter changes → Regular testing, fallback options
- Replicate changes → Monitor API, version lock
- Telegram API changes → Follow changelog, test updates

