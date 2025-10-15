
# AITGChatBot Roadmap

## 1. LaTeX Support for Math Formulas

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

## 2. Profile Activation via Command

- **/activate Command:**
  - Implement a `/activate <filename>` command to load a profile from a text file.
  - The file format:
    1. **First line:** OpenRouter model name (e.g., gpt-3.5-turbo)
    2. **Second line:** Initial greeting
    3. **Third line onward:** System prompt (can be multiple lines)

- **Profile Management:**
  - Save loaded profiles as `<profile name>.profile`.
  - Switching profiles loads corresponding model and prompt.

## 3. Dynamic Model Selection Based on Constraints

- **Profile-based Model Rules:**
  - For each profile, allow an associated `.ai` file that specifies constraints for model selection, e.g.:
    - Must support image input
    - Top by popularity
    - Cost per token < $0.10
  - Use these constraints to automatically choose the best model from OpenRouter's available list for that profile.

## 4. Text-to-Speech (TTS) Responses

- **TTS Integration (Replicate.com):**
  - Add option to render AI responses as audio files using Replicate's TTS.
  - User can toggle between:
    - Text only
    - Speech only
    - Both speech and text

## 5. Voice Input (Speech-to-Text)

- **Voice Input via Whisper Fast (Replicate):**
  - Allow user to send voice messages, convert them to text using Replicate's Whisper Fast.
  - If model supports direct voice input, forward audio; otherwise, transcribe to text first.

## 6. Example Profiles

- **Profile Example 1: "Talk Like a Pirate"**
  - Fun/joke profile for demonstration.
  - Simple prompt: "Speak in pirate slang and give playful answers."

- **Profile Example 2: "EEC Educational Chatbot"**
  - For serious educational use.
  - Prompt: "Act as a knowledgeable tutor for IB Math and IB Physics. Help students understand concepts, coach them through problem-solving, and address gaps in understanding."

---

# Next Steps

1. **Set up LaTeX detection and rendering pipeline.**
2. **Implement profile loading and switching via `/activate`.**
3. **Design profile and AI constraint file formats.**
4. **Integrate Replicate TTS and Whisper for audio features.**
5. **Create and test the two example profiles.**
6. **Document commands and usage for end users.**

