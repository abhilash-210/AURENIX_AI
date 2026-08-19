"""
Service wrapper for LangGraph multi-agent execution.
"""

import logging

from app.services.agents.graph import create_agent_graph
from app.services.agents.state import AgentState

logger = logging.getLogger(__name__)


class AgentOrchestratorService:
    """
    Entry point for executing the multi-agent RAG workflow.
    """
    
    def __init__(self) -> None:
        self.graph = create_agent_graph()

    async def execute_query(self, workspace_id: str, user_id: str, query: str) -> dict:
        """
        Execute the agent workflow and return the final state and answer.
        """
        initial_state: AgentState = {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "original_query": query,
            "plan": "",
            "search_queries": [],
            "retrieved_documents": [],
            "analysis": "",
            "critic_feedback": "",
            "is_approved": False,
            "final_answer": "",
            "iterations": 0,
        }

        logger.info(f"Starting agent orchestration for query: {query}")
        
        try:
            # Await the execution of the state graph
            final_state = await self.graph.ainvoke(initial_state)
            return {
                "answer": final_state.get("final_answer", "Error computing answer."),
                "iterations": final_state.get("iterations", 0),
                "plan": final_state.get("plan", ""),
                "state": final_state,
            }
        except Exception as exc:
            logger.exception("Agent orchestration failed.")
            return {
                "answer": "An unexpected error occurred during research.",
                "iterations": 0,
                "plan": "",
                "state": initial_state,
            }
