"""
Factory for resolving format-specific document parsers.
"""

from __future__ import annotations

from app.exceptions import UnsupportedFileTypeError
from app.services.ingestion.parsers.base import BaseDocumentParser
from app.services.ingestion.parsers.csv import CSVParser
from app.services.ingestion.parsers.docx import DOCXParser
from app.services.ingestion.parsers.pdf import PDFParser
from app.services.ingestion.parsers.txt import TXTParser


class ParserFactory:
    """
    Registry and factory manager for document format parsers.
    """

    _parsers: dict[str, BaseDocumentParser] = {
        "txt": TXTParser(),
        "csv": CSVParser(),
        "docx": DOCXParser(),
        "pdf": PDFParser(),
    }

    @classmethod
    def get_parser(cls, extension: str) -> BaseDocumentParser:
        """
        Return the parser registered for extension.

        Raises:
            UnsupportedFileTypeError: If extension is unrecognised.
        """
        canonical_ext = extension.strip().lstrip(".").lower()
        if canonical_ext not in cls._parsers:
            msg = f"No parser registered for file extension '.{canonical_ext}'."
            raise UnsupportedFileTypeError(msg)
        return cls._parsers[canonical_ext]
