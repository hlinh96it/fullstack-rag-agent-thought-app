import csv
import io
import time
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import Optional

from src.dependencies import PostgreSQLDependency, MongoDependency
from src.schema.user.models import PostgresTable

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["postgres"])


@router.post(
    "/upload/{user_id}",
    description="Upload csv file and add to PostgreSQL database as new table",
)
async def add_new_table(
    user_id: str,
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

        # Create table in PostgreSQL
        row_count = postgres_client.create_table_from_csv(
            table_name=table_name, headers=headers, rows=rows
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

        # Update user document in MongoDB with table metadata
        await mongodb_client.collection.update_one(
            {"_id": user_id},
            {"$push": {"table_list": table_metadata.model_dump()}},
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
    "/tables/{user_id}",
    description="Get list of PostgreSQL tables for a specific user",
)
async def get_user_tables(
    user_id: str,
    mongodb_client: MongoDependency,
):
    """
    Retrieve all PostgreSQL tables metadata for a specific user.

    Args:
        user_id: User identifier
        mongodb_client: MongoDB client dependency

    Returns:
        dict: List of table metadata
    """
    try:
        # Fetch user document from MongoDB
        user_doc = await mongodb_client.collection.find_one({"_id": user_id})

        if not user_doc:
            return {
                "user_id": user_id,
                "tables": [],
                "total_tables": 0,
            }

        table_list = user_doc.get("table_list", [])

        return {
            "user_id": user_id,
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
    limit: int = 100,
):
    """
    Retrieve data from a specific PostgreSQL table.

    Args:
        table_name: Name of the table
        postgres_client: PostgreSQL client dependency
        limit: Maximum number of rows to return (default 100)

    Returns:
        dict: Table data with columns and rows
    """
    try:
        data = postgres_client.get_table_data(table_name, limit)
        return data

    except Exception as e:
        logger.error(f"Error fetching table data: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch table data: {str(e)}"
        )


@router.delete(
    "/table/{user_id}/{table_name}",
    description="Delete a PostgreSQL table and remove from user metadata",
)
async def delete_table(
    user_id: str,
    table_name: str,
    postgres_client: PostgreSQLDependency,
    mongodb_client: MongoDependency,
):
    """
    Delete a table from PostgreSQL and remove metadata from MongoDB.

    Args:
        user_id: User identifier
        table_name: Name of the table to delete
        postgres_client: PostgreSQL client dependency
        mongodb_client: MongoDB client dependency

    Returns:
        dict: Success message
    """
    try:
        # Delete table from PostgreSQL
        postgres_client.delete_table(table_name)

        # Remove table metadata from MongoDB
        await mongodb_client.collection.update_one(
            {"_id": user_id},
            {"$pull": {"table_list": {"table_name": table_name}}},
        )

        logger.info(f"Successfully deleted table '{table_name}' for user {user_id}")

        return {
            "message": "Table deleted successfully",
            "table_name": table_name,
        }

    except Exception as e:
        logger.error(f"Error deleting table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete table: {str(e)}")
