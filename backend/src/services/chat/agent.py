from typing import Optional, List, Dict, Any, TypedDict, Annotated, Hashable

from langchain_milvus import Milvus
from langchain.tools.retriever import create_retriever_tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document

from langgraph.graph.state import StateGraph, START, END, CompiledStateGraph
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode

from src.config import Settings
from src.schema.llm.models import GradeDocument, AskRequest, AskResponse, ProcessingStep, RetrievedDocument
from .openai_client import OpenAIClient

import logging
import time

logger = logging.getLogger(__name__)


class AgentState(MessagesState):
    """Extended state to track search attempts and ensure proper retrieval."""
    search_count: int
    max_searches: int
    rewrite_count: int
    max_rewrites: int
    processing_steps: List[Dict[str, Any]]
    retrieved_documents: List[Dict[str, Any]]


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

        self.vector_stores, self.retriever_tools = self._init_vector_store(vector_stores)
        self.response_model = OpenAIClient(settings=settings, tools=self.retriever_tools)
        self.grader_model = OpenAIClient(settings=settings, temperature=0.0)
        self.graph = self._build_graph()
        
        logger.info(
            f'👌  AgenticRAG initilized with model: {self.settings.openai.model_name}'
            )

    def _init_vector_store(self, vector_stores: List[Dict[str, Any]]):
        """Initialize vector stores and bind as llm tools"""

        initialized_stores = []
        retriever_tools = []
        required_keys = ['store', 'name', 'description']

        for vs_config in vector_stores:

            # check required keys to create vs tools
            missing_keys = [
                key for key in required_keys if key not in vs_config]
            if missing_keys:
                raise ValueError(
                    f'Vector store configuration missing required key: {missing_keys}')

            store: Milvus = vs_config['store']
            name = vs_config['name']
            description = vs_config['description']
            k = vs_config.get('k', 2)
            ranker_type = vs_config.get('ranker_type', 'weighted')
            ranker_weights = vs_config.get('ranker_weights', [0.6, 0.4])

            # IMPORTANT: Use namespace filtering to only retrieve user's documents
            # Apply namespace filter if provided in settings
            # Increase k to get more candidates for better relevance
            effective_k = max(k, 5)  # At least 5 documents for better coverage
            search_kwargs = {'k': effective_k}
            if self.settings.milvus.namespace:
                search_kwargs['expr'] = f'namespace == "{self.settings.milvus.namespace}"'
                logger.info(f"Configured retriever with namespace filter: {self.settings.milvus.namespace}")
            
            # Create retriever with proper search configuration
            retriever = store.as_retriever(
                search_type='similarity',
                search_kwargs=search_kwargs
            )
            
            logger.info(f"Created retriever '{name}' with k={effective_k}, namespace={self.settings.milvus.namespace}")
            
            retriever_tool = create_retriever_tool(
                retriever=retriever, name=name, description=description
            )
            initialized_stores.append({
                'store': store, 'name': name, 'description': description,
                'retriever': retriever, 'tool': retriever_tool,
                'k': k, 'ranker_type': ranker_type, 'ranker_weights': ranker_weights
            })
            retriever_tools.append(retriever_tool)

        return initialized_stores, retriever_tools
    
    def _create_safe_tool_wrapper(self, tool_node: ToolNode, tool_name: str):
        """Create a wrapper around ToolNode to catch and handle errors gracefully."""
        def safe_tool_execution(state: MessagesState):
            try:
                processing_steps = state.get('processing_steps', [])
                retrieved_documents = state.get('retrieved_documents', [])
                
                # Add step: Starting retrieval
                processing_steps.append({
                    'step_name': 'search_documents',
                    'status': 'in_progress',
                    'timestamp': time.time(),
                    'details': f'Searching {tool_name} for relevant documents'
                })
                
                logger.info(f"🔧 Executing retrieval tool: {tool_name}")
                logger.info(f"📥 Tool input state has {len(state.get('messages', []))} messages")
                
                result = tool_node.invoke(state)
                
                # Log retrieval results and extract documents
                if 'messages' in result and result['messages']:
                    last_msg = result['messages'][-1]
                    content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
                    logger.info(f"✅ Tool {tool_name} retrieved {len(content)} characters")
                    logger.info(f"📄 Sample content: {content[:200]}...")
                    
                    # Parse and store retrieved documents
                    # The content is usually formatted as concatenated document text
                    doc_chunks = content.split('\n\n')  # Simple split, adjust based on actual format
                    for idx, chunk in enumerate(doc_chunks[:5]):  # Store up to 5 documents
                        if chunk.strip():
                            retrieved_documents.append({
                                'content': chunk.strip(),
                                'source': tool_name,
                                'score': None  # Score not available from basic retriever
                            })
                    
                    # Update step: Retrieval completed
                    processing_steps.append({
                        'step_name': 'search_documents',
                        'status': 'completed',
                        'timestamp': time.time(),
                        'details': f'Found {len(doc_chunks)} relevant passages from {tool_name}'
                    })
                else:
                    logger.warning(f"⚠️  Tool {tool_name} returned no messages")
                    processing_steps.append({
                        'step_name': 'search_documents',
                        'status': 'completed',
                        'timestamp': time.time(),
                        'details': f'No documents found in {tool_name}'
                    })
                
                logger.info(f"✅ Tool {tool_name} executed successfully")
                
                # Add tracking info to result
                result['processing_steps'] = processing_steps
                result['retrieved_documents'] = retrieved_documents
                
                return result
            except Exception as e:
                logger.error(f"❌ Tool {tool_name} execution failed: {str(e)}", exc_info=True)
                error_msg = f"Failed to retrieve documents using {tool_name}: {str(e)}"
                raise RuntimeError(error_msg) from e
        return safe_tool_execution
    
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
        workflow.add_node(node='generate_query_or_respond', action=self._generate_query_or_response)

        retriever_node_names = []
        for vs_config in self.vector_stores:
            node_name = vs_config['name']
            retriever_node_names.append(node_name)
            # Wrap ToolNode in error handler
            tool_node = ToolNode(tools=[vs_config['tool']])
            workflow.add_node(
                node=node_name, 
                action=self._create_safe_tool_wrapper(tool_node, node_name)
            )

        workflow.add_node(node='rewrite_question', action=self._rewrite_question)
        workflow.add_node(node='generate_answer', action=self._generate_answer)

        workflow.add_edge(start_key=START, end_key='generate_query_or_respond')

        tools_mapping = {}
        for vs_config in self.vector_stores:
            tool_name = vs_config['name']
            tools_mapping[tool_name] = tool_name 
        tools_mapping[END] = END
        workflow.add_conditional_edges(
            source='generate_query_or_respond', path=self._route_tools, path_map=tools_mapping)
        
        # Add conditional edges from retriever nodes to either generate_answer or rewrite_question
        grading_path_map: Dict[Hashable, str] = {
            'generate_answer': 'generate_answer',
            'rewrite_question': 'rewrite_question'
        }
        for node_name in retriever_node_names:
            workflow.add_conditional_edges(
                source=node_name, 
                path=self._grade_documents,
                path_map=grading_path_map
            )
        
        workflow.add_edge('generate_answer', end_key=END)
        workflow.add_edge('rewrite_question', end_key='generate_query_or_respond')
        
        graph = workflow.compile()
        
        # Save graph visualization
        try:
            graph.get_graph().draw_mermaid_png(output_file_path='assets/agent_graph.png')
            logger.info("✅ Agent graph visualization saved to assets/agent_graph.png")
        except Exception as e:
            logger.warning(f"Could not save graph visualization: {e}")
        
        return graph

    def _generate_query_or_response(self, state: AgentState):
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
            search_count = state.get('search_count', 0)
            max_searches = state.get('max_searches', 3)
            processing_steps = state.get('processing_steps', [])
            
            # Add step: Analyzing question
            processing_steps.append({
                'step_name': 'analyze_question',
                'status': 'completed',
                'timestamp': time.time(),
                'details': 'Analyzing your question and determining search strategy'
            })
            
            # Check if we've exceeded max searches
            if search_count >= max_searches:
                logger.warning(f"Max searches ({max_searches}) reached, forcing answer generation")
                processing_steps.append({
                    'step_name': 'max_searches_reached',
                    'status': 'completed',
                    'timestamp': time.time(),
                    'details': f'Maximum search attempts ({max_searches}) reached'
                })
                # Force direct answer if max searches exceeded
                return {
                    'messages': [AIMessage(content="I've searched multiple times but couldn't find highly relevant information. Please try rephrasing your question or ask something else.")],
                    'search_count': search_count,
                    'processing_steps': processing_steps
                }
            
            # Increment search count
            new_search_count = search_count + 1
            logger.info(f"🔍 Search attempt {new_search_count}/{max_searches}")
            logger.info(f"📝 Current conversation has {len(state['messages'])} messages")
            
            response = self.response_model.openai_client.invoke(state['messages'])
            logger.info(f"🤖 Generated response type: {type(response)}")
            logger.info(f"✅ Response with tool calls: {isinstance(response, AIMessage) and hasattr(response, 'tool_calls') and len(response.tool_calls) > 0}")
            
            # Check if the response contains tool calls
            if isinstance(response, AIMessage) and hasattr(response, 'tool_calls') and response.tool_calls:
                tool_names = [tc.get('name') for tc in response.tool_calls]
                tool_args = [tc.get('args') for tc in response.tool_calls]
                logger.info(f"🔧 Tool calls found: {tool_names}")
                logger.info(f"📊 Tool arguments: {tool_args}")
                
                # Add step: Preparing search
                processing_steps.append({
                    'step_name': 'prepare_search',
                    'status': 'completed',
                    'timestamp': time.time(),
                    'details': f'Preparing to search using: {", ".join(tool_names)}'
                })
            else:
                logger.warning("⚠️  No tool calls in response - agent may be trying to answer without searching")
            
            return {
                'messages': [response],
                'search_count': new_search_count,
                'processing_steps': processing_steps
            }
        except Exception as e:
            logger.error(f"❌ Failed to generate query/response: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to generate response: {str(e)}") from e
    
    def _route_tools(self, state: AgentState):
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
        messages = state.get('messages', [])
        if not messages:
            logger.error(f'❌ No messages found in state: {state}')
            raise ValueError(f'No messages found in the input state to tool_edge: {state}')
        
        ai_message = messages[-1]
        logger.info(f"🔀 Routing decision - Last message type: {type(ai_message)}")
        
        if isinstance(ai_message, AIMessage) and hasattr(ai_message, 'tool_calls') \
            and len(ai_message.tool_calls) > 0:
            
            tool_call = ai_message.tool_calls[0]
            tool_name = tool_call.get('name', '')
            tool_args = tool_call.get('args', {})
            
            logger.info(f"🔧 Tool call requested: {tool_name}")
            logger.info(f"📊 Tool arguments: {tool_args}")
            
            valid_tool_names = [vs['name'] for vs in self.vector_stores]
            logger.info(f"✅ Available tools: {valid_tool_names}")
            
            if tool_name in valid_tool_names:
                logger.info(f"➡️  Routing to retrieval tool: {tool_name}")
                return tool_name
            else:
                logger.warning(f'⚠️  Unknown tool name: {tool_name}. Available tools: {valid_tool_names}')
                return END
        
        # If no tool calls and we haven't searched yet, this is a problem
        search_count = state.get('search_count', 0)
        if search_count == 0:
            logger.error("❌ Agent attempted to respond without using any retrieval tools on first attempt!")
            # Force re-generation with stronger prompt
            return END
        
        logger.info("🏁 No tool calls in message, ending conversation")
        return END
    
    def _rewrite_question(self, state: AgentState) -> Dict:
        """Rewrite the question to improve retrieval, maintaining core intent."""
        processing_steps = state.get('processing_steps', [])
        
        last_human_message = HumanMessage(content='')
        for message in reversed(state['messages']):
            if isinstance(message, HumanMessage):
                last_human_message.content = message.content
                break
        
        question = last_human_message.content
        
        # Track rewrite attempts
        rewrite_count = state.get('rewrite_count', 0)
        max_rewrites = state.get('max_rewrites', 1)  # Default to 1 rewrite max
        
        if rewrite_count >= max_rewrites:
            logger.warning(f"Max rewrites ({max_rewrites}) reached, generating answer from available context")
            # Don't rewrite again, just proceed to answer
            return {
                'messages': state['messages'],
                'rewrite_count': rewrite_count,
                'processing_steps': processing_steps
            }
        
        new_rewrite_count = rewrite_count + 1
        logger.info(f"Rewriting question (attempt {new_rewrite_count}/{max_rewrites})")
        
        # Add step: Rewriting question
        processing_steps.append({
            'step_name': 'rewrite_question',
            'status': 'in_progress',
            'timestamp': time.time(),
            'details': f'Refining question for better retrieval (attempt {new_rewrite_count}/{max_rewrites})'
        })
        
        # Improved rewrite prompt that maintains semantic core
        rewrite_prompt = (
            "Analyze the following question and rephrase it to make it clearer and more specific "
            "for document retrieval, while maintaining the core intent.\n\n"
            "Original question: {question}\n\n"
            "Guidelines for rewriting:\n"
            "- Keep the main topic and intent unchanged\n"
            "- Add synonyms or related terms that might appear in documents\n"
            "- Make it more general if it's too specific, or add context if it's too vague\n"
            "- Use common terminology that would appear in formal documents\n"
            "- Keep it concise (1-2 sentences maximum)\n\n"
            "Rewritten question:"
        )
        
        prompt = rewrite_prompt.format(question=question)
        response = self.response_model.openai_client.invoke(input=[{'role': 'user', 'content': prompt}])
        logger.info(f"Original question: {question}")
        logger.info(f"Rewritten question: {response.content}")

        # Complete the step
        processing_steps.append({
            'step_name': 'rewrite_question',
            'status': 'completed',
            'timestamp': time.time(),
            'details': f'Question refined for better document matching'
        })

        # Create a new message list with system prompt and rewritten question
        # This ensures the agent will search again with the improved question
        new_messages = [
            {"role": "system", "content": self.response_model.system_prompt},
            {"role": "user", "content": response.content}
        ]
        
        return {
            "messages": new_messages,
            "rewrite_count": new_rewrite_count,
            "search_count": 0,  # Reset search count for the rewritten question
            "processing_steps": processing_steps
        }

    def _generate_answer(self, state: MessagesState):
        """Generate a direct answer based on retrieved context."""
        processing_steps = state.get('processing_steps', [])
        
        # Add step: Generating answer
        processing_steps.append({
            'step_name': 'generate_answer',
            'status': 'in_progress',
            'timestamp': time.time(),
            'details': 'Generating comprehensive answer from retrieved context'
        })
        
        # Find the original user question (first HumanMessage or user role message)
        question = None
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                question = msg.content
                break
            elif isinstance(msg, dict) and msg.get('role') == 'user':
                question = msg.get('content', '')
                break
        
        if not question:
            question = state["messages"][0].content if state["messages"] else "Unknown question"
        
        # Get the retrieved context from the last ToolMessage
        last_message = state["messages"][-1]
        context = last_message.content if hasattr(last_message, 'content') else str(last_message)
        
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
        response = self.grader_model.openai_client.invoke([{"role": "user", "content": prompt}])
        
        logger.info(f"✅ Generated answer: {response.content[:200]}...")
        
        # Complete the step
        processing_steps.append({
            'step_name': 'generate_answer',
            'status': 'completed',
            'timestamp': time.time(),
            'details': 'Answer generated successfully'
        })
        
        return {
            "messages": [response],
            "processing_steps": processing_steps
        }

    def _grade_documents(self, state: AgentState):
        """
        Determine whether the retrieved documents are relevant to the question.
        Uses a more lenient grading strategy to avoid false negatives.
        """
        processing_steps = state.get('processing_steps', [])
        
        # Add step: Grading documents
        processing_steps.append({
            'step_name': 'grade_documents',
            'status': 'in_progress',
            'timestamp': time.time(),
            'details': 'Evaluating relevance of retrieved documents'
        })
        
        question = state['messages'][0].content
        last_message = state['messages'][-1]
        
        # Extract actual document content from tool message
        if hasattr(last_message, 'content'):
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
            logger.warning(f"⚠️  Very short context ({context_length} chars), likely no documents found")
            processing_steps.append({
                'step_name': 'grade_documents',
                'status': 'completed',
                'timestamp': time.time(),
                'details': 'No relevant documents found'
            })
            
            # Short context means retrieval likely failed
            rewrite_count = state.get('rewrite_count', 0)
            max_rewrites = state.get('max_rewrites', 2)
            
            if rewrite_count >= max_rewrites:
                logger.info("⚠️  No documents found and max rewrites reached, generating answer anyway")
                return 'generate_answer'
            else:
                logger.info(f"🔄 No documents found, rewriting question (attempt {rewrite_count + 1}/{max_rewrites})")
                return 'rewrite_question'
        
        # Use more lenient grading prompt
        grade_prompt = (
            "You are a grader assessing relevance of retrieved documents to a user question. \n"
            "Here is the retrieved content: \n\n {context} \n\n"
            "Here is the user question: {question} \n\n"
            "Grade as 'yes' if ANY of the following are true:\n"
            "- The content contains keywords related to the question\n"
            "- The content discusses topics related to the question's domain\n"
            "- The content provides context that could help answer the question\n"
            "- The content is from a similar subject area as the question\n\n"
            "Only grade as 'no' if the content is completely unrelated or off-topic.\n"
            "Be lenient - partial relevance is acceptable.\n"
            "Respond with 'yes' or 'no'."
        )
        prompt = grade_prompt.format(question=question, context=context[:2000])  # Limit context to avoid token limits
        
        try:
            response = self.grader_model.with_structured_output(
                GradeDocument
            ).invoke([{'role': 'user', 'content': prompt}])
            
            # Grade the document and route accordingly
            binary_score = response.binary_score if isinstance(response, GradeDocument) else response.get('binary_score', 'no')
        except Exception as e:
            logger.error(f"❌ Grading failed: {str(e)}, defaulting to 'yes' to avoid blocking")
            # If grading fails, be optimistic and proceed
            binary_score = 'yes'
        
        rewrite_count = state.get('rewrite_count', 0)
        max_rewrites = state.get('max_rewrites', 1)  # Default to 1 rewrite max
        
        logger.info(f"📝 Document relevance score: {binary_score}")
        logger.info(f"🔄 Rewrite count: {rewrite_count}/{max_rewrites}")
        
        if binary_score.lower() == 'yes':
            logger.info("✅ Document is relevant, proceeding to generate answer")
            processing_steps.append({
                'step_name': 'grade_documents',
                'status': 'completed',
                'timestamp': time.time(),
                'details': 'Documents are relevant to your question'
            })
            return 'generate_answer'
        else:
            if rewrite_count >= max_rewrites:
                logger.info(f"⚠️  Document not highly relevant but max rewrites ({max_rewrites}) reached, generating answer anyway")
                processing_steps.append({
                    'step_name': 'grade_documents',
                    'status': 'completed',
                    'timestamp': time.time(),
                    'details': 'Using available documents despite lower relevance'
                })
                return 'generate_answer'
            else:
                logger.info(f"🔄 Document is not relevant, rewriting question (attempt {rewrite_count + 1}/{max_rewrites})")
                processing_steps.append({
                    'step_name': 'grade_documents',
                    'status': 'completed',
                    'timestamp': time.time(),
                    'details': 'Documents not highly relevant, refining search'
                })
                return 'rewrite_question'

    def run(self, query: AskRequest) -> AskResponse:
        # Build conversation with chat history if available
        conversation = [
            {"role": "system", "content": self.response_model.system_prompt}
        ]
        
        # Add chat history if provided
        if query.chat_history:
            logger.info(f"Including {len(query.chat_history)} messages from chat history")
            for msg in query.chat_history:
                conversation.append({"role": msg.role, "content": msg.content})
        
        # Add current user query
        conversation.append({"role": "user", "content": query.prompt})
        
        logger.info(f"Processing query: {query.prompt[:100]}...")
        
        try:
            # Initialize state with counters and tracking
            initial_state = {
                'messages': conversation,
                'search_count': 0,
                'max_searches': 3,
                'rewrite_count': 0,
                'max_rewrites': 1,  # Reduced from 2 to 1 to avoid excessive rewriting
                'processing_steps': [],
                'retrieved_documents': []
            }
            
            response = self.graph.invoke(initial_state)
            logger.info(f"Raw agent response: {response}")
            
            if not response or 'messages' not in response or not response['messages']:
                logger.error("Agent returned empty response")
                raise RuntimeError("Agent returned empty response")
            
            logger.info(f"Response messages count: {len(response['messages'])}")
            logger.info(f"Last message type: {type(response['messages'][-1])}")
            logger.info(f"Search count: {response.get('search_count', 'N/A')}, Rewrite count: {response.get('rewrite_count', 'N/A')}")
            
            last_message = response['messages'][-1]
            # Handle both AIMessage objects and dict messages
            if hasattr(last_message, 'content'):
                answer = last_message.content
            elif isinstance(last_message, dict):
                answer = last_message.get('content', '')
            else:
                logger.error(f"Unexpected message type: {type(last_message)}")
                raise RuntimeError(f"Unexpected message type: {type(last_message)}")
            
            if not answer or not answer.strip():
                logger.error("Agent generated empty answer")
                raise RuntimeError("Agent generated empty answer")
            
            # Extract processing steps and retrieved documents from response
            processing_steps_data = response.get('processing_steps', [])
            retrieved_docs_data = response.get('retrieved_documents', [])
            
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
                search_count=response.get('search_count', 0),
                rewrite_count=response.get('rewrite_count', 0)
            )
            
        except TimeoutError as e:
            logger.error(f"Agent timed out: {str(e)}", exc_info=True)
            raise RuntimeError("Request timed out. Please try again with a simpler question.") from e
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
                raise RuntimeError(f"Agent failed to process query: {error_message}") from e
        