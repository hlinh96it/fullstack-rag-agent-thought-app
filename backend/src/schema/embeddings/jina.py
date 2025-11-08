from typing import List, Dict
from pydantic import BaseModel


class JinaEmbeddingRequest(BaseModel):
    model: str = 'jina_embeddings-v3'
    task: str = 'retrieval.passage'
    dimensions: int = 1024
    late_chunking: bool = False
    embeding_type: str = 'float'
    input: List[str]
    
class JinaEmbeddingResponse(BaseModel):
    model: str
    object: str = 'list'
    usage: Dict[str, int]
    data: List[Dict]