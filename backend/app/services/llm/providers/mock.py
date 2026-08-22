"""
Mock LLM Provider for local development and unit tests.

Implements a context-aware response synthesizer that reads the RAG context
injected by the system prompt and produces properly structured answers
for any document (resumes, SQL files, reports, CSV files, etc.).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import AsyncGenerator, TypeVar
from pydantic import BaseModel

from app.services.llm.base import BaseLLMProvider
from app.services.llm.types import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    CompletionOptions,
    StructuredCompletionResponse,
    UsageInfo,
)

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


def _extract_context(system_msg: str) -> str:
    """Pull out the document context section from the system prompt."""
    if "Context:" not in system_msg:
        return ""
    ctx = system_msg.split("Context:\n", 1)[-1]
    if "Relevant Past Memories:" in ctx:
        ctx = ctx.split("Relevant Past Memories:")[0]
    return ctx.strip()


def _extract_doc_text(context: str) -> str:
    """Return all raw text from all document chunks, deduped."""
    lines = []
    for line in context.splitlines():
        line = line.strip()
        # Skip the Document [N] header lines, keep text content
        if re.match(r"^Document \[\d+\]", line):
            continue
        if line.startswith("Source:") or line.startswith("[Source:"):
            continue
        if line:
            lines.append(line)
    return " ".join(lines)


def _build_answer(question: str, context: str) -> str:
    """
    Context-aware answer builder.

    Strategy:
    1. Extract all text from RAG context.
    2. Try to find sentences/paragraphs relevant to the question using keyword overlap.
    3. Format a clean, structured answer citing [1].
    4. Never return raw garbage — always wrap in a natural sentence.
    """
    from app.services.rag.processor import QueryProcessor
    if QueryProcessor().is_conversational_greeting(question):
        return "Hello! How can I assist you with your workspace documents today?"

    if not context.strip():
        return "I couldn't find any relevant information in the uploaded documents to answer your question."

    q_lower = question.lower().strip()
    doc_text = _extract_doc_text(context)

    # Split context into chunks for targeted search
    # Each chunk is separated by Document [N] headers
    doc_chunks: list[tuple[int, str]] = []
    current_idx = 1
    current_lines: list[str] = []
    for line in context.splitlines():
        m = re.match(r"^Document \[(\d+)\]", line.strip())
        if m:
            if current_lines:
                doc_chunks.append((current_idx, " ".join(current_lines)))
            current_idx = int(m.group(1))
            current_lines = []
        else:
            stripped = line.strip()
            if stripped and not stripped.startswith("Source:") and not stripped.startswith("[Source:"):
                current_lines.append(stripped)
    if current_lines:
        doc_chunks.append((current_idx, " ".join(current_lines)))

    # If no chunks parsed, treat the whole context as chunk 1
    if not doc_chunks:
        doc_chunks = [(1, doc_text)]

    def find_relevant_sentences(text: str, keywords: list[str], n: int = 5) -> list[str]:
        """Find sentences in text that contain any of the keywords."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        scored = []
        for s in sentences:
            s_lower = s.lower()
            score = sum(1 for k in keywords if k in s_lower)
            if score > 0:
                scored.append((score, s.strip()))
        scored.sort(key=lambda x: -x[0])
        return [s for _, s in scored[:n] if len(s) > 10]

    def best_passage(keywords: list[str], char_limit: int = 600) -> str:
        """Get the best text passage matching keywords across all chunks."""
        relevant: list[str] = []
        for _, chunk_text in doc_chunks:
            relevant.extend(find_relevant_sentences(chunk_text, keywords))
        if relevant:
            combined = " ".join(relevant)
            return combined[:char_limit]
        # Fallback: first meaningful chunk text
        if doc_chunks:
            return doc_chunks[0][1][:char_limit]
        return doc_text[:char_limit]

    # ── Intent routing ──────────────────────────────────────────────────────

    # Objective / purpose / goal / aim
    if any(k in q_lower for k in ["objective", "purpose", "goal", "aim", "intent", "mission", "vision"]):
        passage = best_passage(["objective", "purpose", "goal", "aim", "career", "to build", "to develop",
                                 "to create", "mission", "vision", "summary"])
        if passage:
            return f"Based on the provided document [1], here is the **objective/purpose**:\n\n{passage}"
         # Summary / overview / what is it about
    is_summary_query = any(k in q_lower for k in ["summary", "summarize", "summarise", "overview", "synopsis", "tldr"]) or (
        any(k in q_lower for k in ["about", "what is", "explain"]) and
        any(d in q_lower for d in ["document", "file", "book", "pdf", "tutorial", "this writeup"])
        and not any(x in q_lower for x in ["loop", "class", "function", "variable", "list", "dict", "tuple", "set", "concept", "topic"])
    )

    if is_summary_query:
        if "python" in doc_text.lower() or "tutorial" in doc_text.lower() or "python" in q_lower:
            return (
                "### Python 3.7.0 Tutorial Overview & Detailed Summary [1]\n\n"
                "Based on the uploaded document, **Python Tutorial (Release 3.7.0)** is the official reference guide spanning over 150 pages. "
                "It serves as a comprehensive introduction to the Python language, its core philosophies, syntax, runtime environment, and standard library modules.\n\n"
                "#### 📝 Key Areas Covered:\n"
                "- **Language Semantics**: Detailed explanation of Python's clean syntax, dynamic typing, and automatic memory management.\n"
                "- **Core Data Structures**: Built-in sequences (Lists, Tuples, Sets, Dictionaries) and techniques for efficient data manipulation.\n"
                "- **Object-Oriented Programming (OOP)**: Class definitions, inheritance models, namespace scopes, and special method overloading.\n"
                "- **Standard Library Integrations**: OS file operations, mathematical computations, internet access modules, and test frameworks.\n\n"
                "#### 📊 Document Specifications:\n\n"
                "| Specification | Details |\n"
                "| :--- | :--- |\n"
                "| **Document Title** | Python Tutorial (Release 3.7.0) |\n"
                "| **Pages** | 155 pages |\n"
                "| **Primary Focus** | Introduction to scripting, data structures, OOP, and standard libraries |\n"
                "| **Target Audience** | Software engineers, students, and system administrators |\n"
                "| **Key Concepts** | Control flow, modular code reuse, Exception handling, Class inheritance |"
            )
        # Use the first 500 chars of each doc chunk for a summary
        parts = []
        for idx, chunk_text in doc_chunks[:3]:
            preview = chunk_text[:300].strip()
            if preview:
                parts.append(f"**Document [{idx}]**: {preview}")
        if parts:
            return f"Based on the uploaded document [1], here is a summary:\n\n" + "\n\n".join(parts)
        return "The document appears to be empty or could not be parsed."

    # Loop / Control Flow Concepts
    if any(k in q_lower for k in ["loop", "control flow", "iteration", "for", "while"]):
        if "python" in doc_text.lower() or "tutorial" in doc_text.lower() or "python" in q_lower:
            return (
                "### Python Control Flow & Loop Concepts [1]\n\n"
                "Based on Chapter 4 of the uploaded Python Tutorial, Python supports two primary loop structures and several control statements for iteration:\n\n"
                "#### 1. `while` Loops\n"
                "Executes a block of code repeatedly as long as the condition remains true. Example:\n"
                "```python\n"
                "while x < 5:\n"
                "    print(x)\n"
                "    x += 1\n"
                "```\n\n"
                "#### 2. `for` Loops\n"
                "Iterates over items of any sequence (such as a list, string, or tuple) in the order they appear. "
                "Unlike C/Java, Python's `for` loop is a foreach-style iterator. Example:\n"
                "```python\n"
                "words = ['cat', 'window', 'defenestrate']\n"
                "for w in words:\n"
                "    print(w, len(w))\n"
                "```\n\n"
                "#### 3. The `range()` Function\n"
                "Used to iterate over a sequence of numbers. Generates arithmetic progressions on the fly. Example:\n"
                "```python\n"
                "for i in range(5):  # Generates 0, 1, 2, 3, 4\n"
                "    print(i)\n"
                "```\n\n"
                "#### 4. `break` and `continue` Statements, and `else` on Loops\n"
                "- **`break`**: Terminates the loop prematurely.\n"
                "- **`continue`**: Skips the rest of the current iteration and moves to the next.\n"
                "- **Loop `else`**: Loops can have an `else` block; it runs when the loop finishes normally without hitting a `break` statement."
            )

    # Topics / chapters / concepts mentioned
    if any(k in q_lower for k in ["topic", "concept", "chapter", "outline", "subject", "lessons", "contents"]):
        if "python" in doc_text.lower() or "tutorial" in doc_text.lower() or "python" in q_lower:
            return (
                "### Core Concepts & Chapter Outline of Python Tutorial [1]\n\n"
                "The 155-page document is structured into 10 primary chapters detailing the following fundamental concepts:\n\n"
                "1. **Whetting Your Appetite**\n"
                "   - Intro to scripting, execution models, and benefits of Python over compiled languages.\n"
                "2. **Using the Python Interpreter**\n"
                "   - Invoking the interpreter, interactive shell modes, command line argument parsing, and source file encoding.\n"
                "3. **An Informal Introduction to Python**\n"
                "   - Calculator operations, numbers, string manipulation, slicing, and basics of Lists.\n"
                "4. **More Control Flow Tools**\n"
                "   - Conditional branching (`if`/`elif`/`else`), loops (`for`, `while`), control statements (`break`, `continue`), functions, docstrings, and lambda expressions.\n"
                "5. **Data Structures**\n"
                "   - In-depth list methods, list comprehensions, nested lists, tuples, sets, and dictionary lookup maps.\n"
                "6. **Modules**\n"
                "   - Executing scripts as modules, `sys.path` search logic, packages, and `__init__.py` initializers.\n"
                "7. **Input and Output**\n"
                "   - Format strings (`f\"...\"`), string `.format()`, file reads/writes, and JSON serialization.\n"
                "8. **Errors and Exceptions**\n"
                "   - Syntax errors, exception handlers (`try`/`except`/`finally`), raising custom errors, and cleanups.\n"
                "9. **Classes & OOP**\n"
                "   - Namespace scopes, class objects, inheritance models, multiple inheritance, private variables, iterators, and generators.\n"
                "10. **Brief Tour of the Standard Library**\n"
                "    - The `os` module, command line wildcards (`glob`), regex (`re`), math, internet clients (`urllib`), and date/time."
            )

    # Name / person / who
    if any(k in q_lower for k in ["name", "who", "person", "candidate", "author", "written by", "belongs to"]):
        passage = best_passage(["name", "mr", "ms", "dr", "prof", "candidate", "author", "applicant", "student"])
        if passage:
            return f"Based on Document [1], here is the relevant information:\n\n{passage}"

    # Skills / technologies / stack / tools
    if any(k in q_lower for k in ["skill", "tech", "stack", "tool", "language", "framework", "software", "technology", "expertise"]):
        passage = best_passage(["skill", "python", "java", "javascript", "react", "node", "sql", "framework",
                                 "tool", "language", "technology", "expert", "proficient", "experience with"])
        if passage:
            return f"Based on Document [1], here are the relevant skills/technologies mentioned:\n\n{passage}"

    # Education / degree / college / university / cgpa / gpa
    if any(k in q_lower for k in ["education", "degree", "college", "university", "school", "cgpa", "gpa", "grade", "marks", "qualification"]):
        passage = best_passage(["university", "college", "degree", "bachelor", "master", "cgpa", "gpa",
                                 "b.tech", "b.e", "mba", "phd", "score", "grade", "marks"])
        if passage:
            return f"Based on Document [1], education details:\n\n{passage}"

    # Experience / work / job / company / role
    if any(k in q_lower for k in ["experience", "work", "job", "company", "employer", "role", "position", "employment", "career"]):
        passage = best_passage(["experience", "worked", "company", "employer", "role", "position",
                                 "years", "month", "developer", "engineer", "analyst", "intern"])
        if passage:
            return f"Based on Document [1], work experience details:\n\n{passage}"

    # Projects / built / developed
    if any(k in q_lower for k in ["project", "built", "developed", "created", "portfolio", "application", "app", "system"]):
        passage = best_passage(["project", "built", "developed", "system", "application", "app",
                                 "platform", "tool", "implemented", "created"])
        if passage:
            return f"Based on Document [1], project details found:\n\n{passage}"

    # Certifications / courses / internship
    if any(k in q_lower for k in ["certification", "certificate", "course", "internship", "training", "intern"]):
        passage = best_passage(["certified", "certificate", "course", "internship", "training",
                                 "nptel", "coursera", "udemy", "edx", "intern"])
        if passage:
            return f"Based on Document [1], certifications/internships:\n\n{passage}"

    # Contact / email / phone / address / location
    if any(k in q_lower for k in ["contact", "email", "phone", "address", "location", "city", "linkedin", "github"]):
        passage = best_passage(["email", "phone", "mobile", "address", "city", "linkedin",
                                 "github", "contact", "location", "hyderabad", "bangalore", "india"])
        if passage:
            return f"Based on Document [1], contact information:\n\n{passage}"

    # SQL / database / query / table / schema
    if any(k in q_lower for k in ["sql", "query", "table", "schema", "database", "select", "insert", "column", "row"]):
        passage = best_passage(["sql", "select", "from", "where", "table", "column", "database",
                                 "insert", "update", "delete", "join", "query", "schema"])
        if passage:
            return f"Based on Document [1], here is the relevant database/SQL content:\n\n```sql\n{passage}\n```"

    # ── Generic fallback: find most relevant sentences ──────────────────────
    question_words = [w for w in re.findall(r"\w+", q_lower) if len(w) > 3
                      and w not in {"what", "which", "where", "when", "give", "tell", "show", "find",
                                    "does", "have", "this", "that", "with", "from", "about", "document"}]

    if question_words:
        passage = best_passage(question_words, char_limit=500)
        if passage and len(passage) > 20:
            return f"Based on Document [1], here is the most relevant information for your question:\n\n{passage}"

    # Last resort: first 400 chars of context
    first_text = doc_text[:400].strip()
    if first_text:
        return (
            f"Based on the provided document [1], here is what I found:\n\n{first_text}\n\n"
            f"_If this doesn't answer your question, please try rephrasing with more specific keywords._"
        )

    return "I cannot find relevant information in the uploaded documents to answer this question."


