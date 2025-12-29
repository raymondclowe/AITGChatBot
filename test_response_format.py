#!/usr/bin/env python3
"""
Test script for /format command and response format filtering.
Tests the format command in both regular and kiosk modes, and validates
that responses are correctly filtered based on format preferences.
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


def test_response_format_constants():
    """Test that format constants are defined correctly"""
    print("\n=== Testing Response Format Constants ===")
    
    assert hasattr(aitgbot, 'RESPONSE_FORMAT_AUTO')
    assert hasattr(aitgbot, 'RESPONSE_FORMAT_TEXT')
    assert hasattr(aitgbot, 'RESPONSE_FORMAT_IMAGE')
    assert hasattr(aitgbot, 'RESPONSE_FORMAT_BOTH')
    assert hasattr(aitgbot, 'VALID_RESPONSE_FORMATS')
    
    assert aitgbot.RESPONSE_FORMAT_AUTO == 'auto'
    assert aitgbot.RESPONSE_FORMAT_TEXT == 'text'
    assert aitgbot.RESPONSE_FORMAT_IMAGE == 'image'
    assert aitgbot.RESPONSE_FORMAT_BOTH == 'both'
    
    assert len(aitgbot.VALID_RESPONSE_FORMATS) == 4
    assert 'auto' in aitgbot.VALID_RESPONSE_FORMATS
    assert 'text' in aitgbot.VALID_RESPONSE_FORMATS
    assert 'image' in aitgbot.VALID_RESPONSE_FORMATS
    assert 'both' in aitgbot.VALID_RESPONSE_FORMATS
    
    print("  ✓ All format constants defined correctly")


def test_session_initialization_includes_format():
    """Test that new sessions include response_format field"""
    print("\n=== Testing Session Initialization ===")
    
    # Clear any existing session data
    aitgbot.session_data = {}
    
    # Initialize a test session
    test_chat_id = "test_user_123"
    aitgbot.initialize_session(test_chat_id)
    
    assert test_chat_id in aitgbot.session_data
    assert 'response_format' in aitgbot.session_data[test_chat_id]
    assert aitgbot.session_data[test_chat_id]['response_format'] == 'auto'
    
    print("  ✓ New sessions include response_format field (default: auto)")


def test_apply_response_format_filter_auto():
    """Test that auto format returns everything unchanged"""
    print("\n=== Testing Format Filter: auto ===")
    
    response_text = "This is a test response"
    images = [(b"fake_image_data", "image/png")]
    
    filtered_text, filtered_images = aitgbot.apply_response_format_filter(
        response_text, images, 'auto'
    )
    
    assert filtered_text == response_text
    assert filtered_images == images
    
    print("  ✓ Auto format preserves both text and images")


def test_apply_response_format_filter_text():
    """Test that text format removes images"""
    print("\n=== Testing Format Filter: text ===")
    
    response_text = "This is a test response"
    images = [(b"fake_image_data", "image/png")]
    
    filtered_text, filtered_images = aitgbot.apply_response_format_filter(
        response_text, images, 'text'
    )
    
    assert filtered_text == response_text
    assert len(filtered_images) == 0
    
    print("  ✓ Text format removes images")


def test_apply_response_format_filter_image():
    """Test that image format removes text"""
    print("\n=== Testing Format Filter: image ===")
    
    response_text = "This is a test response"
    images = [(b"fake_image_data", "image/png")]
    
    filtered_text, filtered_images = aitgbot.apply_response_format_filter(
        response_text, images, 'image'
    )
    
    assert filtered_text == ""
    assert filtered_images == images
    
    print("  ✓ Image format removes text")


def test_apply_response_format_filter_image_no_images():
    """Test that image format with no images returns text with note"""
    print("\n=== Testing Format Filter: image (no images) ===")
    
    response_text = "This is a test response"
    images = []
    
    filtered_text, filtered_images = aitgbot.apply_response_format_filter(
        response_text, images, 'image'
    )
    
    assert "image" in filtered_text.lower()
    assert "no image" in filtered_text.lower()
    assert len(filtered_images) == 0
    
    print("  ✓ Image format with no images shows informative message")


def test_apply_response_format_filter_both():
    """Test that both format handles various scenarios"""
    print("\n=== Testing Format Filter: both ===")
    
    # Case 1: Both text and images present
    response_text = "This is a test response"
    images = [(b"fake_image_data", "image/png")]
    
    filtered_text, filtered_images = aitgbot.apply_response_format_filter(
        response_text, images, 'both'
    )
    
    assert filtered_text == response_text
    assert filtered_images == images
    print("  ✓ Both format preserves text and images when both present")
    
    # Case 2: Only images, no text
    response_text = ""
    images = [(b"fake_image_data", "image/png")]
    
    filtered_text, filtered_images = aitgbot.apply_response_format_filter(
        response_text, images, 'both'
    )
    
    assert "Image generated" in filtered_text
    assert filtered_images == images
    print("  ✓ Both format adds note when only images present")
    
    # Case 3: Only text, no images
    response_text = "This is a test response"
    images = []
    
    filtered_text, filtered_images = aitgbot.apply_response_format_filter(
        response_text, images, 'both'
    )
    
    assert "no image" in filtered_text.lower()
    assert len(filtered_images) == 0
    print("  ✓ Both format adds note when only text present")


def test_format_validation():
    """Test that invalid formats are handled"""
    print("\n=== Testing Format Validation ===")
    
    # Test with invalid format (should default to auto behavior)
    response_text = "This is a test response"
    images = [(b"fake_image_data", "image/png")]
    
    filtered_text, filtered_images = aitgbot.apply_response_format_filter(
        response_text, images, 'invalid_format'
    )
    
    # Should behave like auto (return everything)
    assert filtered_text == response_text
    assert filtered_images == images
    
    print("  ✓ Invalid formats default to auto behavior")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("RESPONSE FORMAT FEATURE TEST SUITE")
    print("="*70)
    
    tests = [
        test_response_format_constants,
        test_session_initialization_includes_format,
        test_apply_response_format_filter_auto,
        test_apply_response_format_filter_text,
        test_apply_response_format_filter_image,
        test_apply_response_format_filter_image_no_images,
        test_apply_response_format_filter_both,
        test_format_validation,
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
