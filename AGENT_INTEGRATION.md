# Agentic RAG Integration Guide

## Overview

The application has been updated to use an **Agentic RAG (Retrieval-Augmented Generation)** system instead of the previous simple LLM chat. This provides more intelligent document retrieval and question answering capabilities.

## What Changed

### Backend Changes

#### 1. **New AgenticRAG Class** (`backend/src/services/chat/agent.py`)
- Implements a graph-based agentic workflow using LangGraph
- Features:
  - **Query Generation**: Intelligently decides when to retrieve documents
  - **Document Retrieval**: Multiple vector store support with configurable retrievers
  - **Document Grading**: Assesses relevance of retrieved documents
  - **Question Rewriting**: Reformulates queries for better retrieval
  - **Answer Generation**: Produces final answers based on context

#### 2. **Updated Factory** (`backend/src/services/chat/factory.py`)
- Added `make_agent_client()` function to initialize the AgenticRAG
- Supports multiple vector stores configuration

#### 3. **Updated Dependencies** (`backend/src/dependencies.py`)
- Added `AgentDependency` for FastAPI dependency injection
- New `get_agent_client()` function

#### 4. **Updated Main App** (`backend/src/main.py`)
- Initializes agent with vector store configuration on startup
- Configured with Milvus vector store for paper retrieval

#### 5. **Updated Ask Router** (`backend/src/router/ask.py`)
- Now uses `AgentDependency` instead of `ChatDependency`
- Returns `AskResponse` model with structured output
- New `/ask/status` endpoint to check agent capabilities

#### 6. **Enhanced Schema** (`backend/src/schema/llm/models.py`)
- Added `chat_history` support to `AskRequest`
- Supports conversation context for better answers

#### 7. **Improved Prompts** (`backend/src/services/chat/prompts.py`)
- Updated system prompts to guide the agent's behavior
- Better instructions for tool usage and retrieval

### Frontend Changes

#### 1. **Updated Ask API** (`frontend/src/api/ask.js`)
- Supports sending chat history with requests
- Handles new response format (`{ answer: "..." }`)
- New `getAgentStatus()` function

#### 2. **Enhanced ChatBox** (`frontend/src/components/ChatBox.jsx`)
- Sends last 10 messages as chat history for context
- Better error handling and user feedback

## How It Works

### Agent Workflow

```
1. User Query
   ↓
2. Generate Query or Respond
   ↓
3. Route to Retriever Tool (or End if no retrieval needed)
   ↓
4. Retrieve Documents from Vector Store
   ↓
5. Grade Document Relevance
   ↓
6. If Relevant → Generate Answer → End
   If Not Relevant → Rewrite Question → Back to Step 2
```

### Vector Store Configuration

The agent is configured with a paper retriever tool:

```python
vector_stores = [
    {
        'store': milvus_client.vector_store,
        'name': 'paper_retriever',
        'description': 'Search and retrieve relevant information from academic papers',
        'k': 4,  # Number of documents to retrieve
        'ranker_weights': [0.6, 0.4]  # Dense and sparse retrieval weights
    }
]
```

## API Endpoints

### POST `/ask`
Ask a question to the agent.

**Request:**
```json
{
  "prompt": "What is retrieval-augmented generation?",
  "chat_history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
  ]
}
```

**Response:**
```json
{
  "answer": "Retrieval-augmented generation (RAG) is..."
}
```

### GET `/ask/status`
Get agent status and capabilities.

**Response:**
```json
{
  "status": "active",
  "model": "gpt-4",
  "available_tools": [
    {
      "name": "paper_retriever",
      "description": "Search and retrieve relevant information from academic papers",
      "k": 4
    }
  ],
  "system_prompt": "You are a helpful AI assistant..."
}
```

## Configuration

### Environment Variables

Make sure these are set in your `.env` file:

```bash
# OpenAI
OPENAI__OPENAI_API_KEY=your_key
OPENAI__MODEL_NAME=gpt-4
OPENAI__TEMPERATURE=0.7

# Milvus Vector DB
MILVUS__URI=your_milvus_uri
MILVUS__API_KEY=your_api_key
MILVUS__COLLECTION_NAME=your_collection
MILVUS__NAMESPACE=your_namespace

# Jina Embeddings
JINA__JINA_API_KEY=your_jina_key
JINA__MODEL_NAME=jina-embeddings-v3
```

## Benefits

1. **Intelligent Retrieval**: Only searches documents when needed
2. **Better Context**: Uses chat history for contextual understanding
3. **Self-Correcting**: Rewrites queries if documents aren't relevant
4. **Transparent**: Can see which tools are being used
5. **Extensible**: Easy to add more vector stores or tools

## Testing

1. **Start the backend:**
   ```bash
   cd backend
   uvicorn src.main:app --reload
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test the agent status:**
   ```bash
   curl http://localhost:8000/ask/status
   ```

4. **Ask a question:**
   ```bash
   curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"prompt": "What is machine learning?"}'
   ```

## Troubleshooting

### Agent not initializing
- Check that Milvus is connected and accessible
- Verify vector store collection exists
- Check logs for initialization errors

### No documents retrieved
- Ensure documents have been indexed in Milvus
- Check namespace configuration matches indexed documents
- Verify embedding model is working

### Slow responses
- Increase timeout settings in config
- Reduce number of retrieved documents (k parameter)
- Check vector store performance

## Next Steps

Potential enhancements:
- [ ] Add streaming responses for real-time feedback
- [ ] Support multiple vector stores (papers, code, etc.)
- [ ] Add citation tracking
- [ ] Implement response caching
- [ ] Add agent reasoning visibility in UI
- [ ] Support custom retrieval strategies
