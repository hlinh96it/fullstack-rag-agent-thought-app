from typing import Dict

from langchain_core.messages import HumanMessage, AIMessage
from langfuse.langchain import CallbackHandler

from src.config import Settings
from src.schema.llm.models import AgentState, GradeDocument
from src.services.chat.openai_client import OpenAIClient

from .prompts import AgentPrompt

import time

import logging

logger = logging.getLogger(__name__)


class Nodes:
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
        self.agent_prompts = AgentPrompt()

    def generate_query_or_response(self, state: AgentState):
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

    def _rewrite_question(self, state: AgentState) -> Dict:
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
        max_rewrites = state.get("max_rewrites", 1)  # Default to 1 rewrite max

        if rewrite_count >= max_rewrites:
            logger.warning(
                f"Max rewrites ({max_rewrites}) reached, generating answer from available context"
            )
            # Don't rewrite again, just proceed to answer
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
                "details": f"Question refined for better document matching",
            }
        )

        # Create a new message list with system prompt and rewritten question
        # This ensures the agent will search again with the improved question
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

    def _generate_answer(self, state: AgentState):
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

        # Find the original user question (first HumanMessage or user role message)
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

        # Build a simple, direct prompt for answer generation
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
            [{"role": "user", "content": prompt}], config={"callbacks": [self.langfuse_tracer]}
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

    def _grade_documents(self, state: AgentState):
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
        )  # Limit context to avoid token limits

        try:
            response = self.grader_model.with_structured_output(GradeDocument).invoke(
                [{"role": "user", "content": prompt}], config={"callbacks": [self.langfuse_tracer]}
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
        max_rewrites = state.get("max_rewrites", 1)  # Default to 1 rewrite max

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

