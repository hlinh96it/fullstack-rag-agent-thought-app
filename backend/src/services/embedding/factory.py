from src.config import Settings
from .jina_client import JinaEmbeddingClient


def make_jina_embedding_client(settings: Settings):
    return JinaEmbeddingClient(settings)