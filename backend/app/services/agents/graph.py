"""
LangGraph state graph orchestration.
"""

from typing import Literal

from langgraph.graph import END, StateGraph

from app.services.agents.nodes import (
    critic_node,
    final_answer_node,
    planner_node,
    research_node,
    retriever_node,
    tool_node,
)
from app.services.agents.state import AgentState


def should_continue(state: AgentState) -> Literal["retriever_node", "tool_node", "final_answer_node"]:
    """
    Conditional routing logic based on the Critic's output or Tool Intents.
    """
    if state.get("tool_calls"):
        return "tool_node"
        
    if state.get("is_approved"):
        return "final_answer_node"
    
    # If the critic rejected it but we hit our max iterations (to prevent infinite loops)
    if state.get("iterations", 0) >= 3:
        return "final_answer_node"
        
    # Otherwise, loop back to retrieval with the new search queries from the critic
    return "retriever_node"


def create_agent_graph() -> StateGraph:
    """
    Builds and compiles the RAG multi-agent orchestration graph.
    """
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("planner_node", planner_node)
    workflow.add_node("retriever_node", retriever_node)
    workflow.add_node("research_node", research_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("critic_node", critic_node)
    workflow.add_node("final_answer_node", final_answer_node)

    # Define strict edges
    workflow.set_entry_point("planner_node")
    workflow.add_edge("planner_node", "retriever_node")
    workflow.add_edge("retriever_node", "research_node")
    
    # Tool execution conditionally routes back to research
    workflow.add_edge("tool_node", "research_node")
    
    workflow.add_edge("research_node", "critic_node")

    # Conditional routing from critic
    workflow.add_conditional_edges(
        "critic_node",
        should_continue,
        {
            "tool_node": "tool_node",
            "retriever_node": "retriever_node",
            "final_answer_node": "final_answer_node",
        },
    )

    # Exit edge
    workflow.add_edge("final_answer_node", END)

    return workflow.compile()
