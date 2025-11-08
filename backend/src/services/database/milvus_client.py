from typing import List, Dict, Any

from pymilvus import MilvusClient, DataType, Function, FunctionType
from pymilvus.model.dense import JinaEmbeddingFunction
from langchain_core.documents import Document

from src.config import Settings
from src.schema.embeddings.jina import JinaEmbeddingRequest

import logging

logger = logging.getLogger(__name__)


class MilvusVectorStoreClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = MilvusClient(
            uri=self.settings.milvus.uri, token=self.settings.milvus.api_key
        )
        self.collection_name = self.settings.milvus.collection_name

        # create embedding function
        self.jina_embedding_fn = JinaEmbeddingFunction(
            model_name=self.settings.jina.model_name,
            api_key=self.settings.jina.jina_api_key,
            task="retrieval.passage",
            dimensions=1024,
        )

        self._init_collection_and_vector_store()

    def _init_collection_and_vector_store(self):
        """Check if collection exists, create if not, otherwise load it and create vector store."""

        if self.client.has_collection(collection_name=self.collection_name):
            logger.info(
                f"Collection '{self.collection_name}' already exists. Loading collection."
            )
            # Collection exists, it's automatically loaded when using MilvusClient
        else:
            logger.info(
                f"Collection '{self.collection_name}' does not exist. Creating collection."
            )

            # add field for collection
            schema = self.client.create_schema()
            schema.add_field(
                "id", datatype=DataType.INT64, is_primary=True, auto_id=True
            )
            schema.add_field("document", datatype=DataType.VARCHAR, max_length=9000)
            schema.add_field("dense", datatype=DataType.FLOAT_VECTOR, dim=1024)

            # create index
            index_params = self.client.prepare_index_params(
                field_name="dense", index_type="AUTOINDEX", metric_type="COSINE"
            )

            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                index_params=index_params,
            )
            logger.info(f"Collection '{self.collection_name}' created successfully.")

    async def index_document(self, chunks: List[Document]) -> Dict[str, List[Any]]:
        logger.info(f"Indexing {len(chunks)} documents .....")

        raw_text = []
        embeddings = []
        for chunk in chunks:
            raw_text.append(chunk.page_content)
            embedding = self.jina_embedding_fn.encode_documents([chunk.page_content])
            # Convert numpy array to list for Milvus compatibility
            embedding_list = (
                embedding[0].tolist()
                if hasattr(embedding[0], "tolist")
                else list(embedding[0])
            )
            embeddings.append(embedding_list)

            self.client.insert(
                collection_name=self.collection_name,
                data={"document": chunk.page_content, "dense": embedding_list},
            )

        return {"raw_text": raw_text, "embedding": embeddings}
