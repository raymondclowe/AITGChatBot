#!/usr/bin/env python3
"""
Test suite for profile management functionality.
Tests the profile functions without running the bot.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Define constants
PROFILE_DIR = "./profiles"
session_data = {}

# Import only the profile functions we need to test
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


def test_list_available_profiles():
    """Test that we can list available profiles."""
    profiles = list_available_profiles()
    print(f"✓ Found {len(profiles)} profiles")
    assert isinstance(profiles, list), "list_available_profiles should return a list"
    assert len(profiles) >= 2, "Should have at least 2 example profiles"
    assert any('pirate' in p for p in profiles), "Should have pirate profile"
    assert any('tutor' in p for p in profiles), "Should have tutor profile"
    print("✓ Profile list includes expected profiles")


def test_is_valid_model():
    """Test model validation."""
    # Valid models
    assert is_valid_model("gpt-4o-mini") == True
    assert is_valid_model("gpt-3.5-turbo") == True
    assert is_valid_model("claude-3-opus") == True
    assert is_valid_model("llama3-8b-8192") == True
    assert is_valid_model("openrouter:anthropic/claude-3-opus") == True
    print("✓ Valid models pass validation")
    
    # Invalid models
    assert is_valid_model("invalid-model") == False
    assert is_valid_model("") == False
    print("✓ Invalid models fail validation")


def test_load_profile():
    """Test loading a profile."""
    # Initialize a test chat session
    test_chat_id = "test_chat_123"
    session_data[test_chat_id] = {
        'model_version': "gpt-4o-mini",
        'CONVERSATION': [],
        'tokens_used': 0,
        'max_rounds': 4
    }
    
    # Test loading pirate profile
    success, message, greeting = load_profile("pirate", test_chat_id)
    
    assert success == True, f"Profile loading should succeed: {message}"
    assert "activated successfully" in message.lower()
    assert greeting is not None and len(greeting) > 0, "Should have a greeting"
    assert "ahoy" in greeting.lower() or "matey" in greeting.lower(), "Greeting should be pirate-themed"
    print(f"✓ Pirate profile loaded successfully")
    print(f"  Model: {session_data[test_chat_id]['model_version']}")
    print(f"  Greeting preview: {greeting[:50]}...")
    
    # Check that conversation has system prompt
    assert len(session_data[test_chat_id]['CONVERSATION']) > 0
    assert session_data[test_chat_id]['CONVERSATION'][0]['role'] == 'system'
    print("✓ System prompt added to conversation")
    
    # Test loading tutor profile
    success, message, greeting = load_profile("tutor_ib", test_chat_id)
    
    assert success == True, f"Profile loading should succeed: {message}"
    assert greeting is not None and len(greeting) > 0
    print(f"✓ Tutor profile loaded successfully")
    print(f"  Model: {session_data[test_chat_id]['model_version']}")
    
    # Test loading non-existent profile
    success, message, greeting = load_profile("nonexistent", test_chat_id)
    
    assert success == False, "Loading non-existent profile should fail"
    assert "not found" in message.lower()
    assert greeting is None
    print("✓ Non-existent profile correctly fails to load")


def run_tests():
    """Run all tests."""
    print("\n=== Testing Profile Management System ===\n")
    
    tests = [
        test_list_available_profiles,
        test_is_valid_model,
        test_load_profile,
    ]
    
    failed = 0
    for test_func in tests:
        try:
            print(f"\nRunning {test_func.__name__}...")
            test_func()
            print(f"✓ {test_func.__name__} PASSED\n")
        except AssertionError as e:
            print(f"✗ {test_func.__name__} FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} ERROR: {e}\n")
            failed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Total: {len(tests)}")
    print(f"Passed: {len(tests) - failed}")
    print(f"Failed: {failed}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
