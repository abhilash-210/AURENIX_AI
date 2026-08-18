"""
DOCX Microsoft Word document parser implementation.
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

from app.exceptions import DocumentParsingError
from app.services.ingestion.cleaner import clean_text
from app.services.ingestion.parsers.base import BaseDocumentParser
from app.services.ingestion.types import ParsedDocument, ParsedPage


class DOCXParser(BaseDocumentParser):
    """
    Parses .docx Microsoft Word documents using ZIP XML extraction.
    """

    @property
    def supported_extension(self) -> str:
        return "docx"

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        paragraphs: list[str] = []

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                if "word/document.xml" not in zf.namelist():
                    msg = f"Invalid .docx file '{filename}': missing word/document.xml"
                    raise DocumentParsingError(msg)

                doc_xml = zf.read("word/document.xml")
                root = ET.fromstring(doc_xml)

                # XML namespaces in Word processing ML
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

                # Extract text paragraph by paragraph
                for p_elem in root.findall(".//w:p", ns):
                    texts = [t_elem.text for t_elem in p_elem.findall(".//w:t", ns) if t_elem.text]
                    p_text = "".join(texts).strip()
                    if p_text:
                        paragraphs.append(p_text)
        except zipfile.BadZipFile as exc:
            msg = f"File '{filename}' is not a valid zip/docx archive: {exc}"
            raise DocumentParsingError(msg) from exc
        except ET.ParseError as exc:
            msg = f"Failed to parse XML in docx file '{filename}': {exc}"
            raise DocumentParsingError(msg) from exc
        except DocumentParsingError:
            raise
        except Exception as exc:
            msg = f"Unexpected error reading docx file '{filename}': {exc}"
            raise DocumentParsingError(msg) from exc

        if not paragraphs:
            msg = f"No text content found in DOCX document '{filename}'."
            raise DocumentParsingError(msg)

        full_text = clean_text("\n\n".join(paragraphs))
        page = ParsedPage(page_number=1, text=full_text)

        return ParsedDocument(
            pages=[page],
            total_pages=1,
            metadata={"paragraph_count": len(paragraphs)},
        )
