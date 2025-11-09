from typing import TypedDict, List, Optional, Dict, Any

from pydantic import BaseModel, Field


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
