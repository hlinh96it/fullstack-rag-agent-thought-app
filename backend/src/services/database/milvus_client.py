from typing import List, Dict, Any, Optional
from httpx import HTTPError

from pydantic import SecretStr
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_milvus import Milvus, BM25BuiltInFunction
from langchain_community.embeddings import JinaEmbeddings

from src.config import Settings

import logging

logger = logging.getLogger(__name__)


class MilvusClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.vector_store = self._init_vector_store()
        logger.info("👌  Create Milvus Vector Store successfully!")

    def _init_vector_store(self) -> Milvus:
        jina_embedding_function = JinaEmbeddings(
            jina_api_key=SecretStr(self.settings.jina.jina_api_key),
            model_name=self.settings.jina.model_name,
            session=None,
        )
        logger.info(f'👌  Jina Embedding initialized!')
        connection_args = {
            "uri": self.settings.milvus.uri, "token": self.settings.milvus.api_key,
        }
        
        try:
            # Create Milvus vector store - will auto-create collection if it doesn't exist
            vector_store = Milvus(
                collection_name=self.settings.milvus.collection_name,
                collection_description="Parsed paper vector store",
                connection_args=connection_args,
                embedding_function=jina_embedding_function,
                consistency_level="Strong",
                vector_field="dense", 
                text_field="text",
                builtin_function=BM25BuiltInFunction(),
                drop_old=False,  # Don't drop existing collection
                auto_id=True
            )
            
            # Log collection info
            try:
                col_name = self.settings.milvus.collection_name
                logger.info(f"✅ Connected to Milvus collection '{col_name}'")
            except Exception as log_error:
                logger.debug(f"Could not log collection info: {log_error}")
            
            return vector_store
            
        except Exception as e:
            logger.error(f"Failed to create/connect to Milvus Vector Store: {e}")
            raise HTTPError(
                message=f"Failed to create Milvus Vector Store: {e}")

    def as_retriever(self, k: int = 4, ranker_type: str = 'weighted',
                     ranker_weights: Optional[List[float]] = [0.6, 0.4]) -> BaseRetriever:
        search_kwargs = {'k': k, 'expr': f'namespace == "{self.settings.milvus.namespace}"'}
        return self.vector_store.as_retriever(
            search_kwargs=search_kwargs, ranker_type=ranker_type,
            ranker_params={'weights': ranker_weights}   
        )
    
    async def index_document(self, chunks: List[Document]) -> List[str]:
        try:
            response = self.vector_store.add_documents(chunks)
            logger.info(f'👌  Successfully added {len(response)} documents')
            return response
        except Exception as e:
            raise HTTPError(message=f'Failed to add documents: {e}')
        
    
