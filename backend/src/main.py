import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import Settings
from src.services.chat.factory import make_chat_client
from src.services.database.factory import make_database_client, make_aws_client

from src.router.user import user_router
from src.router.chat import chat_router
from src.router.ask import ask_router
from src.router.aws import s3_router
from src.router.document import doc_router


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
    app.state.mongo_client = make_database_client(settings)  
    app.state.chat_client = make_chat_client(settings, client_type="openai")
    app.state.aws_client = make_aws_client(settings)

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
app.include_router(s3_router, prefix='/s3')
app.include_router(doc_router, prefix='/doc')

