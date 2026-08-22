import asyncio
import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.llm.providers.mock import MockLLMProvider
from app.services.llm.types import ChatMessage, CompletionOptions

async def main():
    provider = MockLLMProvider()
    
    # Test 1: Test general question with no context
    messages = [
        ChatMessage(role="user", content="Hello!")
    ]
    resp = await provider.complete(messages, CompletionOptions())
    print("Test 1 (No Context):", resp.content)
    
    # Test 2: Test context-aware objective query with a non-Abhilash document (e.g. sql.docx details)
    system_prompt = (
        "You are an AI assistant answering questions based strictly on the provided context.\n"
        "Use the provided Document [X] tags to cite your sources (e.g., 'As stated in [1]...').\n"
        "Context:\n"
        "Document [1] (Source: sql.docx, Page: 1):\n"
        "The objective of this document is to outline the SQL database schema migration strategy "
        "and guidelines for the engineering department.\n"
        "Document [2] (Source: sql.docx, Page: 2):\n"
        "This project will upgrade postgresql engines from version 12 to 16.\n\n"
        "Relevant Past Memories:\n"
        "No relevant memories found."
    )
    
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content="give me the objective of the document")
    ]
    resp = await provider.complete(messages, CompletionOptions())
    print("\nTest 2 (Objective Query):", resp.content)
    
    # Test 3: Test context-aware overview query
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content="what is the document about?")
    ]
    resp = await provider.complete(messages, CompletionOptions())
    print("\nTest 3 (Overview Query):", resp.content)

    # Test 4: Generic fallback query
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content="what version of postgresql are we upgrading to?")
    ]
    resp = await provider.complete(messages, CompletionOptions())
    print("\nTest 4 (Relevance Query):", resp.content)

    # Test 5: Specific Page Query
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content="give me the info on page 2")
    ]
    resp = await provider.complete(messages, CompletionOptions())
    print("\nTest 5 (Page 2 Query):", resp.content)

if __name__ == "__main__":
    asyncio.run(main())
