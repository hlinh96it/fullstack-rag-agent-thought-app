import csv
import io
import time
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import Optional
from bson import ObjectId

from src.dependencies import PostgreSQLDependency, MongoDependency
from src.schema.user.models import PostgresTable

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
        postgres_client: PostgreSQL client dependency
        mongodb_client: MongoDB client dependency
        file: CSV file to upload
        table_name: Optional custom table name (will use filename if not provided)

    Returns:
        dict: Success message with table name and row count
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed")

        # Read the CSV file
        contents = await file.read()
        csv_data = io.StringIO(contents.decode("utf-8"))

        # Parse CSV to get headers and data
        csv_reader = csv.reader(csv_data)
        headers = next(csv_reader)  # First row is headers
        rows = list(csv_reader)

        if not headers or not rows:
            raise HTTPException(
                status_code=400, detail="CSV file is empty or has no data"
            )

        # Generate table name from input or filename (sanitize it)
        if not table_name:
            table_name = file.filename.replace(".csv", "").lower()
        else:
            table_name = table_name.strip().lower()

        # Sanitize table name
        table_name = "".join(c if c.isalnum() or c == "_" else "_" for c in table_name)

        # Create table in PostgreSQL with specified database
        row_count = postgres_client.create_table_from_csv(
            table_name=table_name,
            headers=headers,
            rows=rows,
            database_name=database_name,
        )

        # Create table metadata
        current_time = int(time.time())
        table_metadata = PostgresTable(
            table_name=table_name,
            original_filename=file.filename,
            row_count=row_count,
            column_count=len(headers),
            columns=headers,
            created_at=current_time,
            updated_at=current_time,
        )

        # Update user document in MongoDB - add table to the specific database
        user_doc = await mongodb_client.collection.find_one({"_id": ObjectId(user_id)})

        if user_doc:
            database_list = user_doc.get("database_list", [])
            db_found = False

            # Find the database and add table to it
            for db in database_list:
                if db.get("database_name") == database_name:
                    db_found = True
                    break

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
                from src.schema.user.models import PostgresDatabase

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
            from src.schema.user.models import PostgresDatabase

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
        # Fetch user document from MongoDB
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
        data = postgres_client.get_table_data(table_name, limit, database_name)
        return data

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
        # Delete table from PostgreSQL
        postgres_client.delete_table(table_name)

        # Remove table metadata from MongoDB - pull from the specific database's table_list
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
        # Create database in PostgreSQL
        postgres_client.create_database(database_name)

        # Add database to user's database_list in MongoDB
        current_time = int(time.time())
        from src.schema.user.models import PostgresDatabase

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
            # Check if database already exists
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
        # Auto-sync if enabled
        if auto_sync:
            try:
                await sync_databases_and_tables(
                    user_id, postgres_client, mongodb_client
                )
            except Exception as sync_error:
                logger.warning(
                    f"Auto-sync failed, proceeding with cached data: {sync_error}"
                )

        # Fetch user document from MongoDB
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
        # Delete database from PostgreSQL
        postgres_client.delete_database(database_name)

        # Remove database from MongoDB user's database_list
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
        from src.schema.user.models import PostgresDatabase, PostgresTable

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
            # Get tables from this database
            pg_tables = postgres_client.get_tables_in_database(pg_db_name)

            if pg_db_name in mongo_db_map:
                # Database exists in MongoDB, sync tables
                mongo_db = mongo_db_map[pg_db_name]
                mongo_tables = {
                    t["table_name"]: t for t in mongo_db.get("table_list", [])
                }

                new_table_list = []

                # Process PostgreSQL tables
                for pg_table in pg_tables:
                    table_name = pg_table["table_name"]

                    if table_name in mongo_tables:
                        # Table exists, update metadata
                        mongo_table = mongo_tables[table_name]

                        # Check if metadata needs updating
                        needs_update = (
                            mongo_table.get("row_count") != pg_table["row_count"]
                            or mongo_table.get("column_count")
                            != pg_table["column_count"]
                            or set(mongo_table.get("columns", []))
                            != set(pg_table["columns"])
                        )

                        if needs_update:
                            sync_summary["tables_updated"].append(
                                f"{pg_db_name}.{table_name}"
                            )

                        # Use existing table data but update metadata
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
                        new_table_list.append(table_metadata.model_dump())
                    else:
                        # New table found in PostgreSQL
                        sync_summary["tables_added"].append(
                            f"{pg_db_name}.{table_name}"
                        )

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

                # Check for tables in MongoDB that no longer exist in PostgreSQL
                for mongo_table_name in mongo_tables:
                    if not any(t["table_name"] == mongo_table_name for t in pg_tables):
                        sync_summary["tables_removed"].append(
                            f"{pg_db_name}.{mongo_table_name}"
                        )

                # Update database with synced tables
                database_metadata = PostgresDatabase(
                    database_name=pg_db_name,
                    table_list=[PostgresTable(**t) for t in new_table_list],
                    created_at=mongo_db.get("created_at", current_time),
                    updated_at=current_time,
                )
                new_database_list.append(database_metadata.model_dump())

            else:
                # New database found in PostgreSQL
                sync_summary["databases_added"].append(pg_db_name)

                # Create table metadata for all tables
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

                database_metadata = PostgresDatabase(
                    database_name=pg_db_name,
                    table_list=table_list,
                    created_at=current_time,
                    updated_at=current_time,
                )
                new_database_list.append(database_metadata.model_dump())

        # Check for databases in MongoDB that no longer exist in PostgreSQL
        for mongo_db_name in mongo_db_map:
            if mongo_db_name not in pg_databases:
                sync_summary["databases_removed"].append(mongo_db_name)
                # Also count all tables as removed
                mongo_db = mongo_db_map[mongo_db_name]
                for table in mongo_db.get("table_list", []):
                    sync_summary["tables_removed"].append(
                        f"{mongo_db_name}.{table['table_name']}"
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

    except Exception as e:
        logger.error(f"Error syncing databases: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to sync databases: {str(e)}"
        )
