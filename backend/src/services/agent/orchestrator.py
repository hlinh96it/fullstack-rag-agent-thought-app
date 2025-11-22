"""Agent nodes orchestrator for agentic RAG."""

from typing import Dict

from langfuse.langchain import CallbackHandler

from src.config import Settings
from src.schema.llm.models import AgentState
from src.services.chat.openai_client import OpenAIClient
from src.services.agent.nodes import (
    QueryGenerationNode,
    QuestionRewriteNode,
    AnswerGenerationNode,
    DocumentGradingNode,
)

import logging

logger = logging.getLogger(__name__)


class Nodes:
    """Orchestrates specialized node components for agentic RAG."""

    def __init__(
        self,
        settings: Settings,
        response_model: OpenAIClient,
        grader_model: OpenAIClient,
        langfuse_tracer: CallbackHandler,
    ):
        self.settings = settings
        self.response_model = response_model
        self.grader_model = grader_model
        self.langfuse_tracer = langfuse_tracer

        # Initialize specialized node components
        self.query_gen_node = QueryGenerationNode(
            settings, response_model, langfuse_tracer
        )
        self.rewrite_node = QuestionRewriteNode(
            settings, response_model, langfuse_tracer
        )
        self.answer_node = AnswerGenerationNode(
            settings, grader_model, langfuse_tracer
        )
        self.grading_node = DocumentGradingNode(
            settings, grader_model, langfuse_tracer
        )

    def generate_query_or_response(self, state: AgentState) -> Dict:
        """Generate a query or response based on the current conversation state."""
        return self.query_gen_node.execute(state)

    def _rewrite_question(self, state: AgentState) -> Dict:
        """Rewrite the question to improve retrieval."""
        return self.rewrite_node.execute(state)

    def _generate_answer(self, state: AgentState) -> Dict:
        """Generate a direct answer based on retrieved context."""
        return self.answer_node.execute(state)

    def _grade_documents(self, state: AgentState) -> str:
        """Determine whether the retrieved documents are relevant to the question."""
        return self.grading_node.execute(state)

