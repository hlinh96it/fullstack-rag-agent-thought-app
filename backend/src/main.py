import os
from contextlib import asynccontextmanager

# Suppress gRPC fork warnings
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "0")
os.environ.setdefault("GRPC_POLL_STRATEGY", "poll")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import Settings
from src.services.chat.factory import make_chat_client, make_agent_client
from src.services.database.factory import (
    make_mongo_database_client,
    make_aws_client,
    make_milvus_client,
    make_postgres_database_client,
)
from src.services.parser.factory import make_parser_service

from src.router.chat.user import user_router
from src.router.chat.chat import chat_router
from src.router.chat.ask import ask_router
from src.router.database.aws import s3_router
from src.router.database.mongodb import doc_router
from src.router.database.postgres import router as postgres_router


import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting RAG API...")

    settings = Settings()
    app.state.mongo_client = make_mongo_database_client(settings)
    app.state.postgres_client = make_postgres_database_client(settings)
    app.state.chat_client = make_chat_client(settings)
    app.state.aws_client = make_aws_client(settings)
    app.state.milvus_client = make_milvus_client(settings)
    app.state.parser_client = make_parser_service(settings)

    # Initialize agent with vector store configuration
    vector_stores = [
        {
            "store": app.state.milvus_client.vector_store,
            "name": "paper_retriever",
            "description": "Search and retrieve relevant information from academic papers and research documents",
            "k": 4,
            "ranker_weights": [0.6, 0.4],
        }
    ]
    app.state.agent_client = make_agent_client(settings, vector_stores)

    yield


app = FastAPI(title="FullStack Advanced RAG App with Thought", lifespan=lifespan)

origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix="/user")
app.include_router(chat_router, prefix="/chat")
app.include_router(ask_router, prefix="/ask")
app.include_router(s3_router, prefix="/s3")
app.include_router(doc_router, prefix="/doc")
app.include_router(postgres_router, prefix="/postgres")


@app.get("/health")
async def health_check():
    """Health check endpoint to verify all services are running."""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "agent": (
                "initialized"
                if hasattr(app.state, "agent_client")
                else "not initialized"
            ),
            "mongodb": (
                "connected" if hasattr(app.state, "mongo_client") else "not connected"
            ),
            "milvus": (
                "connected" if hasattr(app.state, "milvus_client") else "not connected"
            ),
            "aws": "connected" if hasattr(app.state, "aws_client") else "not connected",
        },
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "FullStack Advanced RAG App with Agentic Thought",
        "version": "2.0.0",
        "description": "An intelligent RAG system with agentic capabilities",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "agent_status": "/ask/status",
            "users": "/user",
            "chats": "/chat",
            "ask": "/ask",
            "documents": "/doc",
            "s3": "/s3",
            "postgres": "/postgres",
        },
    }
