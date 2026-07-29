#!/usr/bin/env python3
"""Compatibility shim: full document text storage is no longer required."""
from __future__ import annotations

from typing import Any


def validate_source_text(record: dict[str, Any]) -> list[str]:
    """Return no errors; lean policy JSON intentionally omits full source text."""
    return []
