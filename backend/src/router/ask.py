from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.dependencies import ChatDependency
from src.schema.llm.models import AskRequest

ask_router = APIRouter(tags=["ask"])


@ask_router.post(
    "",
    description="Ask LLM with prompt",
    response_model=str,
    response_model_by_alias=False,
)
async def ask_llm(chat_client: ChatDependency, request: AskRequest) -> str:
    try:
        response = chat_client.generate_answer(request.prompt)
    except Exception as e:
        raise HTTPException(
            status_code=422, detail=f"Failed to get response from OpenAI: {e}"
        )
    return response
