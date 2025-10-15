#!/usr/bin/env python3
"""
Integration tests to verify the profile and LaTeX features work together.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_profile_files_exist():
    """Verify that profile files exist and are readable."""
    profile_dir = "./profiles"
    
    assert os.path.exists(profile_dir), "Profiles directory should exist"
    
    expected_profiles = ['pirate.profile', 'tutor_ib.profile']
    
    for profile in expected_profiles:
        profile_path = os.path.join(profile_dir, profile)
        assert os.path.exists(profile_path), f"Profile {profile} should exist"
        
        # Check that file has the correct format
        with open(profile_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) >= 3, f"Profile {profile} should have at least 3 lines"
            
            # Line 1: model name
            model = lines[0].strip()
            assert len(model) > 0, f"Profile {profile} should have a model name"
            
            # Line 2: greeting
            greeting = lines[1].strip()
            assert len(greeting) > 0, f"Profile {profile} should have a greeting"
            
            # Line 3+: system prompt
            system_prompt = ''.join(lines[2:]).strip()
            assert len(system_prompt) > 0, f"Profile {profile} should have a system prompt"
            
        print(f"✓ Profile {profile} is valid")


def test_latex_scenarios():
    """Test various LaTeX scenarios that might come from AI responses."""
    import re
    import tempfile
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    def detect_latex_blocks(text):
        patterns = [
            r'```latex\s*\n(.*?)\n\s*```',
            r'\$\$(.*?)\$\$',
            r'\\\[(.*?)\\\]',
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
        
        latex_blocks.sort(key=lambda x: x['start'])
        
        filtered_blocks = []
        last_end = -1
        for block in latex_blocks:
            if block['start'] >= last_end:
                filtered_blocks.append(block)
                last_end = block['end']
        
        return filtered_blocks
    
    def render_latex_to_image(latex_code, output_path):
        try:
            fig = plt.figure(figsize=(10, 2))
            fig.patch.set_alpha(0.0)
            text = fig.text(0.5, 0.5, f'${latex_code}$', 
                           horizontalalignment='center',
                           verticalalignment='center',
                           fontsize=20)
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
    
    # Scenario 1: Educational math problem with solution
    math_problem = """
    Let's solve the quadratic equation. The general form is:
    
    $$ax^2 + bx + c = 0$$
    
    And the solution is given by the quadratic formula:
    
    ```latex
    x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
    ```
    
    For example, if $$a=1$$, $$b=-5$$, and $$c=6$$, we get $$x=2$$ or $$x=3$$.
    """
    
    blocks = detect_latex_blocks(math_problem)
    assert len(blocks) >= 4, f"Should detect at least 4 LaTeX blocks, found {len(blocks)}"
    print(f"✓ Educational scenario: detected {len(blocks)} LaTeX blocks")
    
    # Try rendering each block
    for i, block in enumerate(blocks):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            output_path = tmp.name
        try:
            success = render_latex_to_image(block['content'], output_path)
            if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"  ✓ Rendered block {i+1}: {block['content'][:30]}...")
            else:
                print(f"  ⚠ Could not render block {i+1}")
        finally:
            try:
                os.remove(output_path)
            except:
                pass
    
    # Scenario 2: Physics problem
    physics_problem = """
    The kinetic energy formula is $$E_k = \\frac{1}{2}mv^2$$ where:
    - m is mass
    - v is velocity
    """
    
    blocks = detect_latex_blocks(physics_problem)
    assert len(blocks) >= 1, "Should detect at least 1 LaTeX block"
    print(f"✓ Physics scenario: detected {len(blocks)} LaTeX blocks")


def test_profile_and_latex_together():
    """Test that profiles can be used with LaTeX responses."""
    import re
    
    # Simulate what happens when tutor_ib profile gives a math answer with LaTeX
    profile_dir = "./profiles"
    tutor_profile = os.path.join(profile_dir, "tutor_ib.profile")
    
    with open(tutor_profile, 'r') as f:
        lines = f.readlines()
    
    model = lines[0].strip()
    greeting = lines[1].strip()
    system_prompt = ''.join(lines[2:]).strip()
    
    # Check that the tutor profile uses an appropriate model
    assert any(x in model.lower() for x in ['gpt', 'claude', 'openrouter']), \
        "Tutor profile should use a capable model"
    
    # Simulate an AI response that a tutor might give
    tutor_response = """
    Great question! Let's work through this step by step.
    
    The derivative of $$x^2$$ with respect to x is:
    
    ```latex
    \\frac{d}{dx}(x^2) = 2x
    ```
    
    This follows from the power rule: $$\\frac{d}{dx}(x^n) = nx^{n-1}$$.
    
    Try applying this to $$x^3$$ - what do you get?
    """
    
    # Check that LaTeX can be detected in tutor responses
    patterns = [
        r'```latex\s*\n(.*?)\n\s*```',
        r'\$\$(.*?)\$\$',
    ]
    
    latex_found = False
    for pattern in patterns:
        if re.search(pattern, tutor_response, re.DOTALL):
            latex_found = True
            break
    
    assert latex_found, "Should find LaTeX in tutor response"
    print("✓ Profile and LaTeX integration works")


def run_tests():
    """Run all integration tests."""
    print("\n=== Integration Tests ===\n")
    
    tests = [
        test_profile_files_exist,
        test_latex_scenarios,
        test_profile_and_latex_together,
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
