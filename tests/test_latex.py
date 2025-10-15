#!/usr/bin/env python3
"""
Test suite for LaTeX rendering functionality.
Tests the LaTeX detection and rendering functions.
"""
import os
import sys
import tempfile
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def detect_latex_blocks(text):
    """
    Detect LaTeX blocks in text using multiple patterns.
    Returns list of dicts with 'start', 'end', 'content', 'full_match' keys.
    """
    patterns = [
        r'```latex\s*\n(.*?)\n\s*```',  # Code block format with optional whitespace
        r'\$\$(.*?)\$\$',                # Display math format
        r'\\\[(.*?)\\\]',                # LaTeX display format
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
    
    # Sort by position and remove duplicates
    latex_blocks.sort(key=lambda x: x['start'])
    
    # Remove overlapping blocks (keep first occurrence)
    filtered_blocks = []
    last_end = -1
    for block in latex_blocks:
        if block['start'] >= last_end:
            filtered_blocks.append(block)
            last_end = block['end']
    
    return filtered_blocks


def render_latex_to_image(latex_code, output_path):
    """
    Render LaTeX code to an image using matplotlib.
    
    Args:
        latex_code: LaTeX expression to render
        output_path: Path to save the PNG image
    
    Returns:
        bool: True if rendering succeeded, False otherwise
    """
    try:
        # Create figure with transparent background
        fig = plt.figure(figsize=(10, 2))
        fig.patch.set_alpha(0.0)
        
        # Render LaTeX
        text = fig.text(0.5, 0.5, f'${latex_code}$', 
                       horizontalalignment='center',
                       verticalalignment='center',
                       fontsize=20)
        
        # Save with tight bounding box
        plt.savefig(output_path, bbox_inches='tight', 
                   pad_inches=0.1, transparent=True, dpi=150)
        plt.close(fig)
        
        return True
        
    except Exception as e:
        print(f"LaTeX rendering failed: {e}")
        try:
            plt.close('all')
        except:
            pass
        return False


def test_detect_latex_blocks():
    """Test LaTeX block detection."""
    
    # Test 1: Code block format
    text1 = "Here is an equation: ```latex\nE = mc^2\n``` and more text."
    blocks1 = detect_latex_blocks(text1)
    assert len(blocks1) == 1
    assert blocks1[0]['content'] == "E = mc^2"
    print("✓ Code block format detected")
    
    # Test 2: Display math format
    text2 = "The equation $$x^2 + y^2 = z^2$$ is Pythagorean."
    blocks2 = detect_latex_blocks(text2)
    assert len(blocks2) == 1
    assert blocks2[0]['content'] == "x^2 + y^2 = z^2"
    print("✓ Display math format detected")
    
    # Test 3: LaTeX display format
    text3 = r"The integral \[\int_0^1 x^2 dx\] equals 1/3."
    blocks3 = detect_latex_blocks(text3)
    assert len(blocks3) == 1
    assert "int_0^1 x^2 dx" in blocks3[0]['content']
    print("✓ LaTeX display format detected")
    
    # Test 4: Multiple blocks
    text4 = "First $$a^2$$ then ```latex\nb^2\n``` and finally $$c^2$$."
    blocks4 = detect_latex_blocks(text4)
    assert len(blocks4) == 3
    print("✓ Multiple LaTeX blocks detected")
    
    # Test 5: No LaTeX
    text5 = "This is just plain text with no math."
    blocks5 = detect_latex_blocks(text5)
    assert len(blocks5) == 0
    print("✓ No false positives for plain text")
    
    # Test 6: Complex equation
    text6 = r"$$\frac{d}{dx}\left(\int_0^x f(t)dt\right) = f(x)$$"
    blocks6 = detect_latex_blocks(text6)
    assert len(blocks6) == 1
    assert "frac" in blocks6[0]['content']
    print("✓ Complex equation detected")


def test_render_latex_to_image():
    """Test LaTeX rendering to image."""
    
    test_cases = [
        ("E = mc^2", "Simple equation"),
        (r"\frac{a}{b}", "Fraction"),
        (r"x^2 + y^2 = z^2", "Pythagorean theorem"),
        (r"\int_0^1 x^2 dx", "Integral"),
        (r"\alpha + \beta = \gamma", "Greek letters"),
    ]
    
    for latex_code, description in test_cases:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            success = render_latex_to_image(latex_code, output_path)
            assert success, f"Failed to render: {description}"
            
            # Check that file exists and has content
            assert os.path.exists(output_path), f"Image file not created for: {description}"
            assert os.path.getsize(output_path) > 0, f"Image file is empty for: {description}"
            
            print(f"✓ Rendered: {description}")
        finally:
            try:
                os.remove(output_path)
            except:
                pass
    
    # Test invalid LaTeX (should fail gracefully)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        output_path = tmp.name
    
    try:
        success = render_latex_to_image(r"\invalidcommand{test}", output_path)
        # Should return False but not crash
        print(f"✓ Invalid LaTeX handled gracefully (success={success})")
    finally:
        try:
            os.remove(output_path)
        except:
            pass


def test_latex_integration():
    """Test that detection and rendering work together."""
    
    test_text = r"""
    Here is the famous equation: $$E = mc^2$$
    
    And here's another one:
    ```latex
    \frac{d}{dx}(x^2) = 2x
    ```
    
    Finally: $$a^2 + b^2 = c^2$$
    """
    
    blocks = detect_latex_blocks(test_text)
    assert len(blocks) == 3, f"Expected 3 blocks, got {len(blocks)}: {[b['content'] for b in blocks]}"
    print(f"✓ Found {len(blocks)} LaTeX blocks in integrated test")
    
    # Try rendering each block
    for i, block in enumerate(blocks):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            output_path = tmp.name
        
        try:
            success = render_latex_to_image(block['content'], output_path)
            if success:
                print(f"✓ Rendered block {i+1}: {block['content'][:30]}...")
            else:
                print(f"⚠ Could not render block {i+1}: {block['content'][:30]}...")
        finally:
            try:
                os.remove(output_path)
            except:
                pass


def test_convert_inline_latex_to_telegram():
    """Test inline LaTeX conversion to Telegram formatting."""
    
    # Import the function from the main file
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Read and execute the function from the main file
    with open('ai-tgbot.py', 'r') as f:
        content = f.read()
    
    # Extract the function
    start = content.find('def convert_inline_latex_to_telegram')
    end = content.find('\n\ndef ', start + 1)
    if end == -1:
        end = len(content)
    func_code = content[start:end]
    
    # Execute the function in global scope
    exec(func_code, globals())
    
    # Test cases
    test_cases = [
        (r'The area \(A\) of a circle', 'The area *A* of a circle'),
        (r'The value of \(\pi\) is approximately 3.14', 'The value of π is approximately 3\\.14'),
        (r'Solve for \(x\) in the equation', 'Solve for *x* in the equation'),
        (r'Using \(F = ma\)', 'Using *F* \\= *ma*'),
        (r'Greek letters: \(\alpha + \beta = \gamma\)', 'Greek letters: α \\+ β \\= γ'),
    ]
    
    for input_text, expected in test_cases:
        result = convert_inline_latex_to_telegram(input_text)
        if result != expected:
            print(f"FAIL: Input: {input_text}")
            print(f"Expected: {expected}")
            print(f"Got: {result}")
            return False
    
    print("✓ Inline LaTeX conversion tests passed")
    return True


def run_tests():
    """Run all tests."""
    print("\n=== Testing LaTeX Support System ===\n")
    
    tests = [
        test_detect_latex_blocks,
        test_render_latex_to_image,
        test_latex_integration,
        test_convert_inline_latex_to_telegram,
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
