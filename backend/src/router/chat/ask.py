from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict

from src.dependencies import AgentDependency
from src.schema.llm.models import AskRequest, AskResponse

ask_router = APIRouter(tags=["ask"])


@ask_router.post(
    "",
    description="Ask LLM with prompt using Agentic RAG",
    response_model=AskResponse,
    response_model_by_alias=False,
)
async def ask_llm(agent_client: AgentDependency, request: AskRequest) -> AskResponse:
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Received request: prompt='{request.prompt[:100]}...', chat_history length={len(request.chat_history) if request.chat_history else 0}")
        response = agent_client.run(request)
        logger.info(f"Agent returned response: {response}")
        logger.info(f"Response type: {type(response)}, answer: {response.answer[:100] if response.answer else 'None'}...")
        return response
    except Exception as e:
        logger.error(f"Error in ask_llm: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=422, detail=f"Failed to get response from Agent: {e}"
        )


@ask_router.get(
    "/status",
    description="Get agent status and available tools",
    response_model=Dict,
)
async def get_agent_status(agent_client: AgentDependency) -> Dict:
    """Get information about the agent's capabilities and status."""
    try:
        tools_info = [
            {
                "name": vs["name"],
                "description": vs["description"],
                "k": vs.get("k", 2)
            }
            for vs in agent_client.vector_stores
        ]
        
        return {
            "status": "active",
            "model": agent_client.settings.openai.model_name,
            "available_tools": tools_info,
            "system_prompt": agent_client.response_model.system_prompt
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent status: {e}"
        )
