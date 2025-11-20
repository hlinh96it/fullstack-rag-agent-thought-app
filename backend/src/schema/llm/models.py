from typing import TypedDict, List, Optional, Dict, Any

from pydantic import BaseModel, Field
from langgraph.graph import MessagesState


class Message(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    prompt: str
    chat_history: Optional[List[Message]] = None


class RetrievedDocument(BaseModel):
    content: str
    source: Optional[str] = None
    score: Optional[float] = None
    

class ProcessingStep(BaseModel):
    step_name: str
    status: str  # 'completed', 'in_progress', 'failed'
    timestamp: float
    details: Optional[str] = None

    
class AskResponse(BaseModel):
    answer: str
    retrieved_documents: Optional[List[RetrievedDocument]] = []
    processing_steps: Optional[List[ProcessingStep]] = []
    search_count: Optional[int] = 0
    rewrite_count: Optional[int] = 0
    
    
class GradeDocument(BaseModel):
    binary_score: str = Field(description='Relevance score: "yes" if relevant or "no" if not relevant')


class AgentState(MessagesState):
    """Extended state to track search attempts and ensure proper retrieval."""
    search_count: int
    max_searches: int
    rewrite_count: int
    max_rewrites: int
    processing_steps: List[Dict[str, Any]]
    retrieved_documents: List[Dict[str, Any]]