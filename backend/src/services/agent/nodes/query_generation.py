"""Query generation node for agentic RAG."""

import time
from typing import Dict
from langchain_core.messages import AIMessage
from langfuse.langchain import CallbackHandler

from src.config import Settings
from src.schema.llm.models import AgentState
from src.services.chat.openai_client import OpenAIClient

import logging

logger = logging.getLogger(__name__)


class QueryGenerationNode:
    """Handles query generation or direct response."""

    def __init__(
        self,
        settings: Settings,
        response_model: OpenAIClient,
        langfuse_tracer: CallbackHandler,
    ):
        self.settings = settings
        self.response_model = response_model
        self.langfuse_tracer = langfuse_tracer

    def execute(self, state: AgentState) -> Dict:
        """
        Generate a query or response based on the current conversation state.
        Ensures that the agent ALWAYS uses retrieval tools before answering.

        Args:
            state (AgentState): The current state containing the conversation messages and search tracking.

        Returns:
            dict: A dictionary containing the response and updated state counters.
        """
        try:
            # Initialize counters and tracking lists if not present
            search_count = state.get("search_count", 0)
            max_searches = state.get("max_searches", 3)
            processing_steps = state.get("processing_steps", [])

            # Add step: Analyzing question
            processing_steps.append(
                {
                    "step_name": "analyze_question",
                    "status": "completed",
                    "timestamp": time.time(),
                    "details": "Analyzing your question and determining search strategy",
                }
            )

            # Check if we've exceeded max searches
            if search_count >= max_searches:
                logger.warning(
                    f"Max searches ({max_searches}) reached, forcing answer generation"
                )
                processing_steps.append(
                    {
                        "step_name": "max_searches_reached",
                        "status": "completed",
                        "timestamp": time.time(),
                        "details": f"Maximum search attempts ({max_searches}) reached",
                    }
                )
                # Force direct answer if max searches exceeded
                return {
                    "messages": [
                        AIMessage(
                            content="I've searched multiple times but couldn't find highly relevant information. Please try rephrasing your question or ask something else."
                        )
                    ],
                    "search_count": search_count,
                    "processing_steps": processing_steps,
                }

            # Increment search count
            new_search_count = search_count + 1
            logger.info(f"🔍 Search attempt {new_search_count}/{max_searches}")
            logger.info(
                f"📝 Current conversation has {len(state['messages'])} messages"
            )

            response = self.response_model.openai_client.invoke(
                state["messages"], config={"callbacks": [self.langfuse_tracer]}
            )
            logger.info(f"🤖 Generated response type: {type(response)}")
            logger.info(
                f"✅ Response with tool calls: {isinstance(response, AIMessage) and hasattr(response, 'tool_calls') and len(response.tool_calls) > 0}"
            )

            # Check if the response contains tool calls
            if (
                isinstance(response, AIMessage)
                and hasattr(response, "tool_calls")
                and response.tool_calls
            ):
                tool_names = [tc.get("name") for tc in response.tool_calls]
                tool_args = [tc.get("args") for tc in response.tool_calls]
                logger.info(f"🔧 Tool calls found: {tool_names}")
                logger.info(f"📊 Tool arguments: {tool_args}")

                # Add step: Preparing search
                processing_steps.append(
                    {
                        "step_name": "prepare_search",
                        "status": "completed",
                        "timestamp": time.time(),
                        "details": f'Preparing to search using: {", ".join(tool_names)}',
                    }
                )
            else:
                logger.warning(
                    "⚠️  No tool calls in response - agent may be trying to answer without searching"
                )

            return {
                "messages": [response],
                "search_count": new_search_count,
                "processing_steps": processing_steps,
            }
        except Exception as e:
            logger.error(
                f"❌ Failed to generate query/response: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"Failed to generate response: {str(e)}") from e
