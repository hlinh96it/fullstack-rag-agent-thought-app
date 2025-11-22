"""Question rewriting node for agentic RAG."""

import time
from typing import Dict
from langchain_core.messages import HumanMessage
from langfuse.langchain import CallbackHandler

from src.config import Settings
from src.schema.llm.models import AgentState
from src.services.chat.openai_client import OpenAIClient
from src.services.agent.prompts import AgentPrompt

import logging

logger = logging.getLogger(__name__)


class QuestionRewriteNode:
    """Handles question rewriting to improve retrieval."""

    def __init__(
        self,
        settings: Settings,
        response_model: OpenAIClient,
        langfuse_tracer: CallbackHandler,
    ):
        self.settings = settings
        self.response_model = response_model
        self.langfuse_tracer = langfuse_tracer
        self.agent_prompts = AgentPrompt()

    def execute(self, state: AgentState) -> Dict:
        """Rewrite the question to improve retrieval, maintaining core intent."""
        processing_steps = state.get("processing_steps", [])

        last_human_message = HumanMessage(content="")
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                last_human_message.content = message.content
                break

        question = last_human_message.content

        # Track rewrite attempts
        rewrite_count = state.get("rewrite_count", 0)
        max_rewrites = state.get("max_rewrites", 1)

        if rewrite_count >= max_rewrites:
            logger.warning(
                f"Max rewrites ({max_rewrites}) reached, generating answer from available context"
            )
            return {
                "messages": state["messages"],
                "rewrite_count": rewrite_count,
                "processing_steps": processing_steps,
            }

        new_rewrite_count = rewrite_count + 1
        logger.info(f"Rewriting question (attempt {new_rewrite_count}/{max_rewrites})")

        # Add step: Rewriting question
        processing_steps.append(
            {
                "step_name": "rewrite_question",
                "status": "in_progress",
                "timestamp": time.time(),
                "details": f"Refining question for better retrieval (attempt {new_rewrite_count}/{max_rewrites})",
            }
        )

        # Improved rewrite prompt that maintains semantic core
        prompt = self.agent_prompts.rewrite_prompt.format(question=question)
        response = self.response_model.openai_client.invoke(
            input=[{"role": "user", "content": prompt}],
            config={"callbacks": [self.langfuse_tracer]},
        )
        logger.info(f"Original question: {question}")
        logger.info(f"Rewritten question: {response.content}")

        # Complete the step
        processing_steps.append(
            {
                "step_name": "rewrite_question",
                "status": "completed",
                "timestamp": time.time(),
                "details": "Question refined for better document matching",
            }
        )

        # Create a new message list with system prompt and rewritten question
        new_messages = [
            {"role": "system", "content": self.response_model.system_prompt},
            {"role": "user", "content": response.content},
        ]

        return {
            "messages": new_messages,
            "rewrite_count": new_rewrite_count,
            "search_count": 0,  # Reset search count for the rewritten question
            "processing_steps": processing_steps,
        }
