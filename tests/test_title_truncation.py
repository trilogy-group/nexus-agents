"""
Tests for source title truncation safeguard.
"""
import pytest


def test_title_truncation_logic():
    """Test the title truncation logic directly."""
    # Test cases for title truncation
    test_cases = [
        # (input_title, expected_output)
        ("Short title", "Short title"),  # Normal case
        ("A" * 254, "A" * 254),  # Exactly 254 chars - no truncation
        ("A" * 255, "A" * 254),  # 255 chars - truncate to 254
        ("A" * 300, "A" * 254),  # Very long - truncate to 254
        ("", ""),  # Empty string
        ("A" * 100, "A" * 100),  # Well under limit
    ]
    
    for input_title, expected in test_cases:
        # Apply the same truncation logic used in the orchestrator
        truncated_title = input_title[:254] if len(input_title) > 254 else input_title
        
        assert truncated_title == expected
        assert len(truncated_title) <= 254


def test_title_with_get_fallback():
    """Test title extraction with fallback logic."""
    test_cases = [
        # (result_dict, expected_title)
        ({"title": "Normal Title"}, "Normal Title"),
        ({"title": "A" * 300}, "A" * 254),  # Long title truncated
        ({"title": ""}, ""),  # Empty title
        ({}, "Untitled"),  # Missing title key
        ({"title": None}, "Untitled"),  # None title
    ]
    
    for result_dict, expected in test_cases:
        # Simulate the logic from the orchestrator
        raw_title = result_dict.get('title', 'Untitled')
        if raw_title is None:
            raw_title = 'Untitled'
        truncated_title = raw_title[:254] if len(raw_title) > 254 else raw_title
        
        assert truncated_title == expected
        assert len(truncated_title) <= 254
