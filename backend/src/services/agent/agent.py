import os
from typing import List, Dict, Any, Hashable

from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph
from langgraph.graph.state import START, END, CompiledStateGraph
from langgraph.prebuilt import ToolNode

from src.config import Settings
from src.services.chat.openai_client import OpenAIClient
from src.schema.llm.models import AgentState, AskRequest, AskResponse, ProcessingStep, RetrievedDocument

from .tools import Tools
from .nodes import Nodes

import logging

logger = logging.getLogger(__name__)


class AgenticRAG:
    """
    This class implements an agentic RAG system that uses a graph-based approach to:
    1. Generate a query or respond directly
    2. Retrieve relevant documents from multiple vector stores
    3. Grade document relevance
    4. Rewrite the question if needed
    5. Generate a final answer
    """

    def __init__(self, settings: Settings, vector_stores: List[Dict[str, Any]]) -> None:
        self.settings = settings
        self.tools = Tools(settings=settings, vector_stores=vector_stores)

        self.response_model = OpenAIClient(
            settings=settings, tools=self.tools.retriever_tools
        )
        self.grader_model = OpenAIClient(settings=settings, temperature=0.0)

        # Initialize the callback handler (it will read from environment variables)
        if settings.langfuse.public_key:
            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse.public_key
        if settings.langfuse.secret_key:
            os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse.secret_key
        if settings.langfuse.base_url:
            os.environ["LANGFUSE_HOST"] = settings.langfuse.base_url

        self.langfuse_tracer = CallbackHandler()

        self.nodes = Nodes(
            settings, self.response_model, self.grader_model, self.langfuse_tracer
        )
        self.graph = self._build_graph()

        logger.info(
            f"👌  AgenticRAG initilized with model: {self.settings.openai.model_name}"
        )

    def _build_graph(self) -> CompiledStateGraph:
        """
        Build and compile a state graph workflow for the agentic RAG system.
        This method constructs a LangGraph workflow that orchestrates the interaction between
        query generation, document retrieval, grading, and answer generation nodes.

        Workflow Structure:
            1. START -> generate_query_or_respond: Entry point for processing user queries
            2. generate_query_or_respond -> [retriever nodes | END]: Routes to appropriate retriever or ends
            3. retriever nodes -> [rewrite_question | generate_answer]: Grades documents and routes accordingly
            4. rewrite_question -> generate_query_or_respond: Loops back to retry with rewritten query
            5. generate_answer -> END: Generates final answer and terminates
        Nodes:
            - generate_query_or_respond: Determines whether to query retrievers or respond directly
            - retriever nodes: One per vector store config, handles document retrieval
            - rewrite_question: Reformulates the question for better retrieval
            - generate_answer: Generates the final response based on retrieved documents

        Returns:
            CompiledStateGraph: A compiled LangGraph workflow ready for execution. The graph
                visualization is also saved to 'graph.png'.
        Side Effects:
            - Saves a Mermaid diagram visualization of the graph to 'graph.png'
        """

        workflow = StateGraph(state_schema=AgentState)
        workflow.add_node(
            node="generate_query_or_respond",
            action=self.nodes.generate_query_or_response,
        )

        retriever_node_names = []
        for vs_config in self.tools.vector_stores:
            node_name = vs_config["name"]
            retriever_node_names.append(node_name)

            # Wrap ToolNode in error handler
            tool_node = ToolNode(tools=[vs_config["tool"]])
            workflow.add_node(
                node=node_name,
                action=self.tools.create_safe_tool_wrapper(tool_node, node_name),
            )

        workflow.add_node(node="rewrite_question", action=self.nodes._rewrite_question)
        workflow.add_node(node="generate_answer", action=self.nodes._generate_answer)

        workflow.add_edge(start_key=START, end_key="generate_query_or_respond")

        tools_mapping = {}
        for vs_config in self.tools.vector_stores:
            tool_name = vs_config["name"]
            tools_mapping[tool_name] = tool_name
        tools_mapping[END] = END
        workflow.add_conditional_edges(
            source="generate_query_or_respond",
            path=self.tools.route_tools,
            path_map=tools_mapping,
        )

        # Add conditional edges from retriever nodes to either generate_answer or rewrite_question
        grading_path_map: Dict[Hashable, str] = {
            "generate_answer": "generate_answer",
            "rewrite_question": "rewrite_question",
        }
        for node_name in retriever_node_names:
            workflow.add_conditional_edges(
                source=node_name, path=self.nodes._grade_documents, path_map=grading_path_map
            )

        workflow.add_edge("generate_answer", end_key=END)
        workflow.add_edge("rewrite_question", end_key="generate_query_or_respond")

        graph = workflow.compile()

        # Save graph visualization
        try:
            graph.get_graph().draw_mermaid_png(
                output_file_path="assets/agent_graph.png"
            )
            logger.info("✅ Agent graph visualization saved to assets/agent_graph.png")
        except Exception as e:
            logger.warning(f"Could not save graph visualization: {e}")

        return graph

    def run(self, query: AskRequest) -> AskResponse:
        # Build conversation with chat history if available
        conversation = [
            {"role": "system", "content": self.response_model.system_prompt}
        ]

        # Add chat history if provided
        if query.chat_history:
            logger.info(
                f"Including {len(query.chat_history)} messages from chat history"
            )
            for msg in query.chat_history:
                conversation.append({"role": msg.role, "content": msg.content})

        # Add current user query
        conversation.append({"role": "user", "content": query.prompt})

        logger.info(f"Processing query: {query.prompt[:100]}...")

        try:
            # Initialize state with counters and tracking
            initial_state = {
                "messages": conversation,
                "search_count": 0,
                "max_searches": 3,
                "rewrite_count": 0,
                "max_rewrites": 1,  # Reduced from 2 to 1 to avoid excessive rewriting
                "processing_steps": [],
                "retrieved_documents": [],
            }

            response = self.graph.invoke(initial_state)
            logger.info(f"Raw agent response: {response}")

            if not response or "messages" not in response or not response["messages"]:
                logger.error("Agent returned empty response")
                raise RuntimeError("Agent returned empty response")

            logger.info(f"Response messages count: {len(response['messages'])}")
            logger.info(f"Last message type: {type(response['messages'][-1])}")
            logger.info(
                f"Search count: {response.get('search_count', 'N/A')}, Rewrite count: {response.get('rewrite_count', 'N/A')}"
            )

            last_message = response["messages"][-1]
            # Handle both AIMessage objects and dict messages
            if hasattr(last_message, "content"):
                answer = last_message.content
            elif isinstance(last_message, dict):
                answer = last_message.get("content", "")
            else:
                logger.error(f"Unexpected message type: {type(last_message)}")
                raise RuntimeError(f"Unexpected message type: {type(last_message)}")

            if not answer or not answer.strip():
                logger.error("Agent generated empty answer")
                raise RuntimeError("Agent generated empty answer")

            # Extract processing steps and retrieved documents from response
            processing_steps_data = response.get("processing_steps", [])
            retrieved_docs_data = response.get("retrieved_documents", [])

            # Convert to Pydantic models
            processing_steps = [
                ProcessingStep(**step) for step in processing_steps_data
            ]

            retrieved_documents = [
                RetrievedDocument(**doc) for doc in retrieved_docs_data
            ]

            logger.info(f"Generated answer: {answer[:100]}...")
            logger.info(f"Processing steps: {len(processing_steps)}")
            logger.info(f"Retrieved documents: {len(retrieved_documents)}")
            logger.info(f"Returning AskResponse with answer of length: {len(answer)}")

            return AskResponse(
                answer=answer,
                retrieved_documents=retrieved_documents,
                processing_steps=processing_steps,
                search_count=response.get("search_count", 0),
                rewrite_count=response.get("rewrite_count", 0),
            )

        except TimeoutError as e:
            logger.error(f"Agent timed out: {str(e)}", exc_info=True)
            raise RuntimeError(
                "Request timed out. Please try again with a simpler question."
            ) from e
        except ValueError as e:
            logger.error(f"Invalid input or configuration: {str(e)}", exc_info=True)
            raise RuntimeError(f"Invalid request: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to generate answer: {str(e)}", exc_info=True)
            error_message = str(e)
            if "tool" in error_message.lower():
                raise RuntimeError(f"Tool execution failed: {error_message}") from e
            elif "api" in error_message.lower() or "openai" in error_message.lower():
                raise RuntimeError(f"API error: {error_message}") from e
            else:
                raise RuntimeError(
                    f"Agent failed to process query: {error_message}"
                ) from e