import re


class QueryProcessor:
    """
    Pre-processes user queries before retrieval, including conversational
    intent detection to bypass unnecessary vector search.
    """

    GREETING_PATTERNS = [
        r"^(hi|hello|hey|greetings|howdy)\b",
        r"^good\s+(morning|afternoon|evening|day)\b",
        r"^(thank\s*you|thanks|thx)\b",
        r"^(who\s+are\s+you|what\s+is\s+your\s+name)\b",
    ]

    def process(self, query: str) -> str:
        """
        Clean and normalize the user query.
        """
        cleaned = query.strip()
        # Prevent completely empty queries from causing vector DB errors
        if not cleaned:
            return " "
        return cleaned

    def is_conversational_greeting(self, query: str) -> bool:
        """
        Detect if a query is a pure conversational greeting or courtesy phrase.
        """
        normalized = query.strip().lower()
        # If query is long (> 6 words), treat as complex question even if it starts with greeting
        if len(normalized.split()) > 6:
            return False

        for pattern in self.GREETING_PATTERNS:
            if re.search(pattern, normalized):
                return True
        return False
