#!/bin/bash
# Run script for the Agentic RAG backend

echo "🚀 Starting Agentic RAG Backend..."
echo ""

# Check if we're in the backend directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Must run from backend directory"
    echo "   Run: cd backend && ./run.sh"
    exit 1
fi

# Run setup check
echo "📋 Running setup verification..."
python check_setup.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Setup verification failed. Please fix the issues above."
    exit 1
fi

echo ""
echo "✅ Setup verification passed!"
echo ""
echo "🌐 Starting FastAPI server..."
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/health"
echo ""

# Start the server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
