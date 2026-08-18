"""
Plain text file parser implementation.
"""

from __future__ import annotations

from app.exceptions import DocumentParsingError
from app.services.ingestion.cleaner import clean_text
from app.services.ingestion.parsers.base import BaseDocumentParser
from app.services.ingestion.types import ParsedDocument, ParsedPage


class TXTParser(BaseDocumentParser):
    """
    Parses plain text (.txt) files.
    """

    @property
    def supported_extension(self) -> str:
        return "txt"

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        raw_text: str | None = None

        for enc in encodings:
            try:
                raw_text = content.decode(enc)
                break
            except (UnicodeDecodeError, ValueError):
                continue

        if raw_text is None:
            msg = f"Failed to decode text file '{filename}' with supported encodings."
            raise DocumentParsingError(msg)

        cleaned = clean_text(raw_text)
        if not cleaned:
            msg = f"Text file '{filename}' contains no readable text content."
            raise DocumentParsingError(msg)

        page = ParsedPage(page_number=1, text=cleaned)
        return ParsedDocument(pages=[page], total_pages=1, metadata={"encoding": "utf-8"})
