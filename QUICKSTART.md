# Quick Start Guide - Agentic RAG App

## Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB running
- Milvus vector database running
- OpenAI API key
- Jina AI API key

## Setup Instructions

### 1. Backend Setup

```bash
cd backend

# Install dependencies using Poetry
poetry install

# Or using pip
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Configure Environment Variables

Edit `backend/.env`:

```bash
# OpenAI Configuration
OPENAI__OPENAI_API_KEY=sk-...
OPENAI__MODEL_NAME=gpt-4o-mini
OPENAI__TEMPERATURE=0.7
OPENAI__TIMEOUT=3000

# MongoDB Configuration
MONGO__MONGO_URI=mongodb://localhost:27017
MONGO__MONGO_DATABASE=rag_app
MONGO__MONGO_COLLECTION=users

# AWS S3 Configuration
AWS__ACCESS_KEY=your_access_key
AWS__SECRET_KEY=your_secret_key
AWS__REGION=us-east-1
AWS__BUCKET_NAME=your_bucket

# Milvus Configuration
MILVUS__URI=https://your-milvus-instance.com
MILVUS__API_KEY=your_milvus_key
MILVUS__COLLECTION_NAME=paper_embeddings
MILVUS__NAMESPACE=default

# Jina Embeddings
JINA__EMBEDDING_URL=https://api.jina.ai/v1/embeddings
JINA__JINA_API_KEY=your_jina_key
JINA__MODEL_NAME=jina-embeddings-v3
```

### 3. Test the Agent (Optional)

```bash
cd backend
python test_agent.py
```

This will test the agent without starting the full server.

### 4. Start the Backend

```bash
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

API Documentation: http://localhost:8000/docs

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at: http://localhost:5173

## Testing the Integration

### 1. Check Backend Health

```bash
# Check API is running
curl http://localhost:8000/ask/status

# Expected response:
{
  "status": "active",
  "model": "gpt-4o-mini",
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

### 2. Test Agent Query

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is retrieval-augmented generation?"
  }'

# Expected response:
{
  "answer": "Retrieval-augmented generation (RAG) is a technique..."
}
```

### 3. Test with Chat History

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Can you explain more?",
    "chat_history": [
      {"role": "user", "content": "What is RAG?"},
      {"role": "assistant", "content": "RAG is a technique..."}
    ]
  }'
```

### 4. Use the Frontend

1. Open http://localhost:5173 in your browser
2. Create a new user or login
3. Create a new chat
4. Ask questions!

## Features to Test

### Basic Queries
- "Hello, how are you?" (should respond without retrieval)
- "What is 2+2?" (simple questions)

### Document Retrieval Queries
- "What papers discuss transformer models?"
- "Explain attention mechanisms"
- "What are the latest advances in NLP?"

### Conversational Context
1. Ask: "What is machine learning?"
2. Follow up: "What are its applications?" (should use context)
3. Follow up: "Give me an example" (should maintain context)

## Troubleshooting

### Backend Issues

**Error: "Failed to connect to Milvus"**
- Check Milvus is running
- Verify MILVUS__URI and MILVUS__API_KEY
- Check network connectivity

**Error: "OpenAI API key invalid"**
- Verify OPENAI__OPENAI_API_KEY is correct
- Check API key has sufficient credits

**Error: "No documents found"**
- Ensure documents are indexed in Milvus
- Check MILVUS__NAMESPACE matches indexed documents
- Verify collection name is correct

### Frontend Issues

**Blank page or errors**
- Check browser console for errors
- Verify backend is running
- Check CORS settings in backend

**Messages not saving**
- Check MongoDB is running
- Verify database connection
- Check browser network tab for failed requests

### Agent Not Using Retrieval

If the agent is not retrieving documents:
1. Check vector store is properly initialized
2. Verify documents exist in the collection
3. Review agent logs for tool usage
4. Try more specific queries related to indexed content

## Architecture Overview

```
┌─────────────┐
│   Frontend  │
│   (React)   │
└──────┬──────┘
       │ HTTP
       ↓
┌─────────────────────────────────┐
│      FastAPI Backend            │
├─────────────────────────────────┤
│  ┌──────────────────────────┐  │
│  │   AgenticRAG (LangGraph)  │  │
│  │  ┌────────────────────┐  │  │
│  │  │ Query Generation   │  │  │
│  │  │ Document Retrieval │  │  │
│  │  │ Grading & Rewrite  │  │  │
│  │  │ Answer Generation  │  │  │
│  │  └────────────────────┘  │  │
│  └──────────────────────────┘  │
└─────┬───────────┬───────────┬──┘
      │           │           │
      ↓           ↓           ↓
┌──────────┐ ┌────────┐ ┌─────────┐
│ MongoDB  │ │ Milvus │ │ OpenAI  │
│ (Users)  │ │(Vectors)│ │  (LLM)  │
└──────────┘ └────────┘ └─────────┘
```

## Next Steps

1. Upload documents using the document management interface
2. Documents will be automatically parsed and indexed
3. Start asking questions about your documents!

For more details, see [AGENT_INTEGRATION.md](AGENT_INTEGRATION.md)
