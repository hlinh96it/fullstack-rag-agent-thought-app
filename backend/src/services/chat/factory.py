from .openai_client import OpenAIClient
from src.config import Settings


def make_chat_client(settings: Settings, client_type: str = "openai") -> OpenAIClient:
    return OpenAIClient(settings=settings)
