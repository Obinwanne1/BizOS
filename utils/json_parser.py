"""Robust JSON extraction from Claude output.

Claude may wrap output in:
  - ```json ... ```
  - ``` ... ```
  - plain JSON
  - JSON embedded in prose
"""
import json
import re
from typing import Any


def extract_json_object(text: str) -> dict | None:
    """Extract first valid JSON object from text. Returns None if none found."""
    # Strip ```json ... ``` or ``` ... ``` blocks first
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Walk through text finding balanced braces
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = None
    return None


def extract_json_array(text: str) -> list | None:
    """Extract first valid JSON array from text. Returns None if none found."""
    # Strip ```json ... ``` or ``` ... ``` blocks first
    fenced = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Walk through text finding balanced brackets
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = None
    return None


def extract_json(text: str, expect: str = "object") -> Any:
    """Extract JSON from text. expect: 'object' | 'array'."""
    if expect == "array":
        result = extract_json_array(text)
        if result is not None:
            return result
        # Maybe it's a JSON object with an array inside — try object first
        obj = extract_json_object(text)
        if obj:
            for v in obj.values():
                if isinstance(v, list):
                    return v
        return []

    result = extract_json_object(text)
    return result if result is not None else {}
