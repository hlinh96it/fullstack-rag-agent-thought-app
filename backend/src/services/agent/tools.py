from typing import List, Dict, Any, Optional

from langchain_milvus.vectorstores import Milvus
from langchain.tools.retriever import create_retriever_tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import START, END

from src.config import Settings
from src.schema.llm.models import AgentState

import time
import logging

logger = logging.getLogger(__name__)


class Tools:
    def __init__(
        self, settings: Settings, vector_stores: List[Dict[str, Any]]
    ):
        self.settings = settings
        self.vector_stores, self.retriever_tools = self.create_vector_store(
            vector_stores
        )

    def create_vector_store(self, vector_stores: List[Dict[str, Any]]):
        """Initialize vector stores and bind as llm tools"""

        initialized_stores = []
        retriever_tools = []
        required_keys = ["store", "name", "description"]

        for vs_config in vector_stores:

            # check required keys to create vs tools
            missing_keys = [key for key in required_keys if key not in vs_config]
            if missing_keys:
                raise ValueError(
                    f"Vector store configuration missing required key: {missing_keys}"
                )

            store: Milvus = vs_config["store"]
            name = vs_config["name"]
            description = vs_config["description"]
            k = vs_config.get("k", 2)
            ranker_type = vs_config.get("ranker_type", "weighted")
            ranker_weights = vs_config.get("ranker_weights", [0.6, 0.4])

            # IMPORTANT: Use namespace filtering to only retrieve user's documents
            # Apply namespace filter if provided in settings
            # Increase k to get more candidates for better relevance
            effective_k = max(k, 5)  # At least 5 documents for better coverage
            search_kwargs = {"k": effective_k}
            if self.settings.milvus.namespace:
                search_kwargs["expr"] = (
                    f'namespace == "{self.settings.milvus.namespace}"'
                )
                logger.info(
                    f"Configured retriever with namespace filter: {self.settings.milvus.namespace}"
                )

            # Create retriever with proper search configuration
            retriever = store.as_retriever(
                search_type="similarity", search_kwargs=search_kwargs
            )

            logger.info(
                f"Created retriever '{name}' with k={effective_k}, namespace={self.settings.milvus.namespace}"
            )

            retriever_tool = create_retriever_tool(
                retriever=retriever, name=name, description=description
            )
            initialized_stores.append(
                {
                    "store": store,
                    "name": name,
                    "description": description,
                    "retriever": retriever,
                    "tool": retriever_tool,
                    "k": k,
                    "ranker_type": ranker_type,
                    "ranker_weights": ranker_weights,
                }
            )
            retriever_tools.append(retriever_tool)

        return initialized_stores, retriever_tools

    def create_safe_tool_wrapper(self, tool_node: ToolNode, tool_name: str):
        """Create a wrapper around ToolNode to catch and handle errors gracefully."""

        def safe_tool_execution(state: AgentState):
            try:
                processing_steps = state.get("processing_steps", [])
                retrieved_documents = state.get("retrieved_documents", [])

                # Add step: Starting retrieval
                processing_steps.append(
                    {
                        "step_name": "search_documents",
                        "status": "in_progress",
                        "timestamp": time.time(),
                        "details": f"Searching {tool_name} for relevant documents",
                    }
                )

                logger.info(f"🔧 Executing retrieval tool: {tool_name}")
                logger.info(
                    f"📥 Tool input state has {len(state.get('messages', []))} messages"
                )

                result = tool_node.invoke(state)

                # Log retrieval results and extract documents
                if "messages" in result and result["messages"]:
                    last_msg = result["messages"][-1]
                    content = (
                        last_msg.content
                        if hasattr(last_msg, "content")
                        else str(last_msg)
                    )
                    logger.info(
                        f"✅ Tool {tool_name} retrieved {len(content)} characters"
                    )
                    logger.info(f"📄 Sample content: {content[:200]}...")

                    # Parse and store retrieved documents
                    # The content is usually formatted as concatenated document text
                    doc_chunks = content.split(
                        "\n\n"
                    )  # Simple split, adjust based on actual format
                    for idx, chunk in enumerate(
                        doc_chunks[:5]
                    ):  # Store up to 5 documents
                        if chunk.strip():
                            retrieved_documents.append(
                                {
                                    "content": chunk.strip(),
                                    "source": tool_name,
                                    "score": None,  # Score not available from basic retriever
                                }
                            )

                    # Update step: Retrieval completed
                    processing_steps.append(
                        {
                            "step_name": "search_documents",
                            "status": "completed",
                            "timestamp": time.time(),
                            "details": f"Found {len(doc_chunks)} relevant passages from {tool_name}",
                        }
                    )
                else:
                    logger.warning(f"⚠️  Tool {tool_name} returned no messages")
                    processing_steps.append(
                        {
                            "step_name": "search_documents",
                            "status": "completed",
                            "timestamp": time.time(),
                            "details": f"No documents found in {tool_name}",
                        }
                    )

                logger.info(f"✅ Tool {tool_name} executed successfully")

                # Add tracking info to result
                result["processing_steps"] = processing_steps
                result["retrieved_documents"] = retrieved_documents

                return result
            except Exception as e:
                logger.error(
                    f"❌ Tool {tool_name} execution failed: {str(e)}", exc_info=True
                )
                error_msg = f"Failed to retrieve documents using {tool_name}: {str(e)}"
                raise RuntimeError(error_msg) from e

        return safe_tool_execution

    def route_tools(self, state: AgentState):
        """
        Route the agent's tool calls to the appropriate vector store or end the conversation.
        This method examines the last message in the state to determine which tool should be
        invoked next based on the AI's tool call request.

        Args:
            state (AgentState): The current state containing the conversation messages.
                Must include a 'messages' key with a list of message objects.
        Returns:
            str: Either the name of the tool (vector store) to route to, or END constant
                to terminate the conversation flow.
        Raises:
            ValueError: If no messages are found in the input state.

        Notes:
            - Checks if the last message is an AIMessage with tool calls
            - Validates that the requested tool name exists in the configured vector stores
            - Logs a warning and returns END if an unknown tool is requested
            - Returns END if the last message doesn't contain tool calls
        """
        messages = state.get("messages", [])
        if not messages:
            logger.error(f"❌ No messages found in state: {state}")
            raise ValueError(
                f"No messages found in the input state to tool_edge: {state}"
            )

        ai_message = messages[-1]
        logger.info(f"🔀 Routing decision - Last message type: {type(ai_message)}")

        if (
            isinstance(ai_message, AIMessage)
            and hasattr(ai_message, "tool_calls")
            and len(ai_message.tool_calls) > 0
        ):

            tool_call = ai_message.tool_calls[0]
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})

            logger.info(f"🔧 Tool call requested: {tool_name}")
            logger.info(f"📊 Tool arguments: {tool_args}")

            valid_tool_names = [vs["name"] for vs in self.vector_stores]
            logger.info(f"✅ Available tools: {valid_tool_names}")

            if tool_name in valid_tool_names:
                logger.info(f"➡️  Routing to retrieval tool: {tool_name}")
                return tool_name
            else:
                logger.warning(
                    f"⚠️  Unknown tool name: {tool_name}. Available tools: {valid_tool_names}"
                )
                return END

        # If no tool calls and we haven't searched yet, this is a problem
        search_count = state.get("search_count", 0)
        if search_count == 0:
            logger.error(
                "❌ Agent attempted to respond without using any retrieval tools on first attempt!"
            )
            # Force re-generation with stronger prompt
            return END

        logger.info("🏁 No tool calls in message, ending conversation")
        return END
