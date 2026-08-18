"""
Metadata-preserving text chunker for the document ingestion pipeline.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.services.ingestion.types import ParsedDocument, RawChunk


class RecursiveTextChunker:
    """
    Splits ParsedDocument pages into chunks while preserving page & row metadata.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        self.chunk_size = max(chunk_size, 50)
        self.chunk_overlap = min(chunk_overlap, self.chunk_size // 2)

    def _split_text(self, text: str) -> list[str]:
        """Split plain text into chunks of chunk_size with chunk_overlap."""
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

        def _recursive_split(sub_text: str) -> list[str]:
            if len(sub_text) <= self.chunk_size:
                return [sub_text]

            for sep in separators:
                if not sep:
                    # Hard break by character count
                    res: list[str] = []
                    step = self.chunk_size - self.chunk_overlap
                    for i in range(0, len(sub_text), step):
                        res.append(sub_text[i : i + self.chunk_size])
                    return res

                if sep in sub_text:
                    parts = sub_text.split(sep)
                    res = []
                    current_chunk = ""
                    for part in parts:
                        candidate = f"{current_chunk}{sep}{part}" if current_chunk else part
                        if len(candidate) <= self.chunk_size:
                            current_chunk = candidate
                        else:
                            if current_chunk:
                                res.append(current_chunk)
                            if len(part) > self.chunk_size:
                                res.extend(_recursive_split(part))
                                current_chunk = ""
                            else:
                                current_chunk = part
                    if current_chunk:
                        res.append(current_chunk)
                    return res
            return [sub_text]

        sub_chunks = _recursive_split(text)

        # Apply overlap to contiguous sub_chunks
        final_chunks: list[str] = []
        for i, sc in enumerate(sub_chunks):
            chunk_str = sc.strip()
            if not chunk_str:
                continue
            final_chunks.append(chunk_str)

        return final_chunks

    def chunk_document(
        self,
        document_id: uuid.UUID,
        source_filename: str,
        parsed_doc: ParsedDocument,
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[RawChunk]:
        """
        Convert a ParsedDocument into a sequence of RawChunks with metadata.
        """
        raw_chunks: list[RawChunk] = []
        chunk_counter = 0
        base_meta = extra_metadata or {}

        for page in parsed_doc.pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            text_chunks = self._split_text(page_text)
            for t_chunk in text_chunks:
                chunk_id = f"chunk_{document_id}_{chunk_counter}"
                meta = {
                    "document_id": str(document_id),
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_counter,
                    "source_filename": source_filename,
                    "page_number": page.page_number,
                    "row_number": page.row_number,
                    "char_count": len(t_chunk),
                    **base_meta,
                }

                raw_chunks.append(
                    RawChunk(
                        chunk_id=chunk_id,
                        document_id=str(document_id),
                        chunk_index=chunk_counter,
                        content=t_chunk,
                        page_number=page.page_number,
                        row_number=page.row_number,
                        char_count=len(t_chunk),
                        metadata=meta,
                    ),
                )
                chunk_counter += 1

        return raw_chunks
