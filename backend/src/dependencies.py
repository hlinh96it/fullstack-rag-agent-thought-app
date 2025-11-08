from typing import Annotated

from fastapi import Depends, Request
from src.services.chat.openai_client import OpenAIClient
from src.services.database.mongo_client import MongoDBClient
from src.services.database.aws_client import AWSClient
from src.services.database.milvus_client import MilvusVectorStoreClient
from src.services.parser.parser import ParserService


def get_chat_client(request: Request) -> OpenAIClient:
    return request.app.state.chat_client


def get_mongo_client(request: Request) -> MongoDBClient:
    return request.app.state.mongo_client


def get_aws_client(request: Request) -> AWSClient:
    return request.app.state.aws_client

def get_milvus_client(request: Request) -> MilvusVectorStoreClient:
    return request.app.state.milvus_client

def get_document_parser_service(request: Request) -> ParserService:
    return request.app.state.parser_client


ChatDependency = Annotated[OpenAIClient, Depends(get_chat_client)]
MongoDependency = Annotated[MongoDBClient, Depends(get_mongo_client)]
AWSDependency = Annotated[AWSClient, Depends(get_aws_client)]
ParserDependency = Annotated[ParserService, Depends(get_document_parser_service)]
MilvusDependency = Annotated[MilvusVectorStoreClient, Depends(get_milvus_client)]
