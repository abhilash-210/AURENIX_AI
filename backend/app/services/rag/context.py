"""
Context and Citation building for RAG pipeline.
"""

from typing import Any

from app.services.rag.schemas import Citation, SourceDocument


class ContextBuilder:
    """
    Builds the LLM context prompt from retrieved and reranked chunks with
    deduplication and maximum character token budgeting.
    """

    def __init__(self, max_context_chars: int = 8000) -> None:
        self.max_context_chars = max_context_chars

    def build_context(self, results: list[dict[str, Any]]) -> str:
        """
        Format the chunks into a readable string for the LLM.
        Deduplicates identical/near-identical chunks and enforces max_context_chars.
        """
        if not results:
            return ""

        context_parts: list[str] = []
        seen_texts: set[str] = set()
        current_length = 0

        doc_idx = 1
        for res in results:
            payload = res.get("payload", {})
            text = payload.get("chunk_text", "").strip()
            if not text:
                continue

            # Deduplicate repeated chunks
            normalized_key = " ".join(text.lower().split()[:20])
            if normalized_key in seen_texts:
                continue
            seen_texts.add(normalized_key)

            filename = payload.get("source_filename", "Unknown")
            page = payload.get("page_number")

            meta_str = f"Source: {filename}"
            if page is not None:
                meta_str += f", Page: {page}"

            entry = f"Document [{doc_idx}] ({meta_str}):\n{text}\n"
            if current_length + len(entry) > self.max_context_chars and context_parts:
                # Stop adding more chunks if character budget is exhausted
                break

            context_parts.append(entry)
            current_length += len(entry)
            doc_idx += 1

        return "\n".join(context_parts)


class CitationBuilder:
    """
    Constructs the final Citation objects based on the retrieved results.
    """

    def build_citations(self, results: list[dict[str, Any]]) -> list[Citation]:
        """
        Create structured Citation objects matching the Document [X] indexes
        used in the ContextBuilder.
        """
        citations = []
        for idx, res in enumerate(results, start=1):
            payload = res.get("payload", {})
            
            source = SourceDocument(
                document_id=payload.get("document_id", "unknown"),
                chunk_id=payload.get("chunk_id", "unknown"),
                source_filename=payload.get("source_filename", "Unknown"),
                page_number=payload.get("page_number"),
                relevance_score=res.get("score", 0.0),
            )
            
            citation = Citation(
                citation_id=f"[{idx}]",
                source=source,
                quote=payload.get("chunk_text"),
            )
            citations.append(citation)
            
        return citations
