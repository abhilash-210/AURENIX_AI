"""
LangGraph node definitions.
"""

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from app.services.agents.state import AgentState
from app.services.llm.service import LLMService
from app.services.llm.types import ChatMessage, CompletionOptions
from app.services.mcp.registry import ToolRegistry
from app.services.rag.retriever import Retriever

logger = logging.getLogger(__name__)


class PlannerOutput(BaseModel):
    plan: str = Field(description="The strategy to answer the question.")
    search_queries: list[str] = Field(description="Search queries to execute against the vector DB.")


class CriticOutput(BaseModel):
    is_approved: bool = Field(description="True if the analysis answers the query, False otherwise.")
    feedback: str = Field(description="Feedback on what is missing or incorrect.")


async def planner_node(state: AgentState) -> dict[str, Any]:
    """
    Breaks down the user's query into a search strategy.
    """
    llm = LLMService()
    
    system_prompt = (
        "You are a Planner Agent. Analyze the user query and generate a plan to answer it. "
        "Also generate 1-3 targeted search queries to extract information from the vector database."
    )
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=state["original_query"]),
    ]
    
    try:
        response = await llm.complete_structured(
            messages=messages,
            response_schema=PlannerOutput,
            options=CompletionOptions(temperature=0.0)
        )
        return {
            "plan": response.parsed.plan,
            "search_queries": response.parsed.search_queries,
            "iterations": state.get("iterations", 0) + 1,
        }
    except Exception as exc:
        logger.error(f"Planner failed: {exc}")
        # Fallback in case of LLM error
        return {
            "plan": "Fallback plan: Execute raw query.",
            "search_queries": [state["original_query"]],
            "iterations": state.get("iterations", 0) + 1,
        }


async def retriever_node(state: AgentState) -> dict[str, Any]:
    """
    Executes search queries securely scoped to the workspace.
    """
    retriever = Retriever()
    all_results = []
    seen_ids = set()
    
    # If the retrieved_documents list is getting huge, we might not want to fetch more,
    # but for simplicity we fetch for all current search queries.
    for query in state.get("search_queries", []):
        results = await retriever.retrieve(
            workspace_id=state["workspace_id"],
            query=query,
            top_k=3,
        )
        for res in results:
            if res["id"] not in seen_ids:
                seen_ids.add(res["id"])
                all_results.append(res)
                
    return {"retrieved_documents": all_results}


async def research_node(state: AgentState) -> dict[str, Any]:
    """
    Synthesizes the retrieved context and executes tools to answer the question.
    """
    llm = LLMService()
    docs = state.get("retrieved_documents", [])
    tool_results = state.get("tool_results", [])
    
    context_parts = []
    if docs:
        context_parts.append("Retrieved Documents:")
        for i, doc in enumerate(docs):
            context_parts.append(f"[{i+1}] {doc['payload'].get('chunk_text', '')}")
            
    if tool_results:
        context_parts.append("\nTool Execution Results:")
        for res in tool_results:
            context_parts.append(f"Tool [{res['tool_name']}]: {res['content']}")
            
    if not context_parts:
        return {"analysis": "No relevant documents or tool results were found to answer the query.", "tool_calls": []}
        
    context_str = "\n".join(context_parts)
    
    # We provide the available tools to the LLM so it knows it can call them
    registry = ToolRegistry.get_instance()
    # In a full implementation we would parse these into the `tools` parameter of the LLMService
    # For this Sprint, we just simulate the LLM requesting a tool via text structure.
    
    system_prompt = (
        "You are a Research Agent. Using ONLY the provided context and tool results, write a comprehensive analysis "
        "that answers the user's original query. Cite sources using [1], [2], etc.\n"
        "If you still lack information and there are tools available, you may request a tool call by writing: \n"
        "`TOOL_CALL: tool_name | arg_key=arg_val`"
    )
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=f"Query: {state['original_query']}\n\nContext:\n{context_str}"),
    ]
    
    try:
        response = await llm.complete(
            messages=messages,
            options=CompletionOptions(temperature=0.0)
        )
        
        # Simple string-based tool call detection for MVP (LangGraph typically uses native LLM tool calling)
        if "TOOL_CALL:" in response.content:
            line = [l for l in response.content.split("\n") if l.startswith("TOOL_CALL:")][0]
            parts = line.replace("TOOL_CALL:", "").strip().split("|")
            tool_name = parts[0].strip()
            # Simplistic argument parsing for MVP
            args = {}
            if len(parts) > 1:
                for kv in parts[1].split(","):
                    k, v = kv.split("=")
                    args[k.strip()] = v.strip()
            
            return {"tool_calls": [{"tool_name": tool_name, "arguments": args}]}
            
        return {"analysis": response.content, "tool_calls": []}
    except Exception as exc:
        logger.error(f"Research failed: {exc}")
        return {"analysis": "Error during analysis generation.", "tool_calls": []}


async def tool_node(state: AgentState) -> dict[str, Any]:
    """
    Executes MCP tools securely.
    """
    calls = state.get("tool_calls", [])
    registry = ToolRegistry.get_instance()
    
    results = []
    for call in calls:
        res = await registry.execute_tool(call["tool_name"], call["arguments"])
        results.append(res.model_dump())
        
    # Clear tool_calls so we don't infinitely loop
    return {"tool_results": results, "tool_calls": []}


async def critic_node(state: AgentState) -> dict[str, Any]:
    """
    Evaluates if the analysis sufficiently answers the original query.
    """
    llm = LLMService()
    analysis = state.get("analysis", "")
    
    # If we found no documents, there's no point looping back to research unless we change queries.
    # We will just approve it so the final answer node can tell the user we found nothing.
    if "No relevant documents" in analysis or state.get("iterations", 0) >= 3:
        return {"is_approved": True, "critic_feedback": "Auto-approved due to limits or empty context."}
        
    system_prompt = (
        "You are a Critic Agent. Evaluate if the Analysis thoroughly answers the User Query. "
        "If it does, approve it. If it is missing information, reject it and provide feedback on what to search for next."
    )
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=f"Query: {state['original_query']}\nAnalysis: {analysis}"),
    ]
    
    try:
        response = await llm.complete_structured(
            messages=messages,
            response_schema=CriticOutput,
            options=CompletionOptions(temperature=0.0)
        )
        return {
            "is_approved": response.parsed.is_approved,
            "critic_feedback": response.parsed.feedback,
            "search_queries": [response.parsed.feedback] if not response.parsed.is_approved else [],
        }
    except Exception as exc:
        logger.error(f"Critic failed: {exc}")
        return {"is_approved": True, "critic_feedback": "Fallback approval due to error."}


async def final_answer_node(state: AgentState) -> dict[str, Any]:
    """
    Formats the final output for the user.
    """
    analysis = state.get("analysis", "")
    return {"final_answer": analysis}
