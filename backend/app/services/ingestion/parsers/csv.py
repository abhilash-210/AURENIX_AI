"""
CSV file parser implementation.
"""

from __future__ import annotations

import csv
import io

from app.exceptions import DocumentParsingError
from app.services.ingestion.cleaner import clean_text
from app.services.ingestion.parsers.base import BaseDocumentParser
from app.services.ingestion.types import ParsedDocument, ParsedPage


class CSVParser(BaseDocumentParser):
    """
    Parses comma-separated values (.csv) files into row-level ParsedPages.
    """

    @property
    def supported_extension(self) -> str:
        return "csv"

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        try:
            text_data = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text_data = content.decode("latin-1")
            except Exception as exc:
                msg = f"Failed to decode CSV file '{filename}': {exc}"
                raise DocumentParsingError(msg) from exc

        stream = io.StringIO(text_data)
        try:
            reader = csv.reader(stream)
            rows = list(reader)
        except Exception as exc:
            msg = f"Failed to parse CSV syntax in '{filename}': {exc}"
            raise DocumentParsingError(msg) from exc

        if not rows:
            msg = f"CSV file '{filename}' is empty."
            raise DocumentParsingError(msg)

        header = rows[0] if len(rows) > 1 else None
        data_rows = rows[1:] if header else rows

        pages: list[ParsedPage] = []
        for i, row in enumerate(data_rows, start=1):
            if not row or not any(field.strip() for field in row):
                continue

            if header and len(header) == len(row):
                row_str = ", ".join(f"{h.strip()}: {val.strip()}" for h, val in zip(header, row) if val.strip())
            else:
                row_str = ", ".join(val.strip() for val in row if val.strip())

            cleaned_row = clean_text(row_str)
            if cleaned_row:
                pages.append(ParsedPage(row_number=i, page_number=None, text=cleaned_row))

        if not pages:
            msg = f"No non-empty data rows found in CSV file '{filename}'."
            raise DocumentParsingError(msg)

        return ParsedDocument(
            pages=pages,
            total_pages=len(pages),
            metadata={"columns": len(header) if header else (len(rows[0]) if rows else 0)},
        )
