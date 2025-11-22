"""Answer generation node for agentic RAG."""

import time
from typing import Dict
from langchain_core.messages import HumanMessage
from langfuse.langchain import CallbackHandler

from src.config import Settings
from src.schema.llm.models import AgentState
from src.services.chat.openai_client import OpenAIClient

import logging

logger = logging.getLogger(__name__)


class AnswerGenerationNode:
    """Handles final answer generation based on retrieved context."""

    def __init__(
        self,
        settings: Settings,
        grader_model: OpenAIClient,
        langfuse_tracer: CallbackHandler,
    ):
        self.settings = settings
        self.grader_model = grader_model
        self.langfuse_tracer = langfuse_tracer

    def execute(self, state: AgentState) -> Dict:
        """Generate a direct answer based on retrieved context."""
        processing_steps = state.get("processing_steps", [])

        # Add step: Generating answer
        processing_steps.append(
            {
                "step_name": "generate_answer",
                "status": "in_progress",
                "timestamp": time.time(),
                "details": "Generating comprehensive answer from retrieved context",
            }
        )

        # Find the original user question
        question = None
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                question = msg.content
                break
            elif isinstance(msg, dict) and msg.get("role") == "user":
                question = msg.get("content", "")
                break

        if not question:
            question = (
                state["messages"][0].content
                if state["messages"]
                else "Unknown question"
            )

        # Get the retrieved context from the last ToolMessage
        last_message = state["messages"][-1]
        context = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )

        # Ensure context is a string
        if not isinstance(context, str):
            context = str(context)

        logger.info(f"📝 Generating answer for: {question[:100]}...")
        logger.info(f"📄 Context length: {len(context)} characters")

        # Build prompt for answer generation
        if len(context.strip()) < 50:
            # No meaningful context retrieved
            prompt = (
                f"I couldn't find relevant information in the database to answer: {question}\n\n"
                "Please provide a brief, helpful response suggesting the user try rephrasing their question."
            )
        else:
            # We have context - answer directly based on it
            prompt = (
                f"Answer this question based ONLY on the context provided below. "
                f"Be direct and concise (2-4 sentences).\n\n"
                f"Question: {question}\n\n"
                f"Context:\n{context[:3000]}\n\n"
                f"Answer:"
            )

        # Use grader model (which has no tools bound) for clean text generation
        response = self.grader_model.openai_client.invoke(
            [{"role": "user", "content": prompt}],
            config={"callbacks": [self.langfuse_tracer]},
        )

        logger.info(f"✅ Generated answer: {response.content[:200]}...")

        # Complete the step
        processing_steps.append(
            {
                "step_name": "generate_answer",
                "status": "completed",
                "timestamp": time.time(),
                "details": "Answer generated successfully",
            }
        )

        return {"messages": [response], "processing_steps": processing_steps}
