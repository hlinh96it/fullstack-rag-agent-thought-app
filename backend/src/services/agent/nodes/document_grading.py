"""Document grading node for agentic RAG."""

import time
from typing import Dict
from langfuse.langchain import CallbackHandler

from src.config import Settings
from src.schema.llm.models import AgentState, GradeDocument
from src.services.chat.openai_client import OpenAIClient
from src.services.agent.prompts import AgentPrompt

import logging

logger = logging.getLogger(__name__)


class DocumentGradingNode:
    """Handles document relevance grading."""

    def __init__(
        self,
        settings: Settings,
        grader_model: OpenAIClient,
        langfuse_tracer: CallbackHandler,
    ):
        self.settings = settings
        self.grader_model = grader_model
        self.langfuse_tracer = langfuse_tracer
        self.agent_prompts = AgentPrompt()

    def execute(self, state: AgentState) -> str:
        """
        Determine whether the retrieved documents are relevant to the question.
        Uses a more lenient grading strategy to avoid false negatives.
        """
        processing_steps = state.get("processing_steps", [])

        # Add step: Grading documents
        processing_steps.append(
            {
                "step_name": "grade_documents",
                "status": "in_progress",
                "timestamp": time.time(),
                "details": "Evaluating relevance of retrieved documents",
            }
        )

        question = state["messages"][0].content
        last_message = state["messages"][-1]

        # Extract actual document content from tool message
        if hasattr(last_message, "content"):
            context = last_message.content
        else:
            context = str(last_message)

        # Ensure context is a string
        if not isinstance(context, str):
            context = str(context)

        logger.info(f"📊 Grading retrieved documents")
        logger.info(f"❓ Question: {question[:100]}...")
        logger.info(f"📄 Context length: {len(context)} characters")
        logger.info(f"📄 Context preview: {context[:300]}...")

        # If we have substantial context, be more lenient
        context_length = len(context.strip())
        if context_length < 50:
            logger.warning(
                f"⚠️  Very short context ({context_length} chars), likely no documents found"
            )
            processing_steps.append(
                {
                    "step_name": "grade_documents",
                    "status": "completed",
                    "timestamp": time.time(),
                    "details": "No relevant documents found",
                }
            )

            # Short context means retrieval likely failed
            rewrite_count = state.get("rewrite_count", 0)
            max_rewrites = state.get("max_rewrites", 2)

            if rewrite_count >= max_rewrites:
                logger.info(
                    "⚠️  No documents found and max rewrites reached, generating answer anyway"
                )
                return "generate_answer"
            else:
                logger.info(
                    f"🔄 No documents found, rewriting question (attempt {rewrite_count + 1}/{max_rewrites})"
                )
                return "rewrite_question"

        # Use more lenient grading prompt
        prompt = self.agent_prompts.grade_prompt.format(
            question=question, context=context[:2000]
        )

        try:
            response = self.grader_model.with_structured_output(GradeDocument).invoke(
                [{"role": "user", "content": prompt}],
                config={"callbacks": [self.langfuse_tracer]},
            )

            # Grade the document and route accordingly
            binary_score = (
                response.binary_score
                if isinstance(response, GradeDocument)
                else response.get("binary_score", "no")
            )
        except Exception as e:
            logger.error(
                f"❌ Grading failed: {str(e)}, defaulting to 'yes' to avoid blocking"
            )
            # If grading fails, be optimistic and proceed
            binary_score = "yes"

        rewrite_count = state.get("rewrite_count", 0)
        max_rewrites = state.get("max_rewrites", 1)

        logger.info(f"📝 Document relevance score: {binary_score}")
        logger.info(f"🔄 Rewrite count: {rewrite_count}/{max_rewrites}")

        if binary_score.lower() == "yes":
            logger.info("✅ Document is relevant, proceeding to generate answer")
            processing_steps.append(
                {
                    "step_name": "grade_documents",
                    "status": "completed",
                    "timestamp": time.time(),
                    "details": "Documents are relevant to your question",
                }
            )
            return "generate_answer"
        else:
            if rewrite_count >= max_rewrites:
                logger.info(
                    f"⚠️  Document not highly relevant but max rewrites ({max_rewrites}) reached, generating answer anyway"
                )
                processing_steps.append(
                    {
                        "step_name": "grade_documents",
                        "status": "completed",
                        "timestamp": time.time(),
                        "details": "Using available documents despite lower relevance",
                    }
                )
                return "generate_answer"
            else:
                logger.info(
                    f"🔄 Document is not relevant, rewriting question (attempt {rewrite_count + 1}/{max_rewrites})"
                )
                processing_steps.append(
                    {
                        "step_name": "grade_documents",
                        "status": "completed",
                        "timestamp": time.time(),
                        "details": "Documents not highly relevant, refining search",
                    }
                )
                return "rewrite_question"
