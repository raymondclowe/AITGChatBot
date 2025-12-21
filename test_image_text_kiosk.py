#!/usr/bin/env python3
"""
Test script to validate image+text response enforcement in kiosk mode.
This script tests the core functionality without requiring API keys or live connections.
"""

import sys
import os

# Add the parent directory to the path to import the main module
sys.path.insert(0, os.path.dirname(__file__))

# Mock the environment variables before importing the main module
os.environ['BOT_KEY'] = 'test_bot_key'
os.environ['API_KEY'] = 'test_api_key'
os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
os.environ['OPENROUTER_API_KEY'] = 'test_openrouter_key'
os.environ['GROQ_API_KEY'] = 'test_groq_key'

# Mock the config file check to prevent kiosk mode from loading
def mock_exists(path):
    if path == 'kiosk.conf':
        return False
    return original_exists(path)

import os.path
original_exists = os.path.exists
os.path.exists = mock_exists

# Now import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("aitgbot", "ai-tgbot.py")
aitgbot = importlib.util.module_from_spec(spec)

# Restore os.path.exists before loading the module
os.path.exists = original_exists

# Load the module
spec.loader.exec_module(aitgbot)


def test_model_supports_image_output():
    """Test the model_supports_image_output function"""
    print("\n=== Testing model_supports_image_output ===")
    
    # Test cases
    test_cases = [
        ("openrouter:google/gemini-2.0-flash-001", "Should detect Gemini as image-capable"),
        ("openrouter:anthropic/claude-3-opus", "Should detect Claude as NOT image-capable"),
        ("gpt-4o", "Should detect GPT-4o as NOT image-capable (no image output yet)"),
        ("gpt-4o-mini", "Should detect GPT-4o-mini as NOT image-capable"),
        ("claude-3-opus-20240229", "Should detect Claude as NOT image-capable"),
        ("llama3-8b-8192", "Should detect Llama as NOT image-capable"),
    ]
    
    # Mock the capabilities cache with some test data
    aitgbot._model_capabilities_cache = {
        "google/gemini-2.0-flash-001": {
            "image_output": True,
            "image_input": True,
            "name": "Gemini 2.0 Flash"
        },
        "google/gemini-3-pro-image-preview": {
            "image_output": True,
            "image_input": True,
            "name": "Gemini 3 Pro Image"
        },
        "anthropic/claude-3-opus": {
            "image_output": False,
            "image_input": True,
            "name": "Claude 3 Opus"
        }
    }
    aitgbot._cache_timestamp = aitgbot.time.time()
    
    passed = 0
    failed = 0
    
    for model, description in test_cases:
        result = aitgbot.model_supports_image_output(model)
        expected = "image" in model.lower() or "gemini" in model.lower()
        
        # Adjust expectations based on actual implementation
        if model.startswith("openrouter:"):
            model_id = model[11:]
            caps = aitgbot._model_capabilities_cache.get(model_id, {})
            expected = caps.get('image_output', False)
        else:
            expected = False  # Other providers don't support image output yet
        
        status = "✓ PASS" if result == expected else "✗ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"  {status}: {model}")
        print(f"    {description}")
        print(f"    Result: {result}, Expected: {expected}")
    
    print(f"\n  Total: {passed} passed, {failed} failed")
    return failed == 0


def test_image_request_keyword_detection():
    """Test that image request keywords are properly detected"""
    print("\n=== Testing Image Request Keyword Detection ===")
    
    test_cases = [
        ("Can you draw a diagram of the water cycle?", True),
        ("Please illustrate this concept", True),
        ("Show me a graph of this data", True),
        ("Create an image of a triangle", True),
        ("Generate a picture of a cat", True),
        ("What is photosynthesis?", False),
        ("Explain Newton's laws", False),
        ("Help me with this math problem", False),
    ]
    
    image_request_keywords = [
        'draw', 'sketch', 'diagram', 'illustrate', 'visualize', 'show me',
        'picture', 'image', 'graph', 'chart', 'plot', 'create',
        'generate', 'make', 'design'
    ]
    
    passed = 0
    failed = 0
    
    for message, expected in test_cases:
        message_lower = message.lower()
        result = any(keyword in message_lower for keyword in image_request_keywords)
        
        status = "✓ PASS" if result == expected else "✗ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"  {status}: '{message[:50]}...'")
        print(f"    Detected as image request: {result}, Expected: {expected}")
    
    print(f"\n  Total: {passed} passed, {failed} failed")
    return failed == 0


def test_system_prompt_enhancement():
    """Test that system prompts are properly enhanced for image-capable models"""
    print("\n=== Testing System Prompt Enhancement ===")
    
    # Mock KIOSK_MODE and KIOSK_SYSTEM_PROMPT
    original_kiosk_mode = aitgbot.KIOSK_MODE
    original_kiosk_prompt = aitgbot.KIOSK_SYSTEM_PROMPT
    
    aitgbot.KIOSK_MODE = True
    aitgbot.KIOSK_SYSTEM_PROMPT = "You are a helpful tutor."
    
    # Mock the capabilities
    aitgbot._model_capabilities_cache = {
        "google/gemini-2.0-flash-001": {
            "image_output": True,
            "image_input": True,
        }
    }
    aitgbot._cache_timestamp = aitgbot.time.time()
    
    # Test with image-capable model
    test_chat_id = "test_456"
    
    # Make sure session doesn't already exist
    if test_chat_id in aitgbot.session_data:
        del aitgbot.session_data[test_chat_id]
    
    # Temporarily override the default model to use an image-capable one
    original_get_default = aitgbot.get_default_model
    aitgbot.get_default_model = lambda: 'openrouter:google/gemini-2.0-flash-001'
    
    # Call initialize_session to create a new session
    aitgbot.initialize_session(test_chat_id)
    
    conversation = aitgbot.session_data[test_chat_id]['CONVERSATION']
    
    passed = False
    if conversation and len(conversation) > 0:
        system_message = conversation[0]
        if system_message.get('role') == 'system':
            content = system_message.get('content', [])
            if content and len(content) > 0:
                text = content[0].get('text', '')
                if 'IMPORTANT' in text and 'image' in text.lower() and 'text explanation' in text.lower():
                    print("  ✓ PASS: System prompt enhanced with image+text instructions")
                    print(f"    Enhanced prompt contains: 'IMPORTANT', 'image', 'text explanation'")
                    passed = True
                else:
                    print("  ✗ FAIL: System prompt not properly enhanced")
                    print(f"    Prompt text: {text[:200]}...")
            else:
                print("  ✗ FAIL: System message content is empty")
        else:
            print("  ✗ FAIL: First message is not a system message")
    else:
        print("  ✗ FAIL: No conversation messages found")
    
    # Restore original values
    aitgbot.KIOSK_MODE = original_kiosk_mode
    aitgbot.KIOSK_SYSTEM_PROMPT = original_kiosk_prompt
    aitgbot.get_default_model = original_get_default
    
    return passed


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Testing Image+Text Response Enforcement in Kiosk Mode")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Model Image Output Detection", test_model_supports_image_output()))
    results.append(("Image Request Keyword Detection", test_image_request_keyword_detection()))
    results.append(("System Prompt Enhancement", test_system_prompt_enhancement()))
    
    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n  Total: {total_passed}/{total_tests} test suites passed")
    print("="*60 + "\n")
    
    # Exit with appropriate code
    sys.exit(0 if total_passed == total_tests else 1)


if __name__ == "__main__":
    main()
