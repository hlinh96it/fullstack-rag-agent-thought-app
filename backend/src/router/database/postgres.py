from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import Optional

from src.dependencies import PostgreSQLDependency, MongoDependency
from src.services.database.postgres import (
    TableOperations,
    DatabaseOperations,
    SyncOperations,
)
from src.services.database.postgres.validators import CSVValidator

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["postgres"])


@router.post(
    "/upload/{user_id}/{database_name}",
    description="Upload csv file and add to PostgreSQL database as new table",
)
async def add_new_table(
    user_id: str,
    database_name: str,
    postgres_client: PostgreSQLDependency,
    mongodb_client: MongoDependency,
    file: UploadFile = File(...),
    table_name: Optional[str] = Form(None),
):
    """
    Upload a CSV file and create a new table in PostgreSQL database.

    Args:
        user_id: User identifier
        database_name: Database name
        postgres_client: PostgreSQL client dependency
        mongodb_client: MongoDB client dependency
        file: CSV file to upload
        table_name: Optional custom table name (will use filename if not provided)

    Returns:
        dict: Success message with table name and row count
    """
    try:
        # Validate and parse CSV
        headers, rows = await CSVValidator.validate_and_parse_csv(file)

        # Generate and sanitize table name
        if not table_name:
            assert file.filename is not None
            table_name = file.filename.replace(".csv", "").lower()
        else:
            table_name = table_name.strip().lower()

        table_name = CSVValidator.sanitize_table_name(table_name)

        # Create table using service
        return await TableOperations.create_table_from_csv(
            user_id=user_id,
            database_name=database_name,
            table_name=table_name,
            original_filename=file.filename or "unknown.csv",
            headers=headers,
            rows=rows,
            postgres_client=postgres_client,
            mongodb_client=mongodb_client,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading CSV file: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to upload CSV file: {str(e)}"
        )


@router.get(
    "/tables/{user_id}/{database_name}",
    description="Get list of PostgreSQL tables for a specific database",
)
async def get_user_tables(
    user_id: str,
    database_name: str,
    mongodb_client: MongoDependency,
):
    """
    Retrieve all PostgreSQL tables metadata for a specific database.

    Args:
        user_id: User identifier
        database_name: Database name
        mongodb_client: MongoDB client dependency

    Returns:
        dict: List of table metadata
    """
    try:
        return await TableOperations.get_user_tables(
            user_id=user_id,
            database_name=database_name,
            mongodb_client=mongodb_client,
        )
    except Exception as e:
        logger.error(f"Error fetching user tables: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch user tables: {str(e)}"
        )


@router.get(
    "/table/{table_name}/data",
    description="Get data from a specific PostgreSQL table",
)
async def get_table_data(
    table_name: str,
    postgres_client: PostgreSQLDependency,
    database_name: Optional[str] = None,
    limit: int = 100,
):
    """
    Retrieve data from a specific PostgreSQL table.

    Args:
        table_name: Name of the table
        postgres_client: PostgreSQL client dependency
        database_name: Optional database name (query parameter)
        limit: Maximum number of rows to return (default 100)

    Returns:
        dict: Table data with columns and rows
    """
    try:
        return TableOperations.get_table_data(
            table_name=table_name,
            postgres_client=postgres_client,
            database_name=database_name,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error fetching table data: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch table data: {str(e)}"
        )


@router.delete(
    "/table/{user_id}/{database_name}/{table_name}",
    description="Delete a PostgreSQL table and remove from user metadata",
)
async def delete_table(
    user_id: str,
    database_name: str,
    table_name: str,
    postgres_client: PostgreSQLDependency,
    mongodb_client: MongoDependency,
):
    """
    Delete a table from PostgreSQL and remove metadata from MongoDB.

    Args:
        user_id: User identifier
        database_name: Database name
        table_name: Name of the table to delete
        postgres_client: PostgreSQL client dependency
        mongodb_client: MongoDB client dependency

    Returns:
        dict: Success message
    """
    try:
        return await TableOperations.delete_table(
            user_id=user_id,
            database_name=database_name,
            table_name=table_name,
            postgres_client=postgres_client,
            mongodb_client=mongodb_client,
        )
    except Exception as e:
        logger.error(f"Error deleting table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete table: {str(e)}")


