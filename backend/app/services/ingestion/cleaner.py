"""
Text cleaning and normalization utilities for extracted document content.
"""

from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted document text.

    - Strips zero-width spaces, BOM markers, null bytes.
    - Removes non-printable control characters (except \\n, \\t).
    - Normalizes CRLF (\\r\\n) to LF (\\n).
    - Collapses excessive blank lines (3+ \\n -> 2 \\n).
    - Strips trailing whitespace per line.
    """
    if not text:
        return ""

    # 1. Remove zero-width spaces, BOM, null bytes
    cleaned = text.replace("\ufeff", "").replace("\u200b", "").replace("\x00", "")

    # 2. Normalize CRLF / CR to LF
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Strip non-printable control characters (keep tab \t and newline \n)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)

    # 4. Strip trailing whitespace from each line
    lines = [line.rstrip() for line in cleaned.split("\n")]
    cleaned = "\n".join(lines)

    # 5. Collapse 3+ consecutive newlines into double newline
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()
