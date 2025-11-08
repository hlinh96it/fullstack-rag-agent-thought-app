from src.config import Settings

from .factory import make_chat_client


class AgenticRAG:
    """
    This class implements an agentic RAG system that uses a graph-based approach to:
    1. Generate a query or respond directly
    2. Retrieve relevant documents from multiple vector stores
    3. Grade document relevance
    4. Rewrite the question if needed
    5. Generate a final answer
    """ 
    
    
