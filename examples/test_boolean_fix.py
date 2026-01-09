"""
Test case demonstrating the boolean parsing bug fix.
Before fix: bool("False") returns True (any non-empty string is truthy)
After fix: Explicit boolean parsing handles True/False correctly
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import secretagent as sec
import ast
import re

def mock_llm(prompt, service='null', model=None, echo_service=False):
    """Mock LLM that returns specific answers based on test context."""
    # Extract test context from prompt to return appropriate answer
    if 'dangerous' in prompt.lower():
        if 'sunny meadow' in prompt.lower():
            return '<answer>False</answer>'
        elif 'poison gas' in prompt.lower():
            return '<answer>True</answer>'
    return '<answer>False</answer>'

# Patch LLM for testing
sec.llm_util.llm = mock_llm
sec.configure(service='null', model='test')

@sec.subagent()
def is_dangerous(room_desc: str) -> bool:
    """Determine if a room description sounds dangerous."""
    pass

def test_boolean_with_llm():
    """Test boolean parsing with actual @subagent calls."""
    print("Testing boolean parsing with @subagent calls...")
    
    # Test False case
    result1 = is_dangerous("A sunny meadow with butterflies")
    assert result1 is False, f"Expected False, got {result1}"
    print(f"  sunny meadow -> {result1}")
    
    # Test True case
    result2 = is_dangerous("A room filled with poison gas")
    assert result2 is True, f"Expected True, got {result2}"
    print(f"  poison gas -> {result2}")

def test_boolean_parsing_variations():
    """Test all boolean string variations."""
    print("\nTesting boolean parsing variations...")
    
    @sec.subagent()
    def dummy_bool(x: str) -> bool:
        """Dummy function for testing."""
        pass
    
    test_cases = [
        ("<answer>True</answer>", True),
        ("<answer>False</answer>", False),
        ("<answer>true</answer>", True),
        ("<answer>false</answer>", False),
        ("<answer>TRUE</answer>", True),
        ("<answer>FALSE</answer>", False),
        ("<answer>yes</answer>", True),
        ("<answer>no</answer>", False),
        ("<answer>1</answer>", True),
        ("<answer>0</answer>", False),
        ("<answer>y</answer>", True),
        ("<answer>n</answer>", False),
    ]
    
    for llm_output, expected in test_cases:
        result = sec.parse_llm_output(dummy_bool, llm_output)
        assert result == expected, f"Failed: {llm_output} -> {result}, expected {expected}"
        print(f"  '{llm_output}' -> {result}")

def test_other_types():
    """Test that other return types still work correctly."""
    print("\nTesting other return types...")
    
    @sec.subagent()
    def dummy_int(x: str) -> int:
        pass
    
    @sec.subagent()
    def dummy_str(x: str) -> str:
        pass
    
    test_cases = [
        (dummy_int, "<answer>42</answer>", 42),
        (dummy_str, "<answer>hello</answer>", "hello"),
    ]
    
    for func, llm_output, expected in test_cases:
        result = sec.parse_llm_output(func, llm_output)
        assert result == expected, f"Failed: {llm_output} -> {result}, expected {expected}"
        print(f"  {func.__annotations__['return'].__name__}: {llm_output} -> {result}")

if __name__ == '__main__':
    try:
        test_boolean_with_llm()
        test_boolean_parsing_variations()
        test_other_types()
        print("\nAll tests passed! Boolean parsing fix works correctly.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)