# Database management endpoints
@router.post(
    "/database/create/{user_id}",
    description="Create a new PostgreSQL database",
)
async def create_database(
    user_id: str,
    postgres_client: PostgreSQLDependency,
    mongodb_client: MongoDependency,
    database_name: str = Form(...),
):
    """
    Create a new PostgreSQL database.

    Args:
        user_id: User identifier
        postgres_client: PostgreSQL client dependency
        mongodb_client: MongoDB client dependency
        database_name: Name of the database to create

    Returns:
        dict: Success message with database name
    """
    try:
        return await DatabaseOperations.create_database(
            user_id=user_id,
            database_name=database_name,
            postgres_client=postgres_client,
            mongodb_client=mongodb_client,
        )
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create database: {str(e)}"
        )


@router.get(
    "/databases/{user_id}",
    description="List all PostgreSQL databases for a user with auto-sync",
)
async def list_databases(
    user_id: str,
    mongodb_client: MongoDependency,
    postgres_client: PostgreSQLDependency,
    auto_sync: bool = True,
):
    """
    List all PostgreSQL databases for a specific user from MongoDB.
    Optionally auto-syncs with PostgreSQL before returning data.

    Args:
        user_id: User identifier
        mongodb_client: MongoDB client dependency
        postgres_client: PostgreSQL client dependency
        auto_sync: Whether to sync with PostgreSQL before returning (default: True)

    Returns:
        dict: List of databases with their details
    """
    try:
        return await DatabaseOperations.list_databases(
            user_id=user_id,
            mongodb_client=mongodb_client,
            postgres_client=postgres_client,
            auto_sync=auto_sync,
        )
    except Exception as e:
        logger.error(f"Error listing databases: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list databases: {str(e)}"
        )


@router.delete(
    "/database/{user_id}/{database_name}",
    description="Delete a PostgreSQL database",
)
async def delete_database(
    user_id: str,
    database_name: str,
    postgres_client: PostgreSQLDependency,
    mongodb_client: MongoDependency,
):
    """
    Delete a PostgreSQL database.

    Args:
        user_id: User identifier
        database_name: Name of the database to delete
        postgres_client: PostgreSQL client dependency
        mongodb_client: MongoDB client dependency

    Returns:
        dict: Success message
    """
    try:
        return await DatabaseOperations.delete_database(
            user_id=user_id,
            database_name=database_name,
            postgres_client=postgres_client,
            mongodb_client=mongodb_client,
        )
    except Exception as e:
        logger.error(f"Error deleting database: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete database: {str(e)}"
        )


@router.post(
    "/sync/{user_id}",
    description="Sync PostgreSQL databases and tables with MongoDB metadata",
)
async def sync_databases_and_tables(
    user_id: str,
    postgres_client: PostgreSQLDependency,
    mongodb_client: MongoDependency,
):
    """
    Synchronize PostgreSQL databases and tables with MongoDB metadata.
    This ensures both data stores are in sync by:
    1. Adding databases/tables from PostgreSQL that are missing in MongoDB
    2. Removing databases/tables from MongoDB that no longer exist in PostgreSQL
    3. Updating table metadata (row counts, columns) to match actual PostgreSQL data

    Args:
        user_id: User identifier
        postgres_client: PostgreSQL client dependency
        mongodb_client: MongoDB client dependency

    Returns:
        dict: Sync summary with added, removed, and updated items
    """
    try:
        return await SyncOperations.sync_databases_and_tables(
            user_id=user_id,
            postgres_client=postgres_client,
            mongodb_client=mongodb_client,
        )
    except Exception as e:
        logger.error(f"Error syncing databases: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to sync databases: {str(e)}"
        )
