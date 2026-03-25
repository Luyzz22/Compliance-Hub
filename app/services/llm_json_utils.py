"""Extract JSON objects from LLM text (markdown fences, trailing prose)."""

from __future__ import annotations

import json
import re
from typing import Any


class LLMJsonParseError(ValueError):
    """Could not parse a JSON object from model output."""


def extract_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise LLMJsonParseError("empty model response")
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end <= start:
            raise LLMJsonParseError("no JSON object delimiters in model response")
        raw = raw[start : end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMJsonParseError(str(exc)) from exc
    if not isinstance(data, dict):
        raise LLMJsonParseError("root JSON must be an object")
    return data
