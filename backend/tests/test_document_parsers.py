"""
Unit tests for document parsers, text cleaner, text chunker, and file validators.
"""

from __future__ import annotations

import io
import uuid
import zipfile
import pytest

from app.exceptions import (
    DocumentParsingError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.services.ingestion.chunker import RecursiveTextChunker
from app.services.ingestion.cleaner import clean_text
from app.services.ingestion.parsers.csv import CSVParser
from app.services.ingestion.parsers.docx import DOCXParser
from app.services.ingestion.parsers.factory import ParserFactory
from app.services.ingestion.parsers.pdf import PDFParser
from app.services.ingestion.parsers.txt import TXTParser
from app.services.ingestion.types import ParsedDocument, ParsedPage
from app.services.ingestion.validators import sanitize_filename, validate_file_upload


# ──────────────────────────────────────────────────────────────────────────────
# 1. Sanitizer & Validator Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestValidators:
    def test_sanitize_filename(self):
        assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
        assert sanitize_filename("my report (2026).docx") == "my_report__2026_.docx"
        assert sanitize_filename("") == "unnamed_document"

    def test_validate_file_upload_valid_txt(self):
        ext = validate_file_upload("notes.txt", b"Hello world text", max_size_mb=10)
        assert ext == "txt"

    def test_validate_file_upload_valid_csv(self):
        ext = validate_file_upload("data.csv", b"name,age\nAlice,30", max_size_mb=10)
        assert ext == "csv"

    def test_validate_file_upload_valid_pdf_magic(self):
        content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n"
        ext = validate_file_upload("document.pdf", content, max_size_mb=10)
        assert ext == "pdf"

    def test_validate_file_upload_valid_docx_magic(self):
        content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        ext = validate_file_upload("file.docx", content, max_size_mb=10)
        assert ext == "docx"

    def test_validate_file_upload_invalid_extension(self):
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_upload("script.sh", b"echo hello", max_size_mb=10)

    def test_validate_file_upload_invalid_pdf_magic(self):
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_upload("fake.pdf", b"this is fake pdf text", max_size_mb=10)

    def test_validate_file_upload_too_large(self):
        huge_content = b"A" * (2 * 1024 * 1024)
        with pytest.raises(FileTooLargeError):
            validate_file_upload("big.txt", huge_content, max_size_mb=1)


# ──────────────────────────────────────────────────────────────────────────────
# 2. Text Cleaner Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestTextCleaner:
    def test_clean_text_normalizes_crlf_and_whitespace(self):
        raw = "Line 1\r\nLine 2  \r\n\r\n\r\n\r\nLine 3"
        cleaned = clean_text(raw)
        assert cleaned == "Line 1\nLine 2\n\nLine 3"

    def test_clean_text_strips_control_characters(self):
        raw = "Hello\x00 World\ufeff \x07Control"
        cleaned = clean_text(raw)
        assert cleaned == "Hello World Control"


# ──────────────────────────────────────────────────────────────────────────────
# 3. Format Parser Tests (TXT, CSV, DOCX, PDF)
# ──────────────────────────────────────────────────────────────────────────────


class TestParsers:
    @pytest.mark.asyncio
    async def test_txt_parser_success(self):
        parser = TXTParser()
        content = b"Sample plain text content for testing."
        res = await parser.parse(content, "sample.txt")

        assert res.total_pages == 1
        assert "Sample plain text" in res.pages[0].text

    @pytest.mark.asyncio
    async def test_csv_parser_success(self):
        parser = CSVParser()
        csv_bytes = b"Name,Role,Department\nAlice,Engineer,AI\nBob,Manager,Ops\n"
        res = await parser.parse(csv_bytes, "team.csv")

        assert res.total_pages == 2
        assert res.pages[0].row_number == 1
        assert "Name: Alice" in res.pages[0].text
        assert "Role: Engineer" in res.pages[0].text

    @pytest.mark.asyncio
    async def test_docx_parser_success(self):
        parser = DOCXParser()
        buf = io.BytesIO()
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
            '  <w:body>\n'
            '    <w:p><w:t>First Paragraph</w:t></w:p>\n'
            '    <w:p><w:t>Second Paragraph</w:t></w:p>\n'
            '  </w:body>\n'
            '</w:document>'
        )
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("word/document.xml", doc_xml)

        docx_bytes = buf.getvalue()
        res = await parser.parse(docx_bytes, "test.docx")

        assert res.total_pages == 1
        assert "First Paragraph" in res.pages[0].text
        assert "Second Paragraph" in res.pages[0].text

    @pytest.mark.asyncio
    async def test_docx_parser_corrupt_zip_fails(self):
        parser = DOCXParser()
        with pytest.raises(DocumentParsingError):
            await parser.parse(b"PK\x03\x04Not a zip archive", "corrupt.docx")

    @pytest.mark.asyncio
    async def test_pdf_parser_success(self):
        parser = PDFParser()
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
            b"BT\n(Hello PDF world) Tj\nET\n"
            b"%%EOF"
        )
        res = await parser.parse(pdf_bytes, "sample.pdf")

        assert res.total_pages >= 1
        assert "Hello PDF world" in res.pages[0].text

    def test_parser_factory(self):
        assert isinstance(ParserFactory.get_parser("txt"), TXTParser)
        assert isinstance(ParserFactory.get_parser("csv"), CSVParser)
        assert isinstance(ParserFactory.get_parser("docx"), DOCXParser)
        assert isinstance(ParserFactory.get_parser("pdf"), PDFParser)
        with pytest.raises(UnsupportedFileTypeError):
            ParserFactory.get_parser("exe")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Text Chunker Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestTextChunker:
    def test_chunk_document_preserves_page_metadata(self):
        chunker = RecursiveTextChunker(chunk_size=50, chunk_overlap=10)
        parsed_doc = ParsedDocument(
            pages=[
                ParsedPage(page_number=1, text="Page 1 text content that is relatively long."),
                ParsedPage(page_number=2, text="Page 2 text content."),
            ],
            total_pages=2,
        )
        doc_id = uuid.uuid4()
        chunks = chunker.chunk_document(doc_id, "doc.txt", parsed_doc)

        assert len(chunks) >= 2
        assert chunks[0].page_number == 1
        assert chunks[0].metadata["page_number"] == 1
        assert chunks[0].metadata["source_filename"] == "doc.txt"
        assert chunks[0].metadata["document_id"] == str(doc_id)

    def test_chunk_document_preserves_row_metadata(self):
        chunker = RecursiveTextChunker(chunk_size=100, chunk_overlap=10)
        parsed_doc = ParsedDocument(
            pages=[
                ParsedPage(row_number=1, text="col1: val1, col2: val2"),
                ParsedPage(row_number=2, text="col1: val3, col2: val4"),
            ],
            total_pages=2,
        )
        doc_id = uuid.uuid4()
        chunks = chunker.chunk_document(doc_id, "data.csv", parsed_doc)

        assert len(chunks) == 2
        assert chunks[0].row_number == 1
        assert chunks[1].row_number == 2
