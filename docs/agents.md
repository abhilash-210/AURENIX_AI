# Aurenix AI — Multi-Agent Architecture & LangGraph Workflows

> **Module:** `backend/app/services/agents/`  
> **Framework:** LangGraph & LangChain Core  
> **Status:** Production-Ready | Stateful Checkpointing

---

## 1. Multi-Agent Design Paradigm

Aurenix AI uses **LangGraph StateGraph** workflows to coordinate autonomous multi-step reasoning, dynamic tool invocation, memory synthesis, and safety guardrails.

```
                      ┌───────────────────────────┐
                      │        Agent Entry        │
                      └─────────────┬─────────────┘
                                    │
                                    ▼
                      ┌───────────────────────────┐
                      │    1. Planner / Router    │
                      │    (Analyzes intent)      │
                      └─────────────┬─────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
        ┌─────────────────────────┐   ┌─────────────────────────┐
        │  2. Direct Answer Node  │   │   3. Tool Reasoner Node │
        │  (Conversational/Simple)│   │   (Determines tool call)│
        └────────────┬────────────┘   └────────────┬────────────┘
                     │                             │
                     │                             ▼
                     │                ┌─────────────────────────┐
                     │                │   4. Tool Executor Node │
                     │                │   (MCP / Custom Tools)  │
                     │                └────────────┬────────────┘
                     │                             │
                     │                ┌────────────▼────────────┐
                     │                │   5. Synthesizer Node   │
                     │                │   (Assembles final res) │
                     │                └────────────┬────────────┘
                     │                             │
                     └──────────────┬──────────────┘
                                    │
                                    ▼
                      ┌───────────────────────────┐
                      │      Response Output      │
                      └───────────────────────────┘
```

---

## 2. State Schema (`AgentState`)

```python
class AgentState(TypedDict):
    messages: list[BaseMessage]
    workspace_id: str
    user_id: str
    tools_available: list[str]
    current_step: int
    max_steps: int
    memory_context: list[str]
    scratchpad: dict[str, Any]
```

---

## 3. Supported Specialized Agents

1. **Research & RAG Agent**: Synthesizes cross-document evidence from Qdrant vector store and constructs attributed citations.
2. **Analysis & Code Agent**: Executes calculations, structured data transformation, and JSON schema formatting.
3. **Enterprise Integration Agent**: Interacts with Model Context Protocol (MCP) servers and external APIs with granular permission enforcement.

---

## 4. Guardrails & Termination Criteria

* **Max Recursion Limit**: Capped at 10 execution loops to prevent runaway tool iterations.
* **Deterministic Fallback**: If an agent fails to conclude within bounds, the synthesizer returns a graceful degradation response citing intermediate results.
