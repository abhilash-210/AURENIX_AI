# Aurenix AI — AI Concepts Reference

> **Document Status:** Sprint 0  
> **Audience:** Engineers new to production AI systems, technical reviewers, contributors

This document explains the core AI concepts behind Aurenix AI — not as academic abstractions, but as engineering problems with concrete solutions.

---

## Table of Contents

1. [Large Language Models (LLMs)](#1-large-language-models-llms)
2. [Retrieval-Augmented Generation (RAG)](#2-retrieval-augmented-generation-rag)
3. [Embeddings & Vector Search](#3-embeddings--vector-search)
4. [AI Agents](#4-ai-agents)
5. [Memory Systems](#5-memory-systems)
6. [Evaluation](#6-evaluation)
7. [Prompt Engineering](#7-prompt-engineering)
8. [Glossary](#8-glossary)

---

## 1. Large Language Models (LLMs)

### What they are

LLMs (GPT-4o, Claude, Gemini, Llama) are neural networks trained on vast text corpora to predict the next token given a context window. They are not databases — they do not "know" your company's documents. They are not search engines — they cannot retrieve real-time information without augmentation.

### What they are good at

- Natural language understanding and generation
- Reasoning, summarisation, and synthesis
- Code generation and explanation
- Instruction-following from structured prompts

### What they are bad at (without augmentation)

- Factual recall of private or recent data (hallucination risk)
- Multi-step computation without tool calls
- Persistent memory across conversations
- Knowing *when* they don't know something

### How Aurenix AI uses LLMs

LLMs are the **reasoning core** of every agent. They receive structured prompts (system prompt + context + user query) and generate responses. They never operate in isolation — they are always paired with retrieval, memory, and tool use.

---

## 2. Retrieval-Augmented Generation (RAG)

### The problem RAG solves

LLMs have a fixed knowledge cutoff and cannot access your organisation's private documents. If you ask GPT-4o about your internal policy, it will confabulate an answer. RAG fixes this by **retrieving relevant document chunks** before calling the LLM, and instructing the model to answer only from that context.

### How RAG works (step by step)

```
1. INGESTION (one-time, per document)
   ┌─────────────┐
   │ Raw Document│ PDF, DOCX, TXT, URL
   └──────┬──────┘
          │ Extract text
          ▼
   ┌─────────────┐
   │   Chunks    │ Split into ~500 token segments with ~50 token overlap
   └──────┬──────┘
          │ Generate embedding (numeric vector)
          ▼
   ┌─────────────┐
   │ Vector Store│ Persist chunk + embedding + metadata
   └─────────────┘

2. RETRIEVAL (per query)
   ┌─────────────┐
   │ User Query  │
   └──────┬──────┘
          │ Embed the query
          ▼
   ┌─────────────┐
   │ Vector Store│ Find top-k most similar chunk vectors
   └──────┬──────┘
          │ Return chunks + source metadata
          ▼
   ┌─────────────────┐
   │ Context Assembly│ Pack chunks into LLM context window
   └──────┬──────────┘
          │ Call LLM with: system prompt + chunks + user question
          ▼
   ┌─────────────┐
   │   Answer    │ + Citations pointing to source chunks
   └─────────────┘
```

### Chunking strategy

Chunking is non-trivial. Too large → irrelevant noise in context. Too small → loss of semantic coherence. Aurenix AI uses **recursive character splitting** with sentence-boundary awareness, targeting 500 tokens per chunk with 50-token overlap to preserve cross-boundary context.

### Hybrid retrieval

Semantic search alone misses exact keyword matches (product codes, names, numbers). Aurenix AI combines:
- **Semantic search** (embedding cosine similarity) — captures meaning
- **BM25 keyword search** — captures exact terms
- **Reciprocal Rank Fusion (RRF)** — merges both ranked lists into one

---

## 3. Embeddings & Vector Search

### What an embedding is

An embedding is a fixed-length numeric vector (e.g., 1,536 dimensions) that encodes the semantic meaning of a piece of text. Texts with similar meanings produce vectors that are geometrically close to each other in high-dimensional space.

```
"What is the refund policy?" → [0.12, -0.87, 0.34, ... ] (1,536 numbers)
"How do I get my money back?" → [0.11, -0.89, 0.36, ... ] (very close)
"What is the capital of France?" → [-0.41, 0.23, -0.77, ... ] (far away)
```

### Cosine similarity

The most common similarity metric. Measures the angle between two vectors. A score of 1.0 means identical direction (same meaning). 0.0 means orthogonal (unrelated). -1.0 means opposite.

### Vector store

A specialised database optimised for approximate nearest-neighbour (ANN) search over millions of vectors. Aurenix AI uses:
- **ChromaDB** in development (zero-config, runs in-process)
- **pgvector** in production (PostgreSQL extension, keeps vectors co-located with metadata)

---

## 4. AI Agents

### What makes something an "agent"

A standard LLM call is **reactive**: prompt in, response out. An agent is **agentic**: it can observe, decide, act, observe the result, and repeat — in a loop — until it achieves a goal.

```
Agent Loop:
  Observation → Thought → Action → Observation → Thought → ...
```

### The Supervisor + Specialist pattern

Aurenix AI uses a two-tier topology:

```
User Query
    │
    ▼
Supervisor Agent
  - Classifies intent
  - Selects specialist
  - Manages handoffs
    │
    ├──► Research Agent     (web search + RAG)
    ├──► Q&A Agent          (retrieval + citation)
    ├──► Summarisation Agent (document condensation)
    └──► Code Agent         (code generation + execution)
```

**Why this pattern?**
- Each specialist has a focused system prompt optimised for its task
- The supervisor can chain specialists (research → summarise)
- Individual specialists are independently testable

### LangGraph

LangGraph models agent execution as a **directed graph**. Each node is a function (LLM call, tool call, decision). Edges define transitions. State is typed and explicit. This makes agents:
- Debuggable (you can inspect state at any node)
- Testable (you can unit-test individual nodes)
- Observable (every edge transition is loggable)

### Tool calling

Agents are given a list of tools (functions with typed schemas). When the LLM decides it needs external information, it emits a structured tool call request. The runtime executes the tool and feeds the result back. This is how agents use web search, calculators, and databases without generating hallucinated results.

---

## 5. Memory Systems

### The problem

LLMs are stateless. Without augmentation, every call starts from a blank slate. A production AI system needs multiple memory horizons:

| Horizon | Duration | What it stores |
|---|---|---|
| **In-context** | Current prompt | Last N messages in context window |
| **Short-term** | Current session | Conversation history for current session |
| **Long-term** | Indefinite | User preferences, stated facts, past decisions |
| **Episodic** | Configurable | Timestamped log of past interactions |

### Short-term memory (Redis)

The current conversation window (e.g., last 20 turns) is stored in Redis. Before every LLM call, the agent retrieves this window and prepends it to the context. Redis is used for its sub-millisecond read latency.

### Long-term memory (PostgreSQL)

After each session, a summarisation agent extracts key facts from the conversation (user name, stated preferences, important decisions). These are stored as structured records in PostgreSQL and injected into future sessions.

### Episodic memory

A full timestamped log of interactions. Useful for:
- Debugging: "What did the agent say to this user 3 weeks ago?"
- Personalisation: "When did the user first mention their role?"
- Evaluation: Replay past interactions to test updated agents

---

## 6. Evaluation

### Why LLM evaluation is hard

Unlike traditional software, LLM outputs are probabilistic and subjective. "Is this a good answer?" often has no binary ground truth. Aurenix AI uses **reference-free** evaluation metrics that assess quality without needing manually labelled examples.

### RAGAS Metrics

| Metric | What it measures | How |
|---|---|---|
| **Faithfulness** | Is every claim in the answer grounded in the retrieved context? | LLM-as-judge: extracts claims, verifies each against context |
| **Answer Relevance** | Does the answer actually address the question? | Reverse-generates questions from the answer, compares to original |
| **Context Precision** | Is the retrieved context relevant (low noise)? | Fraction of retrieved chunks that are relevant to the answer |
| **Context Recall** | Does the retrieved context cover all necessary information? | Requires a reference answer; measures coverage |
| **Hallucination Rate** | Fraction of responses containing unsupported claims | Derived from Faithfulness score |

### Evaluation pipeline

Evaluation runs **asynchronously** after every response is delivered, so it never adds latency for the user. Scores are stored in PostgreSQL and aggregated into daily/weekly quality reports.

---

## 7. Prompt Engineering

### System prompts

Every agent has a versioned system prompt that defines its persona, capabilities, constraints, and output format. Aurenix AI treats system prompts as **source code**: they are version-controlled, peer-reviewed, and tested.

### Prompt structure (standard)

```
[ROLE]
You are {agent_name}, a specialist in {domain}.

[CAPABILITIES]
You can: {list of allowed actions}

[CONSTRAINTS]
- Answer only from the provided context.
- If the answer is not in the context, say so explicitly.
- Never fabricate citations.

[CONTEXT]
{retrieved_chunks}

[MEMORY]
{relevant_memory}

[TASK]
{user_query}

[OUTPUT FORMAT]
Respond in structured JSON with keys: answer, citations, confidence.
```

### Chain-of-thought

For complex reasoning tasks, agents are instructed to reason step-by-step before giving a final answer. This significantly reduces errors on multi-step problems.

---

## 8. Glossary

| Term | Definition |
|---|---|
| **ANN** | Approximate Nearest Neighbour — fast vector similarity search |
| **BM25** | Best Match 25 — probabilistic keyword ranking algorithm |
| **Chunk** | A segment of a document, typically 300–700 tokens |
| **Context window** | Maximum tokens an LLM can process in a single call |
| **Embedding** | Dense numeric vector encoding semantic meaning of text |
| **Hallucination** | LLM generating plausible but factually incorrect content |
| **LangGraph** | Python library for building stateful agent workflows as graphs |
| **RAG** | Retrieval-Augmented Generation — grounding LLM answers in retrieved documents |
| **RAGAS** | RAG Assessment — open-source LLM evaluation framework |
| **RRF** | Reciprocal Rank Fusion — algorithm for merging multiple ranked lists |
| **SSE** | Server-Sent Events — HTTP mechanism for server-to-client streaming |
| **Token** | The atomic unit of LLM text processing (~4 characters for English) |
| **Vector store** | Database optimised for ANN search over embedding vectors |
