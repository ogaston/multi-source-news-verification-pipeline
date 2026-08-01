"""Tests for shared agent helpers."""

import pytest
from pydantic import BaseModel

from agents.utils import pydantic_json_default, strip_json_fences


def test_strip_json_fences_removes_json_fence():
    assert strip_json_fences('```json\n{"ok": true}\n```') == '{"ok": true}'


def test_strip_json_fences_preserves_unfenced_json():
    assert strip_json_fences('  {"ok": true}  ') == '{"ok": true}'


def test_strip_json_fences_handles_empty_input():
    assert strip_json_fences(None) == ""


def test_pydantic_json_default_serializes_model():
    class Example(BaseModel):
        value: int

    assert pydantic_json_default(Example(value=3)) == {"value": 3}


def test_pydantic_json_default_rejects_other_objects():
    with pytest.raises(TypeError, match="not JSON serializable"):
        pydantic_json_default(object())
