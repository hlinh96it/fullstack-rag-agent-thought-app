from src.config import Settings
from .mongo_client import MongoDBClient
from .aws_client import AWSClient

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def make_database_client(settings: Settings):
    settings = settings if settings else Settings()
    return MongoDBClient(settings)

def make_aws_client(settings: Settings):
    settings = settings if settings else Settings()
    return AWSClient(settings)
