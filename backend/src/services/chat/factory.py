from typing import Optional, List, Dict, Any
from langchain.tools import BaseTool

from .openai_client import OpenAIClient
from src.services.agent.agent import AgenticRAG
from src.config import Settings


def make_chat_client(
        settings: Settings, temperature: Optional[float] = None, tools: Optional[List[BaseTool]] = None
) -> OpenAIClient:
    return OpenAIClient(settings=settings, temperature=temperature, tools=tools)


def make_agent_client(settings: Settings, vector_stores: Optional[List[Dict[str, Any]]] = None) -> AgenticRAG:
    """
    Factory function to create an AgenticRAG instance.
    
    Args:
        settings: Application settings
        vector_stores: List of vector store configurations. Each config should have:
            - store: The Milvus vector store instance
            - name: Name of the retriever tool
            - description: Description of what the retriever searches
            - k (optional): Number of documents to retrieve (default: 2)
            - ranker_weights (optional): Weights for ranking (default: [0.6, 0.4])
    
    Returns:
        AgenticRAG instance configured with the provided vector stores
    """
    if vector_stores is None:
        vector_stores = []
    
    return AgenticRAG(settings=settings, vector_stores=vector_stores)
