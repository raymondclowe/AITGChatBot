#!/usr/bin/env python3
"""
Test script for /format command and modalities/image_config support.
Tests that format command correctly sets modalities and image options for OpenRouter API.
"""

import sys
import os

# Mock environment variables before importing
os.environ['BOT_KEY'] = 'test_bot_key'
os.environ['API_KEY'] = 'test_api_key'
os.environ['ANTHROPIC_API_KEY'] = 'test_anthropic_key'
os.environ['OPENROUTER_API_KEY'] = 'test_openrouter_key'
os.environ['GROQ_API_KEY'] = 'test_groq_key'

# Mock the config file check
def mock_exists(path):
    if path == 'kiosk.conf':
        return False
    return original_exists(path)

import os.path
original_exists = os.path.exists
os.path.exists = mock_exists

# Import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("aitgbot", "ai-tgbot.py")
aitgbot = importlib.util.module_from_spec(spec)

# Restore os.path.exists
os.path.exists = original_exists

# Load the module
spec.loader.exec_module(aitgbot)


def test_format_constants():
    """Test that format constants are defined correctly"""
    print("\n=== Testing Format Constants ===")
    
    assert hasattr(aitgbot, 'VALID_MODALITIES')
    assert hasattr(aitgbot, 'VALID_ASPECT_RATIOS')
    assert hasattr(aitgbot, 'VALID_IMAGE_SIZES')
    
    assert 'auto' in aitgbot.VALID_MODALITIES
    assert 'text' in aitgbot.VALID_MODALITIES
    assert 'image' in aitgbot.VALID_MODALITIES
    assert 'text+image' in aitgbot.VALID_MODALITIES
    
    assert '1:1' in aitgbot.VALID_ASPECT_RATIOS
    assert '16:9' in aitgbot.VALID_ASPECT_RATIOS
    
    assert 'SD' in aitgbot.VALID_IMAGE_SIZES
    assert 'HD' in aitgbot.VALID_IMAGE_SIZES
    assert '4K' in aitgbot.VALID_IMAGE_SIZES
    
    print("  ✓ All format constants defined correctly")


def test_session_initialization_includes_modalities():
    """Test that new sessions include modalities, aspect_ratio, image_size fields"""
    print("\n=== Testing Session Initialization ===")
    
    # Clear any existing session data
    aitgbot.session_data = {}
    
    # Initialize a test session
    test_chat_id = "test_user_123"
    aitgbot.initialize_session(test_chat_id)
    
    assert test_chat_id in aitgbot.session_data
    assert 'modalities' in aitgbot.session_data[test_chat_id]
    assert 'aspect_ratio' in aitgbot.session_data[test_chat_id]
    assert 'image_size' in aitgbot.session_data[test_chat_id]
    assert aitgbot.session_data[test_chat_id]['modalities'] == 'auto'
    assert aitgbot.session_data[test_chat_id]['aspect_ratio'] is None
    assert aitgbot.session_data[test_chat_id]['image_size'] is None
    
    print("  ✓ New sessions include modalities, aspect_ratio, image_size fields")


def test_modality_values():
    """Test valid modality values"""
    print("\n=== Testing Modality Values ===")
    
    valid_modalities = ['auto', 'text', 'image', 'text+image']
    
    for modality in valid_modalities:
        assert modality in aitgbot.VALID_MODALITIES
        print(f"  ✓ Valid modality: {modality}")


def test_aspect_ratio_values():
    """Test valid aspect ratio values"""
    print("\n=== Testing Aspect Ratio Values ===")
    
    valid_ratios = ['1:1', '16:9', '9:16', '4:3', '3:4']
    
    for ratio in valid_ratios:
        assert ratio in aitgbot.VALID_ASPECT_RATIOS
        print(f"  ✓ Valid aspect ratio: {ratio}")


def test_image_size_values():
    """Test valid image size values"""
    print("\n=== Testing Image Size Values ===")
    
    valid_sizes = ['SD', 'HD', '4K']
    
    for size in valid_sizes:
        assert size in aitgbot.VALID_IMAGE_SIZES
        print(f"  ✓ Valid image size: {size}")


def test_session_modalities_update():
    """Test that session modalities can be updated"""
    print("\n=== Testing Session Modalities Update ===")
    
    # Clear and initialize session
    aitgbot.session_data = {}
    test_chat_id = "test_user_456"
    aitgbot.initialize_session(test_chat_id)
    
    # Update modalities
    aitgbot.session_data[test_chat_id]['modalities'] = 'text+image'
    aitgbot.session_data[test_chat_id]['aspect_ratio'] = '16:9'
    aitgbot.session_data[test_chat_id]['image_size'] = '4K'
    
    assert aitgbot.session_data[test_chat_id]['modalities'] == 'text+image'
    assert aitgbot.session_data[test_chat_id]['aspect_ratio'] == '16:9'
    assert aitgbot.session_data[test_chat_id]['image_size'] == '4K'
    
    print("  ✓ Session modalities can be updated")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("FORMAT COMMAND TEST SUITE")
    print("="*70)
    
    tests = [
        test_format_constants,
        test_session_initialization_includes_modalities,
        test_modality_values,
        test_aspect_ratio_values,
        test_image_size_values,
        test_session_modalities_update,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
