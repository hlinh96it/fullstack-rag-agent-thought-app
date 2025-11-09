#!/usr/bin/env python3
"""
Test script for the AgenticRAG system.
This script tests the agent without running the full server.
"""

import os
import asyncio
import logging
import warnings

# Suppress gRPC fork warnings
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = '0'
os.environ['GRPC_POLL_STRATEGY'] = 'poll'

# Suppress other warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

from src.config import Settings
from src.services.chat.factory import make_agent_client
from src.services.database.factory import make_milvus_client
from src.schema.llm.models import AskRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_agent():
    """Test the agent with a sample query."""
    logger.info("🚀 Starting agent test...")
    
    # Initialize settings
    settings = Settings()
    logger.info("✅ Settings loaded")
    
    # Initialize Milvus client
    milvus_client = make_milvus_client(settings)
    logger.info("✅ Milvus client initialized")
    
    # Configure vector stores
    vector_stores = [
        {
            'store': milvus_client.vector_store,
            'name': 'paper_retriever',
            'description': 'Search and retrieve relevant information from academic papers and research documents',
            'k': 4,
            'ranker_weights': [0.6, 0.4]
        }
    ]
    
    # Initialize agent
    agent = make_agent_client(settings, vector_stores)
    logger.info("✅ Agent initialized")
    logger.info(f"📊 Agent has {len(agent.vector_stores)} vector store(s)")
    logger.info(f"🤖 Using model: {settings.openai.model_name}")
    
    # Test queries
    test_queries = [
        "What is machine learning?",
        "Explain retrieval-augmented generation",
        "Hello, how are you?",  # Should not trigger retrieval
    ]
    
    for i, query_text in enumerate(test_queries, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Test {i}/{len(test_queries)}: {query_text}")
        logger.info('='*60)
        
        try:
            request = AskRequest(prompt=query_text)
            response = agent.run(request)
            
            logger.info(f"✅ Response received:")
            logger.info(f"   {response.answer}")
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("🎉 Agent test completed!")
    logger.info("="*60)


if __name__ == "__main__":
    try:
        test_agent()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
