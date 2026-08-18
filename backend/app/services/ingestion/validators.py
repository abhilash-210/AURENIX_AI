"""
File upload validation and security utilities for document ingestion.
"""

from __future__ import annotations

import os
import re
from app.exceptions import FileTooLargeError, UnsupportedFileTypeError

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv"}

# Magic signature byte checks for security verification
MAGIC_SIGNATURES = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and unsafe character injection.

    Example: '../../etc/passwd.pdf' -> 'etc_passwd.pdf'
    """
    if not filename:
        return "unnamed_document"

    # Strip any directory path components
    clean_name = os.path.basename(filename)

    # Replace unsafe characters with underscore, keeping alphanumeric, dot, hyphen, underscore
    clean_name = re.sub(r"[^\w\.\-]", "_", clean_name)

    # Prevent hidden files or relative dots
    clean_name = clean_name.lstrip(".")
    if not clean_name:
        clean_name = "unnamed_document"

    return clean_name


def validate_file_upload(
    filename: str,
    content: bytes,
    max_size_mb: int = 10,
) -> str:
    """
    Validate file extension, size, and magic header signatures.

    Args:
        filename: Name of the uploaded file.
        content: Binary file content bytes.
        max_size_mb: Maximum allowed file size in MB.

    Returns:
        Canonical file extension string (e.g. 'pdf', 'docx', 'txt', 'csv').

    Raises:
        UnsupportedFileTypeError: If extension or magic signature is unsupported.
        FileTooLargeError: If size exceeds max_size_mb.
    """
    if not content:
        msg = "Uploaded file is empty (0 bytes)."
        raise UnsupportedFileTypeError(msg)

    # 1. Size check
    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        msg = f"File size ({len(content)} bytes) exceeds the maximum limit of {max_size_mb} MB."
        raise FileTooLargeError(msg)

    # 2. Extension check
    _, ext = os.path.splitext(filename.lower())
    if ext not in SUPPORTED_EXTENSIONS:
        msg = f"File extension '{ext}' is not supported. Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        raise UnsupportedFileTypeError(msg)

    # 3. Magic header / binary safety check
    if ext in MAGIC_SIGNATURES:
        expected_header = MAGIC_SIGNATURES[ext]
        if not content.startswith(expected_header):
            msg = f"File content magic bytes do not match expected signature for extension '{ext}'."
            raise UnsupportedFileTypeError(msg)
    elif ext in {".txt", ".csv"}:
        # Ensure text files do not contain binary null bytes (\x00)
        if b"\x00" in content[:4096]:
            msg = f"File '{filename}' contains binary data and cannot be parsed as plain text or CSV."
            raise UnsupportedFileTypeError(msg)

    return ext.lstrip(".")
