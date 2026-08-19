"""
Context and Citation building for RAG pipeline.
"""

from typing import Any

from app.services.rag.schemas import Citation, SourceDocument


class ContextBuilder:
    """
    Builds the LLM context prompt from retrieved and reranked chunks.
    """

    def build_context(self, results: list[dict[str, Any]]) -> str:
        """
        Format the chunks into a readable string for the LLM.
        We assign an index [1], [2], etc., to each chunk to encourage the LLM to cite them.
        """
        if not results:
            return ""

        context_parts = []
        for idx, res in enumerate(results, start=1):
            payload = res.get("payload", {})
            text = payload.get("chunk_text", "")
            filename = payload.get("source_filename", "Unknown")
            page = payload.get("page_number")
            
            meta_str = f"Source: {filename}"
            if page is not None:
                meta_str += f", Page: {page}"
                
            context_parts.append(f"Document [{idx}] ({meta_str}):\n{text}\n")
            
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
