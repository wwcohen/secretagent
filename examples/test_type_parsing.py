"""
Test cases demonstrating type parsing improvements in parse_llm_output.

Fixes:
1. Boolean parsing: bool("False") no longer returns True
2. Tuple parsing: tuple(string) no longer converts character-by-character
3. Complex type handling: list, dict, set now use ast.literal_eval
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import secretagent as sec
import ast
import re

def mock_llm(prompt, service='null', model=None, echo_service=False):
    """Mock LLM that returns specific answers based on test context."""
    if 'dangerous' in prompt.lower():
        if 'sunny meadow' in prompt.lower():
            return '<answer>False</answer>'
        elif 'poison gas' in prompt.lower():
            return '<answer>True</answer>'
    elif 'analyze_sentence' in prompt.lower():
        return '<answer>("Santi Cazorla", "scored a touchdown")</answer>'
    elif 'get_coords' in prompt.lower():
        return '<answer>[10, 20, 30]</answer>'
    return '<answer>False</answer>'

# Patch LLM for testing
sec.llm_util.llm = mock_llm
sec.configure(service='null', model='test')

@sec.subagent()
def is_dangerous(room_desc: str) -> bool:
    """Determine if a room description sounds dangerous."""
    pass

@sec.subagent()
def analyze_sentence(sentence: str) -> tuple:
    """Extract player name and action from sports sentence."""
    pass

@sec.subagent()
def get_coords(location: str) -> list:
    """Get coordinates for a location."""
    pass

def test_boolean_with_llm():
    """Test boolean parsing with actual @subagent calls."""
    print("Testing boolean parsing with @subagent calls...")
    
    result1 = is_dangerous("A sunny meadow with butterflies")
    assert result1 is False, f"Expected False, got {result1}"
    print(f"  sunny meadow -> {result1}")
    
    result2 = is_dangerous("A room filled with poison gas")
    assert result2 is True, f"Expected True, got {result2}"
    print(f"  poison gas -> {result2}")

def test_tuple_with_llm():
    """Test tuple parsing with actual @subagent calls."""
    print("\nTesting tuple parsing with @subagent calls...")
    
    result = analyze_sentence("Santi Cazorla scored a touchdown")
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2, f"Expected 2 elements, got {len(result)}"
    assert result == ("Santi Cazorla", "scored a touchdown"), f"Got {result}"
    print(f"  Tuple parsing: {result}")

def test_list_with_llm():
    """Test list parsing with actual @subagent calls."""
    print("\nTesting list parsing with @subagent calls...")
    
    result = get_coords("home")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert result == [10, 20, 30], f"Got {result}"
    print(f"  List parsing: {result}")

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
        ("<answer>yes</answer>", True),
        ("<answer>no</answer>", False),
        ("<answer>1</answer>", True),
        ("<answer>0</answer>", False),
    ]
    
    for llm_output, expected in test_cases:
        result = sec.parse_llm_output(dummy_bool, llm_output)
        assert result == expected, f"Failed: {llm_output} -> {result}, expected {expected}"
        print(f"  {llm_output} -> {result}")

def test_complex_type_parsing():
    """Test tuple, list, dict parsing directly."""
    print("\nTesting complex type parsing...")
    
    @sec.subagent()
    def dummy_tuple(x: str) -> tuple:
        pass
    
    @sec.subagent()
    def dummy_list(x: str) -> list:
        pass
    
    @sec.subagent()
    def dummy_dict(x: str) -> dict:
        pass
    
    test_cases = [
        (dummy_tuple, '<answer>("hello", "world")</answer>', ("hello", "world")),
        (dummy_list, '<answer>[1, 2, 3]</answer>', [1, 2, 3]),
        (dummy_dict, '<answer>{"key": "value"}</answer>', {"key": "value"}),
    ]
    
    for func, llm_output, expected in test_cases:
        result = sec.parse_llm_output(func, llm_output)
        assert result == expected, f"Failed: {llm_output} -> {result}, expected {expected}"
        print(f"  {type(expected).__name__}: {result}")

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
        print(f"  {func.__annotations__['return'].__name__}: {result}")

if __name__ == '__main__':
    try:
        test_boolean_with_llm()
        test_tuple_with_llm()
        test_list_with_llm()
        test_boolean_parsing_variations()
        test_complex_type_parsing()
        test_other_types()
        print("\n" + "="*60)
        print("All tests passed! Type parsing improvements verified.")
        print("="*60)
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)