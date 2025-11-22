"""Sync operations service for PostgreSQL and MongoDB synchronization."""

import time
from typing import Dict, Any
from bson import ObjectId

from src.schema.user.models import PostgresDatabase, PostgresTable
from src.services.database.postgres_client import PostgreSQLDBClient
from src.services.database.mongo_client import MongoDBClient

import logging

logger = logging.getLogger(__name__)


class SyncOperations:
    """Handles synchronization between PostgreSQL and MongoDB metadata."""

    @staticmethod
    async def sync_databases_and_tables(
        user_id: str,
        postgres_client: PostgreSQLDBClient,
        mongodb_client: MongoDBClient,
    ) -> Dict[str, Any]:
        """
        Synchronize PostgreSQL databases and tables with MongoDB metadata.

        This ensures both data stores are in sync by:
        1. Adding databases/tables from PostgreSQL that are missing in MongoDB
        2. Removing databases/tables from MongoDB that no longer exist in PostgreSQL
        3. Updating table metadata (row counts, columns) to match actual PostgreSQL data

        Args:
            user_id: User identifier
            postgres_client: PostgreSQL client
            mongodb_client: MongoDB client

        Returns:
            dict: Sync summary with added, removed, and updated items
        """
        current_time = int(time.time())

        # Get actual databases from PostgreSQL
        pg_databases = postgres_client.get_all_user_databases()

        # Get user's MongoDB data
        user_doc = await mongodb_client.collection.find_one({"_id": ObjectId(user_id)})
        mongo_database_list = user_doc.get("database_list", []) if user_doc else []

        # Create lookup maps
        mongo_db_map = {db["database_name"]: db for db in mongo_database_list}

        # Track changes
        sync_summary = {
            "databases_added": [],
            "databases_removed": [],
            "tables_added": [],
            "tables_removed": [],
            "tables_updated": [],
        }

        # Build new database list
        new_database_list = []

        # Process each PostgreSQL database
        for pg_db_name in pg_databases:
            pg_tables = postgres_client.get_tables_in_database(pg_db_name)

            if pg_db_name in mongo_db_map:
                # Database exists, sync tables
                database_metadata = SyncOperations._sync_existing_database(
                    pg_db_name=pg_db_name,
                    pg_tables=pg_tables,
                    mongo_db=mongo_db_map[pg_db_name],
                    current_time=current_time,
                    sync_summary=sync_summary,
                )
            else:
                # New database found
                database_metadata = SyncOperations._sync_new_database(
                    pg_db_name=pg_db_name,
                    pg_tables=pg_tables,
                    current_time=current_time,
                    sync_summary=sync_summary,
                )

            new_database_list.append(database_metadata.model_dump())

        # Check for removed databases
        SyncOperations._check_removed_databases(
            mongo_db_map=mongo_db_map,
            pg_databases=pg_databases,
            sync_summary=sync_summary,
        )

        # Update MongoDB with synced data
        await mongodb_client.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"database_list": new_database_list}},
            upsert=True,
        )

        logger.info(f"Successfully synced databases and tables for user {user_id}")

        return {
            "message": "Sync completed successfully",
            "user_id": user_id,
            "summary": sync_summary,
            "total_databases": len(new_database_list),
            "total_tables": sum(
                len(db.get("table_list", [])) for db in new_database_list
            ),
        }

    @staticmethod
    def _sync_existing_database(
        pg_db_name: str,
        pg_tables: list,
        mongo_db: dict,
        current_time: int,
        sync_summary: dict,
    ) -> PostgresDatabase:
        """Sync an existing database by updating its tables."""
        mongo_tables = {t["table_name"]: t for t in mongo_db.get("table_list", [])}
        new_table_list = []

        # Process PostgreSQL tables
        for pg_table in pg_tables:
            table_name = pg_table["table_name"]

            if table_name in mongo_tables:
                # Table exists, check if needs updating
                mongo_table = mongo_tables[table_name]
                needs_update = (
                    mongo_table.get("row_count") != pg_table["row_count"]
                    or mongo_table.get("column_count") != pg_table["column_count"]
                    or set(mongo_table.get("columns", [])) != set(pg_table["columns"])
                )

                if needs_update:
                    sync_summary["tables_updated"].append(f"{pg_db_name}.{table_name}")

                # Update table metadata
                table_metadata = PostgresTable(
                    table_name=table_name,
                    original_filename=mongo_table.get(
                        "original_filename", f"{table_name}.csv"
                    ),
                    row_count=pg_table["row_count"],
                    column_count=pg_table["column_count"],
                    columns=pg_table["columns"],
                    created_at=mongo_table.get("created_at", current_time),
                    updated_at=current_time,
                )
            else:
                # New table found
                sync_summary["tables_added"].append(f"{pg_db_name}.{table_name}")
                table_metadata = PostgresTable(
                    table_name=table_name,
                    original_filename=f"{table_name}.csv",
                    row_count=pg_table["row_count"],
                    column_count=pg_table["column_count"],
                    columns=pg_table["columns"],
                    created_at=current_time,
                    updated_at=current_time,
                )

            new_table_list.append(table_metadata.model_dump())

        # Check for removed tables
        for mongo_table_name in mongo_tables:
            if not any(t["table_name"] == mongo_table_name for t in pg_tables):
                sync_summary["tables_removed"].append(
                    f"{pg_db_name}.{mongo_table_name}"
                )

        return PostgresDatabase(
            database_name=pg_db_name,
            table_list=[PostgresTable(**t) for t in new_table_list],
            created_at=mongo_db.get("created_at", current_time),
            updated_at=current_time,
        )

    @staticmethod
    def _sync_new_database(
        pg_db_name: str,
        pg_tables: list,
        current_time: int,
        sync_summary: dict,
    ) -> PostgresDatabase:
        """Sync a newly discovered database."""
        sync_summary["databases_added"].append(pg_db_name)

        table_list = []
        for pg_table in pg_tables:
            sync_summary["tables_added"].append(
                f"{pg_db_name}.{pg_table['table_name']}"
            )

            table_metadata = PostgresTable(
                table_name=pg_table["table_name"],
                original_filename=f"{pg_table['table_name']}.csv",
                row_count=pg_table["row_count"],
                column_count=pg_table["column_count"],
                columns=pg_table["columns"],
                created_at=current_time,
                updated_at=current_time,
            )
            table_list.append(table_metadata.model_dump())

        return PostgresDatabase(
            database_name=pg_db_name,
            table_list=table_list,
            created_at=current_time,
            updated_at=current_time,
        )

    @staticmethod
    def _check_removed_databases(
        mongo_db_map: dict,
        pg_databases: list,
        sync_summary: dict,
    ) -> None:
        """Check for databases removed from PostgreSQL."""
        for mongo_db_name in mongo_db_map:
            if mongo_db_name not in pg_databases:
                sync_summary["databases_removed"].append(mongo_db_name)
                # Count removed tables
                mongo_db = mongo_db_map[mongo_db_name]
                for table in mongo_db.get("table_list", []):
                    sync_summary["tables_removed"].append(
                        f"{mongo_db_name}.{table['table_name']}"
                    )
