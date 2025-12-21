# AITGChatBot Usage Guide

## Getting Started

### Basic Commands
Start by sending `/help` to the bot to see all available commands.

## Using Profiles

### Activating a Profile
To switch to a different AI personality:
```
/activate pirate
```

The bot will respond with confirmation and a greeting in character.

### Listing Available Profiles
```
/listprofiles
```

Shows all profiles in the `profiles/` directory.

### Checking Current Profile
```
/currentprofile
```

Shows which profile is currently active and which model it's using.

### Returning to Default
```
/deactivate
```

Returns to the default configuration (gpt-4o-mini with no special personality).

## Using LaTeX

LaTeX support is automatic! When the AI responds with mathematical equations, they will be automatically rendered as images.

### Example Conversation

**You:** "Can you explain the quadratic formula?"

**Bot (with tutor_ib profile):**
```
The quadratic formula is used to solve equations of the form:

$$ax^2 + bx + c = 0$$

The solution is:

```latex
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
```

Where a, b, and c are coefficients from your equation.
```

The bot will send the text portions normally, and render each LaTeX equation as a separate image.

### Supported LaTeX Formats

1. **Display Math** (most common):
   ```
   $$E = mc^2$$
   ```

2. **Code Blocks** (for complex multi-line equations):
   ````
   ```latex
   \begin{align}
   x + y &= 10 \\
   2x - y &= 5
   \end{align}
   ```
   ````

3. **LaTeX Display**:
   ```
   \[\int_0^1 x^2 dx = \frac{1}{3}\]
   ```

## Creating Custom Profiles

### Profile File Format

Create a `.profile` file in the `profiles/` directory with this structure:

```
Line 1: Model name (e.g., gpt-4o-mini, openrouter:anthropic/claude-3-opus)
Line 2: Initial greeting message
Line 3+: System prompt (can span multiple lines)
```

### Example: Math Tutor Profile

File: `profiles/math_tutor.profile`
```
gpt-4o
Hello! I'm your mathematics tutor. Let's work through problems together! 📊
You are a patient mathematics tutor who uses the Socratic method. When students ask questions:
1. Ask guiding questions to help them think
2. Break down complex problems into steps
3. Use LaTeX for all mathematical expressions
4. Provide visual explanations when possible
5. Encourage students to show their work

Always format equations using LaTeX notation with $$...$$ or ```latex blocks so they render beautifully.
```

Then activate it with: `/activate math_tutor`

### Profile Best Practices

1. **Choose the right model:**
   - `gpt-4o-mini` - Fast, cost-effective, good for simple tasks
   - `gpt-4o` - Balanced performance and capability
   - `openrouter:anthropic/claude-3-opus` - Best for complex reasoning
   - `claude-3-haiku` - Fast and efficient for structured tasks

2. **Write clear system prompts:**
   - Describe the personality and behavior
   - Set specific guidelines for responses
   - Include examples of desired behavior
   - For educational profiles, mention LaTeX usage

3. **Test your profiles:**
   - Try edge cases
   - Verify the greeting is appropriate
   - Check that LaTeX renders correctly if used

## Educational Use Cases

### IB Math/Physics Tutoring

```
/activate tutor_ib
```

Ask questions like:
- "Can you help me understand derivatives?"
- "Explain projectile motion with equations"
- "How do I solve this quadratic equation: 2x² - 5x + 2 = 0?"

The tutor will:
- Guide you with questions
- Show step-by-step solutions
- Use LaTeX for all math
- Connect concepts to IB curriculum

### Practice Problems

After activating the tutor profile, you can ask:
- "Give me a practice problem on integration"
- "Can you create a physics problem about forces?"
- "Show me how to derive the quadratic formula"

## Tips and Tricks

### Getting Better LaTeX Results

1. **Be explicit in your prompts:**
   ```
   "Explain the Pythagorean theorem using LaTeX notation"
   ```

2. **Request step-by-step with equations:**
   ```
   "Show me how to factor x² + 5x + 6 step by step with each step as an equation"
   ```

3. **Ask for multiple approaches:**
   ```
   "Show me three different ways to solve this integral, each with proper LaTeX formatting"
   ```

### Switching Contexts

You can switch profiles at any time. Your conversation history is cleared when you activate a new profile, so:

1. Finish your current topic
2. Switch profiles with `/activate <name>`
3. Start a new conversation in the new context

### Combining Features

Use `/status` to check:
- Current profile
- Current model
- Conversation length
- Bot version

Use `/clear` to:
- Reset conversation while keeping the same profile
- Start fresh without switching profiles

## Troubleshooting

### LaTeX Not Rendering

If LaTeX doesn't render properly:
- Check that you used the correct delimiters (`$$...$$` or ```latex blocks)
- Verify the LaTeX syntax is valid
- The bot will fall back to showing the raw LaTeX if rendering fails

### Profile Not Loading

If `/activate` fails:
- Check the profile file exists in `profiles/` directory
- Verify the file has the `.profile` extension
- Ensure the file has at least 3 lines
- Check that the model name on line 1 is valid

### Getting Help

- Use `/help` to see all commands
- Use `/status` to check current configuration
- Check the README.md for installation issues
- Review test files in `tests/` for examples

## Advanced Usage

### Model Selection

You can override the profile's model after activation:
```
/activate tutor_ib
/gpt4omini
```

This keeps the personality but uses a different model.

### Conversation Management

- `/maxrounds 8` - Increase context length for longer conversations
- `/clear` - Clear context but keep profile active
- `/deactivate` - Return to default state

### Image Support

Send images with your questions to vision-capable models:
1. Activate a profile using a vision model (gpt-4o, claude-3)
2. Send an image with your question
3. The AI will analyze the image and respond

## Example Workflow: Homework Help

1. **Activate tutor profile:**
   ```
   /activate tutor_ib
   ```

2. **Ask your question:**
   ```
   I'm stuck on this calculus problem: Find the derivative of x³ + 2x² - 5x + 3
   ```

3. **Work through the solution with the tutor:**
   - Follow the guiding questions
   - View rendered LaTeX equations
   - Understand each step

4. **Practice more:**
   ```
   Can you give me a similar problem to try?
   ```

5. **When done:**
   ```
   /deactivate
   ```

## Conclusion

The combination of profiles and LaTeX support makes AITGChatBot particularly powerful for educational use. Experiment with different profiles and see which works best for your needs!
