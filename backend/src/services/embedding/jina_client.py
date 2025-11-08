from typing import List
import httpx

from src.config import Settings
from src.schema.embeddings.jina import JinaEmbeddingRequest, JinaEmbeddingResponse

import logging

logger = logging.getLogger(__name__)


class JinaEmbeddingClient:
    def __init__(self, settings: Settings):
        self.settings = settings.jina
        self.embedding_url = self.settings.embedding_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.jina_api_key}",
        }
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info("👌 Jina Embedding Client initialized")

    async def embed_documents(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
            request_data = JinaEmbeddingRequest(
                model=self.settings.model_name, task="retrieval.passage",
                dimensions=1024, input=batch,
            )

            try:
                response = await self.client.post(
                    url=f'{self.embedding_url}', headers=self.headers, json=request_data.model_dump()
                )
                response.raise_for_status()

                result = JinaEmbeddingResponse(**response.json())
                batch_embeddings = [item['embedding'] for item in result.data]
                embeddings.extend(batch_embeddings)

                logger.debug(f'Embedded batch of {len(batch)} passages')

            except httpx.HTTPError as e:
                logger.error(f"Error embedding passages: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in embed_passages: {e}")
                raise

        logger.info(f"Successfully embedded {len(texts)} passages")
        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        request_data = JinaEmbeddingRequest(
            model=self.settings.model_name, task='retrieval.query', dimensions=1024, input=[query]
        )

        try:
            response = await self.client.post(
                url=self.settings.embedding_url, headers=self.headers, json=request_data.model_dump()
            )
            result = JinaEmbeddingResponse(**response.json())
            embedding = result.data[0]['embedding']

            logger.debug(f'Embeded query: "{query[:50]}..."')
            return embedding
        
        except httpx.HTTPError as e:
            logger.error(f"Error embedding query: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in embed_query: {e}")
            raise
        
    async def close(self):
        await self.client.aclose()
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
