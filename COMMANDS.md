# 🚀 Agentic RAG - Command Reference

## Quick Start Commands

### Backend

```bash
# Check setup and dependencies
cd backend
python check_setup.py

# Test the agent (without starting server)
python test_agent.py

# Start the backend server
./run.sh
# or
uvicorn src.main:app --reload

# Start with custom host/port
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### Frontend

```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Testing Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Agent Status
```bash
curl http://localhost:8000/ask/status
```

### Ask a Question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?"}'
```

### Ask with Chat History
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Can you explain more?",
    "chat_history": [
      {"role": "user", "content": "What is RAG?"},
      {"role": "assistant", "content": "RAG stands for..."}
    ]
  }'
```

## Development Commands

### Backend

```bash
# Install dependencies with Poetry
poetry install

# Activate virtual environment
poetry shell

# Run tests
pytest

# Format code
black src/
isort src/

# Type checking
mypy src/
```

### Frontend

```bash
# Install specific package
npm install package-name

# Update dependencies
npm update

# Check for outdated packages
npm outdated

# Lint code
npm run lint
```

## Environment Variables

### Required Variables

```bash
# OpenAI
OPENAI__OPENAI_API_KEY=sk-...
OPENAI__MODEL_NAME=gpt-4o-mini
OPENAI__TEMPERATURE=0.7

# MongoDB
MONGO__MONGO_URI=mongodb://localhost:27017
MONGO__MONGO_DATABASE=rag_app
MONGO__MONGO_COLLECTION=users

# Milvus
MILVUS__URI=https://your-instance.com
MILVUS__API_KEY=your-key
MILVUS__COLLECTION_NAME=papers
MILVUS__NAMESPACE=default

# Jina
JINA__JINA_API_KEY=your-key
JINA__MODEL_NAME=jina-embeddings-v3
```

## Troubleshooting

### Backend won't start
```bash
# Check setup
python check_setup.py

# Check logs
tail -f logs/app.log

# Verify Python version
python --version  # Should be 3.10+
```

### Import errors
```bash
# Reinstall dependencies
poetry install --no-cache

# or with pip
pip install -r requirements.txt --force-reinstall
```

### Database connection issues
```bash
# Check MongoDB
mongosh  # Should connect

# Check Milvus (in Python)
python -c "from pymilvus import connections; connections.connect(uri='YOUR_URI', token='YOUR_TOKEN')"
```

### gRPC warnings
Already suppressed in the code, but you can also set:
```bash
export GRPC_ENABLE_FORK_SUPPORT=0
export GRPC_POLL_STRATEGY=poll
```

## Useful URLs

- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Agent Status**: http://localhost:8000/ask/status
- **Frontend**: http://localhost:5173

## Project Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── dependencies.py      # FastAPI dependencies
│   ├── router/              # API route handlers
│   ├── services/
│   │   ├── chat/
│   │   │   ├── agent.py     # AgenticRAG implementation
│   │   │   ├── factory.py   # Client factories
│   │   │   └── prompts.py   # System prompts
│   │   ├── database/        # DB clients
│   │   ├── embedding/       # Embedding services
│   │   └── parser/          # Document parsers
│   └── schema/              # Pydantic models
├── check_setup.py           # Setup verification script
├── test_agent.py            # Agent testing script
└── run.sh                   # Startup script

frontend/
├── src/
│   ├── api/                 # API clients
│   ├── components/          # React components
│   ├── context/             # React context
│   └── hooks/               # Custom hooks
└── package.json             # Dependencies
```

## Quick Tips

1. **Always check setup first**: `python check_setup.py`
2. **Test agent before full server**: `python test_agent.py`
3. **Use the run script**: `./run.sh` (includes verification)
4. **Check logs in terminal** for debugging
5. **Use `/health` endpoint** to verify all services
6. **Use `/ask/status`** to see agent capabilities

## Getting Help

- Check `QUICKSTART.md` for detailed setup
- Check `AGENT_INTEGRATION.md` for architecture details
- Review logs in the terminal
- Check FastAPI docs at `/docs` endpoint
