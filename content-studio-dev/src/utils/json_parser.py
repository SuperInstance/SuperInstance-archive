# src/utils/json_parser.py
"""
Robust JSON parsing utilities for LLM responses
"""

import json
import re
from typing import Any, Optional


def extract_json_from_text(text: str) -> Optional[Any]:
    """
    Extract JSON from text that may contain markdown code blocks or extra text

    Handles:
    - ```json ... ```
    - ``` ... ```
    - Plain JSON with surrounding text
    - Multiple JSON objects (returns first)

    Args:
        text: Text potentially containing JSON

    Returns:
        Parsed JSON object or None if parsing fails
    """
    # Try direct parsing first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    # Pattern 1: ```json ... ```
    pattern1 = r'```json\s*(.*?)\s*```'
    matches = re.findall(pattern1, text, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[0].strip())
        except json.JSONDecodeError:
            pass

    # Pattern 2: ``` ... ``` (no language specified)
    pattern2 = r'```\s*(.*?)\s*```'
    matches = re.findall(pattern2, text, re.DOTALL)
    if matches:
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

    # Pattern 3: Find JSON-like structures (starts with { or [)
    # Look for balanced braces/brackets
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start_idx = text.find(start_char)
        if start_idx != -1:
            # Find matching closing character
            depth = 0
            for i in range(start_idx, len(text)):
                if text[i] == start_char:
                    depth += 1
                elif text[i] == end_char:
                    depth -= 1
                    if depth == 0:
                        # Found complete JSON structure
                        try:
                            return json.loads(text[start_idx:i+1])
                        except json.JSONDecodeError:
                            pass
                        break

    # If all else fails, return None
    return None


def safe_json_parse(text: str, default: Any = None) -> Any:
    """
    Safely parse JSON with a default fallback

    Args:
        text: Text to parse
        default: Value to return if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        result = extract_json_from_text(text)
        return result if result is not None else default
    except Exception:
        return default


def validate_json_structure(data: Any, required_keys: list) -> bool:
    """
    Validate that JSON has required structure

    Args:
        data: Parsed JSON data
        required_keys: List of required top-level keys

    Returns:
        True if all required keys present
    """
    if not isinstance(data, dict):
        return False

    return all(key in data for key in required_keys)


def extract_json_array(text: str) -> Optional[list]:
    """
    Extract JSON array from text

    Args:
        text: Text containing JSON array

    Returns:
        List or None
    """
    result = extract_json_from_text(text)
    if isinstance(result, list):
        return result
    return None


def extract_json_object(text: str) -> Optional[dict]:
    """
    Extract JSON object from text

    Args:
        text: Text containing JSON object

    Returns:
        Dict or None
    """
    result = extract_json_from_text(text)
    if isinstance(result, dict):
        return result
    return None