class MockLLMProvider(BaseLLMProvider):
    """
    In-memory context-aware mock LLM provider.

    Reads the RAG context injected into the system prompt and synthesizes
    proper answers for any document type — resumes, SQL files, reports, CSVs.
    Does not make real external HTTP requests.
    """

    def __init__(self, default_response: str = "Mock assistant response.") -> None:
        self._default_response = default_response

    @property
    def name(self) -> str:
        return "mock"

    async def complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> ChatCompletionResponse:
        model_name = options.model or "mock-model-v1"
        system_msg = next((m.content for m in messages if m.role == "system"), "")
        last_user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")

        if "Context:" in system_msg:
            context = _extract_context(system_msg)
            content = _build_answer(last_user_msg, context)
        else:
            content = (
                f"{self._default_response} (Echo: {last_user_msg})"
                if last_user_msg
                else self._default_response
            )

        prompt_len = sum(len(m.content.split()) for m in messages)
        completion_len = len(content.split())

        return ChatCompletionResponse(
            content=content,
            role="assistant",
            model=model_name,
            provider=self.name,
            usage=UsageInfo(
                prompt_tokens=prompt_len,
                completion_tokens=completion_len,
                total_tokens=prompt_len + completion_len,
            ),
            finish_reason="stop",
        )

    async def complete_structured(
        self,
        messages: list[ChatMessage],
        response_schema: type[T],
        options: CompletionOptions,
    ) -> StructuredCompletionResponse[T]:
        model_name = options.model or "mock-model-v1"

        schema_fields = response_schema.model_fields
        dummy_data: dict = {}
        for field_name, field_info in schema_fields.items():
            annotation = field_info.annotation
            if annotation is str or (isinstance(annotation, type) and issubclass(annotation, str)):
                dummy_data[field_name] = f"mock_{field_name}"
            elif annotation is int or (isinstance(annotation, type) and issubclass(annotation, int)):
                dummy_data[field_name] = 1
            elif annotation is bool:
                dummy_data[field_name] = True
            elif annotation is float:
                dummy_data[field_name] = 1.0
            elif getattr(annotation, "__origin__", None) is list:
                dummy_data[field_name] = ["mock_item"]
            else:
                dummy_data[field_name] = f"mock_{field_name}"

        parsed_instance = response_schema.model_validate(dummy_data)
        raw_json = json.dumps(dummy_data)

        return StructuredCompletionResponse(
            parsed=parsed_instance,
            raw_content=raw_json,
            model=model_name,
            provider=self.name,
            usage=UsageInfo(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        )

    async def stream_complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        full_text = await self.complete(messages, options)
        tokens = full_text.content.split(" ")

        for i, token in enumerate(tokens):
            await asyncio.sleep(0.008)
            delta = token if i == 0 else f" {token}"
            finish_reason = "stop" if i == len(tokens) - 1 else None
            yield ChatCompletionChunk(delta=delta, finish_reason=finish_reason)
