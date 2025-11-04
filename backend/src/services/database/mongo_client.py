from pymongo.asynchronous.mongo_client import AsyncMongoClient
from pymongo.server_api import ServerApi
import ssl

from src.config import Settings

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MongoDBClient:
    def __init__(self, settings: Settings):
        self.settings = settings.mongo_db
        self.uri = self.settings.mongo_uri

        # Configure SSL/TLS settings for MongoDB Atlas
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        self.client = AsyncMongoClient(
            host=self.uri,
            server_api=ServerApi("1"),
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000,
        )
        self.collection = self.init_database()

    def init_database(self):
        database = self.client.get_database(self.settings.mongo_database)
        collection = database.get_collection(self.settings.mongo_collection)
        
        logger.info('MongoDB client initialized sucessfully')
        return collection
