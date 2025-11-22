"""Database operations service for PostgreSQL database management."""

import time
from typing import Dict, Any, List
from bson import ObjectId

from src.schema.user.models import PostgresDatabase
from src.services.database.postgres_client import PostgreSQLDBClient
from src.services.database.mongo_client import MongoDBClient

import logging

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """Handles all database-level operations for PostgreSQL."""

    @staticmethod
    async def create_database(
        user_id: str,
        database_name: str,
        postgres_client: PostgreSQLDBClient,
        mongodb_client: MongoDBClient,
    ) -> Dict[str, str]:
        """
        Create a new PostgreSQL database.

        Args:
            user_id: User identifier
            database_name: Name of the database to create
            postgres_client: PostgreSQL client
            mongodb_client: MongoDB client

        Returns:
            dict: Success message with database name
        """
        # Create database in PostgreSQL
        postgres_client.create_database(database_name)

        # Add to MongoDB
        current_time = int(time.time())
        database_metadata = PostgresDatabase(
            database_name=database_name,
            table_list=[],
            created_at=current_time,
            updated_at=current_time,
        )

        # Check if database already exists in user's list
        user_doc = await mongodb_client.collection.find_one({"_id": ObjectId(user_id)})

        if user_doc:
            database_list = user_doc.get("database_list", [])
            db_exists = any(
                db.get("database_name") == database_name for db in database_list
            )

            if not db_exists:
                await mongodb_client.collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$push": {"database_list": database_metadata.model_dump()}},
                )
        else:
            # Create user if doesn't exist
            await mongodb_client.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$push": {"database_list": database_metadata.model_dump()}},
                upsert=True,
            )

        logger.info(
            f"Successfully created database '{database_name}' for user {user_id}"
        )

        return {
            "message": "Database created successfully",
            "database_name": database_name,
        }

    @staticmethod
    async def list_databases(
        user_id: str,
        mongodb_client: MongoDBClient,
        postgres_client: PostgreSQLDBClient,
        auto_sync: bool = True,
    ) -> Dict[str, Any]:
        """
        List all databases for a user with optional auto-sync.

        Args:
            user_id: User identifier
            mongodb_client: MongoDB client
            postgres_client: PostgreSQL client
            auto_sync: Whether to sync before returning

        Returns:
            dict: List of databases with their details
        """
        # Auto-sync if enabled
        if auto_sync:
            try:
                from .sync_operations import SyncOperations

                await SyncOperations.sync_databases_and_tables(
                    user_id, postgres_client, mongodb_client
                )
            except Exception as sync_error:
                logger.warning(
                    f"Auto-sync failed, proceeding with cached data: {sync_error}"
                )

        # Fetch from MongoDB
        user_doc = await mongodb_client.collection.find_one({"_id": ObjectId(user_id)})

        if not user_doc:
            return {
                "user_id": user_id,
                "databases": [],
                "total": 0,
            }

        database_list = user_doc.get("database_list", [])

        return {
            "user_id": user_id,
            "databases": database_list,
            "total": len(database_list),
        }

    @staticmethod
    async def delete_database(
        user_id: str,
        database_name: str,
        postgres_client: PostgreSQLDBClient,
        mongodb_client: MongoDBClient,
    ) -> Dict[str, str]:
        """
        Delete a PostgreSQL database.

        Args:
            user_id: User identifier
            database_name: Database name
            postgres_client: PostgreSQL client
            mongodb_client: MongoDB client

        Returns:
            dict: Success message
        """
        # Delete from PostgreSQL
        postgres_client.delete_database(database_name)

        # Remove from MongoDB
        await mongodb_client.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"database_list": {"database_name": database_name}}},
        )

        logger.info(
            f"Successfully deleted database '{database_name}' for user {user_id}"
        )

        return {
            "message": "Database deleted successfully",
            "database_name": database_name,
        }
