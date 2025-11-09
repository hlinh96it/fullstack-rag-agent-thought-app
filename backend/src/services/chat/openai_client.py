from typing import Dict, Any, Optional, List, Type

from pydantic import SecretStr, BaseModel
from langchain_openai.chat_models import ChatOpenAI
from langchain.tools import BaseTool

from .prompts import RAGPromptBuilder
from src.config import Settings

import logging

logger = logging.getLogger(__name__)


class OpenAIClient:
    prompt_builder = RAGPromptBuilder(default_experties="normal")

    def __init__(self, settings: Settings, temperature: Optional[float] = None, 
                 tools: Optional[List[BaseTool]] = None):
        self.settings = settings.openai
        self.openai_client: ChatOpenAI = ChatOpenAI(
            api_key=SecretStr(self.settings.openai_api_key),
            model=self.settings.model_name,
            temperature=temperature if temperature else self.settings.temperature,
            timeout=self.settings.timeout,
        )
        if tools is not None:
            self.openai_client = self.openai_client.bind_tools(tools)  # type: ignore
        self.system_prompt = OpenAIClient.prompt_builder.system_prompt
    
    def with_structured_output(self, schema: Type[BaseModel]):
        """
        Bind a Pydantic model schema to the chat model for structured output.
        
        Args:
            schema: A Pydantic BaseModel class defining the expected output structure
            
        Returns:
            A runnable that will return instances of the provided schema
        """
        return self.openai_client.with_structured_output(schema, include_raw=False)
