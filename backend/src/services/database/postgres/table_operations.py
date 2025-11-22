"""Table operations service for PostgreSQL database management."""

import time
from typing import List, Optional, Dict, Any
from bson import ObjectId

from src.schema.user.models import PostgresTable
from src.services.database.postgres_client import PostgreSQLDBClient
from src.services.database.mongo_client import MongoDBClient

import logging

logger = logging.getLogger(__name__)


class TableOperations:
    """Handles all table-related operations for PostgreSQL."""

    @staticmethod
    async def create_table_from_csv(
        user_id: str,
        database_name: str,
        table_name: str,
        original_filename: str,
        headers: List[str],
        rows: List[List[str]],
        postgres_client: PostgreSQLDBClient,
        mongodb_client: MongoDBClient,
    ) -> Dict[str, Any]:
        """
        Create a new table from CSV data and update metadata.

        Args:
            user_id: User identifier
            database_name: Database name
            table_name: Name for the new table
            original_filename: Original CSV filename
            headers: Column headers
            rows: Data rows
            postgres_client: PostgreSQL client
            mongodb_client: MongoDB client

        Returns:
            dict: Table creation result with metadata
        """
        # Create table in PostgreSQL
        row_count = postgres_client.create_table_from_csv(
            table_name=table_name,
            headers=headers,
            rows=rows,
            database_name=database_name,
        )

        # Create metadata
        current_time = int(time.time())
        table_metadata = PostgresTable(
            table_name=table_name,
            original_filename=original_filename,
            row_count=row_count,
            column_count=len(headers),
            columns=headers,
            created_at=current_time,
            updated_at=current_time,
        )

        # Update MongoDB
        await TableOperations._update_table_metadata(
            user_id=user_id,
            database_name=database_name,
            table_metadata=table_metadata,
            mongodb_client=mongodb_client,
        )

        logger.info(
            f"Successfully created table '{table_name}' with {row_count} rows for user {user_id}"
        )

        return {
            "message": "Table created successfully",
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(headers),
            "columns": headers,
        }

    @staticmethod
    async def _update_table_metadata(
        user_id: str,
        database_name: str,
        table_metadata: PostgresTable,
        mongodb_client: MongoDBClient,
    ) -> None:
        """Update table metadata in MongoDB."""
        from src.schema.user.models import PostgresDatabase

        current_time = int(time.time())
        user_doc = await mongodb_client.collection.find_one({"_id": ObjectId(user_id)})

        if user_doc:
            database_list = user_doc.get("database_list", [])
            db_found = any(
                db.get("database_name") == database_name for db in database_list
            )

            if db_found:
                # Database exists, add table to it
                await mongodb_client.collection.update_one(
                    {
                        "_id": ObjectId(user_id),
                        "database_list.database_name": database_name,
                    },
                    {
                        "$push": {
                            "database_list.$.table_list": table_metadata.model_dump()
                        },
                        "$set": {"database_list.$.updated_at": current_time},
                    },
                )
            else:
                # Database doesn't exist, create it with the table
                database_metadata = PostgresDatabase(
                    database_name=database_name,
                    table_list=[table_metadata],
                    created_at=current_time,
                    updated_at=current_time,
                )

                await mongodb_client.collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$push": {"database_list": database_metadata.model_dump()}},
                )
        else:
            # User doesn't exist, create user with database and table
            database_metadata = PostgresDatabase(
                database_name=database_name,
                table_list=[table_metadata],
                created_at=current_time,
                updated_at=current_time,
            )

            await mongodb_client.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$push": {"database_list": database_metadata.model_dump()}},
                upsert=True,
            )

    @staticmethod
    async def get_user_tables(
        user_id: str,
        database_name: str,
        mongodb_client: MongoDBClient,
    ) -> Dict[str, Any]:
        """
        Retrieve all tables for a specific database.

        Args:
            user_id: User identifier
            database_name: Database name
            mongodb_client: MongoDB client

        Returns:
            dict: List of table metadata
        """
        user_doc = await mongodb_client.collection.find_one({"_id": ObjectId(user_id)})

        if not user_doc:
            return {
                "user_id": user_id,
                "database_name": database_name,
                "tables": [],
                "total_tables": 0,
            }

        database_list = user_doc.get("database_list", [])
        table_list = []

        # Find the specific database and get its tables
        for db in database_list:
            if db.get("database_name") == database_name:
                table_list = db.get("table_list", [])
                break

        return {
            "user_id": user_id,
            "database_name": database_name,
            "tables": table_list,
            "total_tables": len(table_list),
        }

    @staticmethod
    def get_table_data(
        table_name: str,
        postgres_client: PostgreSQLDBClient,
        database_name: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Retrieve data from a specific table.

        Args:
            table_name: Table name
            postgres_client: PostgreSQL client
            database_name: Optional database name
            limit: Maximum number of rows

        Returns:
            dict: Table data with columns and rows
        """
        return postgres_client.get_table_data(table_name, limit, database_name)

    @staticmethod
    async def delete_table(
        user_id: str,
        database_name: str,
        table_name: str,
        postgres_client: PostgreSQLDBClient,
        mongodb_client: MongoDBClient,
    ) -> Dict[str, str]:
        """
        Delete a table from PostgreSQL and remove metadata.

        Args:
            user_id: User identifier
            database_name: Database name
            table_name: Table name
            postgres_client: PostgreSQL client
            mongodb_client: MongoDB client

        Returns:
            dict: Success message
        """
        # Delete from PostgreSQL
        postgres_client.delete_table(table_name)

        # Remove from MongoDB
        await mongodb_client.collection.update_one(
            {"_id": ObjectId(user_id), "database_list.database_name": database_name},
            {"$pull": {"database_list.$.table_list": {"table_name": table_name}}},
        )

        logger.info(
            f"Successfully deleted table '{table_name}' from database '{database_name}' for user {user_id}"
        )

        return {
            "message": "Table deleted successfully",
            "database_name": database_name,
            "table_name": table_name,
        }
