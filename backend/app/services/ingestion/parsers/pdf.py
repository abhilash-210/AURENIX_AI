"""
PDF document parser implementation.
"""

from __future__ import annotations

import io
import re

from app.exceptions import DocumentParsingError
from app.services.ingestion.cleaner import clean_text
from app.services.ingestion.parsers.base import BaseDocumentParser
from app.services.ingestion.types import ParsedDocument, ParsedPage


class PDFParser(BaseDocumentParser):
    """
    Parses PDF documents into page-structured ParsedPages.
    """

    @property
    def supported_extension(self) -> str:
        return "pdf"

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        # 1. Try pypdf library if available
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(content))
            pages: list[ParsedPage] = []
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                cleaned = clean_text(text)
                if cleaned:
                    pages.append(ParsedPage(page_number=i, text=cleaned))

            if pages:
                return ParsedDocument(pages=pages, total_pages=len(reader.pages))
        except ImportError:
            pass
        except Exception as exc:
            # Fall through to raw stream parser if pypdf raises
            pass

        # 2. Native PDF stream parser fallback
        pages = self._extract_pdf_pages_native(content, filename)
        if not pages:
            msg = f"Failed to extract readable text content from PDF document '{filename}'."
            raise DocumentParsingError(msg)

        return ParsedDocument(pages=pages, total_pages=len(pages))

    def _extract_pdf_pages_native(self, content: bytes, filename: str) -> list[ParsedPage]:
        """
        Pure Python fallback parser that extracts text stream contents per page.
        """
        pages: list[ParsedPage] = []
        try:
            # Split raw PDF by page markers or stream objects
            raw_str = content.decode("latin-1", errors="replace")

            # Extract text blocks inside BT (Begin Text) ... ET (End Text)
            bt_et_blocks = re.findall(r"BT(.*?)ET", raw_str, flags=re.DOTALL)
            if not bt_et_blocks:
                # Try finding literal parentheses text strings
                strings = re.findall(r"\((.*?)\)\s*Tj", raw_str)
                if strings:
                    text_content = clean_text("\n".join(strings))
                    if text_content:
                        return [ParsedPage(page_number=1, text=text_content)]
                return []

            extracted_chunks: list[str] = []
            for block in bt_et_blocks:
                # Find (string) Tj or [(string1) ... (stringN)] TJ
                tj_matches = re.findall(r"\((.*?)\)\s*(?:Tj|TJ|\'|\")", block)
                if tj_matches:
                    text_part = "".join(tj_matches)
                    if text_part.strip():
                        extracted_chunks.append(text_part.strip())

            if extracted_chunks:
                full_text = clean_text("\n\n".join(extracted_chunks))
                if full_text:
                    pages.append(ParsedPage(page_number=1, text=full_text))
        except Exception as exc:
            msg = f"Error during PDF fallback text extraction in '{filename}': {exc}"
            raise DocumentParsingError(msg) from exc

        return pages
