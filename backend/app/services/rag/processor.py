"""
Query processor for RAG pipeline.
"""


class QueryProcessor:
    """
    Pre-processes user queries before retrieval.
    This can be expanded to include spelling correction, keyword extraction, or query expansion.
    """

    def process(self, query: str) -> str:
        """
        Clean and normalize the user query.
        """
        cleaned = query.strip()
        # Prevent completely empty queries from causing vector DB errors
        if not cleaned:
            return " "
        return cleaned
