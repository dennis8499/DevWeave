"""Bounded diagnostics that discard prompt, reasoning, and secret content."""

from __future__ import annotations

import re

SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|password|secret)\b\s*[:=]\s*([^\s,;]+)"
)
SECRET_TOKEN = re.compile(r"\b(?:sk|sess|token)-[A-Za-z0-9_-]{8,}\b")
PRIVATE_FIELD = re.compile(r'(?i)"(?:prompt|reasoning|input_text)"\s*:\s*"(?:[^"\\]|\\.)*"')


def redact(value: str) -> str:
    result = PRIVATE_FIELD.sub('"private_content":"<discarded>"', value)
    result = SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=<redacted>", result)
    return SECRET_TOKEN.sub("<redacted>", result)


def bounded_text(value: bytes | str, *, max_bytes: int = 65_536) -> tuple[str, bool]:
    decoded = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
    sanitized = redact(decoded)
    encoded = sanitized.encode("utf-8")
    if len(encoded) <= max_bytes:
        return sanitized, False
    suffix = b"\n<diagnostic-truncated>"
    clipped = encoded[: max(0, max_bytes - len(suffix))]
    while clipped:
        try:
            return (clipped + suffix).decode("utf-8"), True
        except UnicodeDecodeError:
            clipped = clipped[:-1]
    return suffix.decode("utf-8"), True
