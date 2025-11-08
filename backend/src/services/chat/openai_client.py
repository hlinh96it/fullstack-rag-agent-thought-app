from typing import Dict, Any

from pydantic import SecretStr
from fastapi import HTTPException
from langchain_openai.chat_models import ChatOpenAI

from .prompts import RAGPromptBuilder
from src.config import Settings

import logging

logger = logging.getLogger(__name__)


class OpenAIClient:
    prompt_builder = RAGPromptBuilder(default_experties="normal")

    def __init__(self, settings: Settings):
        self.settings = settings.openai
        self.openai_client = ChatOpenAI(
            api_key=SecretStr(self.settings.openai_api_key),
            model=self.settings.model_name,
            temperature=self.settings.temperature,
            timeout=self.settings.timeout,
        )
        self.system_prompt = OpenAIClient.prompt_builder.system_prompt

    def generate_answer(self, query: str):
        conversation = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query},
        ]
        try:
            response = self.openai_client.invoke(conversation)
            return response.content
        except Exception as e:
            logger.error(f"Failed to generated answer: {e}")
            raise
