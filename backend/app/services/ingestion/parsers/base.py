"""
Abstract base class for document format parsers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from app.services.ingestion.types import ParsedDocument


class BaseDocumentParser(ABC):
    """
    Interface for document format text extractors.
    """

    @property
    @abstractmethod
    def supported_extension(self) -> str:
        """Return target file extension handled by parser (e.g. 'pdf', 'docx')."""
        ...

    @abstractmethod
    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """
        Parse binary file content into a ParsedDocument instance.

        Args:
            content: Raw binary file bytes.
            filename: Original filename.

        Returns:
            ParsedDocument containing extracted pages and metadata.

        Raises:
            DocumentParsingError: If file is corrupted or text extraction fails.
        """
        ...
