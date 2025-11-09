from src.config import Settings
from .mongo_client import MongoDBClient
from .aws_client import AWSClient
from .milvus_client import MilvusClient

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def make_database_client(settings: Settings):
    return MongoDBClient(settings)


def make_aws_client(settings: Settings):
    return AWSClient(settings)

def make_milvus_client(settings: Settings):
    return MilvusClient(settings)
