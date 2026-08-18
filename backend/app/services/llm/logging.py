"""
Secret-safe logging and telemetry utilities for the LLM Gateway.

Ensures API keys, auth tokens, and credentials are never leaked to logs or traces.
"""

from __future__ import annotations

import logging
import re
from typing import Any

# Regex patterns matching API keys and tokens (OpenAI sk-..., Anthropic x-api-key, Bearer tokens, etc.)
SECRET_PATTERNS = [
    (re.compile(r"(sk-[A-Za-z0-9T3BlbkFJ_\-]{20,})"), "sk-***REDACTED***"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(x-api-key:\s*)[A-Za-z0-9_\-]{10,}", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"(api_key=)[A-Za-z0-9_\-]{10,}", re.IGNORECASE), r"\1***REDACTED***"),
]

SENSITIVE_HEADER_KEYS = {
    "authorization",
    "x-api-key",
    "api-key",
    "proxy-authorization",
}


def sanitize_text(text: str) -> str:
    """Mask any known secret pattern inside plain text string."""
    if not text:
        return text
    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a dictionary of HTTP headers with sensitive authorization values masked."""
    cleaned: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADER_KEYS:
            cleaned[k] = "***REDACTED***"
        else:
            cleaned[k] = sanitize_text(v)
    return cleaned


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively scrub sensitive keys and values from a dictionary."""
    scrubbed: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in ("api_key", "secret", "token", "password", "auth")):
            scrubbed[key] = "***REDACTED***"
        elif isinstance(value, dict):
            scrubbed[key] = sanitize_dict(value)
        elif isinstance(value, list):
            scrubbed[key] = [
                sanitize_dict(item) if isinstance(item, dict) else (sanitize_text(str(item)) if isinstance(item, str) else item)
                for item in value
            ]
        elif isinstance(value, str):
            scrubbed[key] = sanitize_text(value)
        else:
            scrubbed[key] = value
    return scrubbed


def log_llm_request(
    logger: logging.Logger,
    provider: str,
    model: str,
    message_count: int,
    options: dict[str, Any],
) -> None:
    """Log an outgoing LLM request safely without leaking prompt data or secrets."""
    safe_options = sanitize_dict(options)
    logger.info(
        "LLM request initiated",
        extra={
            "provider": provider,
            "model": model,
            "message_count": message_count,
            "options": safe_options,
        },
    )


def log_llm_response(
    logger: logging.Logger,
    provider: str,
    model: str,
    duration_ms: float,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    """Log LLM completion response metrics safely."""
    logger.info(
        "LLM response received",
        extra={
            "provider": provider,
            "model": model,
            "duration_ms": round(duration_ms, 2),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    )
