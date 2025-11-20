from typing import List, Dict, Any

from src.config import Settings
from .agent import AgenticRAG


def make_agent_client(settings: Settings, vector_stores: List[Dict[str, Any]]):
    return AgenticRAG(settings=settings, vector_stores=vector_stores)