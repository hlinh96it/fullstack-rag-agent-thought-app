from typing import Optional, List, Dict, Any, cast

import pandas as pd
import numpy as np
from sqlalchemy import (
    create_engine,
    inspect,
    text,
    URL,
    Table,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Date,
    Text,
    MetaData,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import session, sessionmaker, declarative_base

from src.config import Settings

import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class PostgreSQLDBClient:
    """PostgreSQL database implementation for data analytics"""

    def __init__(self, settings: Settings):
        self.settings = settings.postgres_db
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.startup()

    def startup(self) -> None:
        """Initialize the database connection."""

        try:
            # %% create connection
            logger.info(
                f"Attempting to connect to PostgreSQL at: {self.settings.host}:{self.settings.port}"
            )
            url = URL.create(
                drivername=self.settings.driver_name,
                username=self.settings.username,
                password=self.settings.password,
                host=self.settings.host,
                port=self.settings.port,
                database=self.settings.database_name,
            )
            self.engine = create_engine(
                url=url,
                echo=False,
                pool_size=self.settings.pool_size,
                max_overflow=self.settings.max_overflow,
                pool_pre_ping=True,  # verify connections before use
            )
            self.session_factory = sessionmaker(
                bind=self.engine, expire_on_commit=False
            )

            # %% test connection
            assert self.engine is not None
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("👌  Database connection test successfully")

            # %% check table exists
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            Base.metadata.create_all(bind=self.engine)

            update_tables = inspector.get_table_names()
            new_tables = set(update_tables) - set(existing_tables)

            if new_tables:
                logger.info(f"🍽️  Create new tables: {', '.join(new_tables)}")
            else:
                logger.info(f"All tables already exist")
            logger.info("👌  PostgreSQL database initilized sucessfully")

        # %% exeptions
        except Exception as e:
            logger.error(f"❌  Failed to initialize PostgreSQL database: {e}")

    def _sanitize_name(self, name: str) -> str:
        """Sanitize table or column names."""
        sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name.lower())
        # Ensure it starts with a letter or underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = f"col_{sanitized}"
        return sanitized or "unnamed"

    def _pandas_dtype_to_sqlalchemy(self, dtype) -> type:
        """
        Map pandas dtype to SQLAlchemy column type.

        Args:
            dtype: Pandas dtype

        Returns:
            SQLAlchemy column type
        """
        if pd.api.types.is_integer_dtype(dtype):
            return Integer
        elif pd.api.types.is_float_dtype(dtype):
            return Float
        elif pd.api.types.is_bool_dtype(dtype):
            return Boolean
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return DateTime
        elif pd.api.types.is_object_dtype(dtype):
            # Check if it's a date
            return Text  # Use Text for longer strings
        else:
            return String

    def create_table_from_csv(
        self, table_name: str, headers: List[str], rows: List[List[str]]
    ) -> int:
        """
        Create a new table from CSV data using SQLAlchemy ORM with pandas type inference.

        Args:
            table_name: Name of the table to create
            headers: List of column names
            rows: List of data rows

        Returns:
            int: Number of rows inserted
        """
        try:
            if not self.engine:
                raise Exception("Database engine not initialized")

            # Create pandas DataFrame for better type inference
            df = pd.DataFrame(rows, columns=headers)

            # Let pandas infer the best dtypes
            df = df.convert_dtypes()

            # Sanitize table and column names
            sanitized_table_name = self._sanitize_name(table_name)

            # Create column mapping: original -> sanitized
            column_mapping = {col: self._sanitize_name(col) for col in headers}
            df.rename(columns=column_mapping, inplace=True)

            # Create metadata
            metadata = MetaData()

            # Define table dynamically with auto-detected column types
            columns = [Column("id", Integer, primary_key=True, autoincrement=True)]

            # Add columns with inferred types
            for col_name in df.columns:
                col_type = self._pandas_dtype_to_sqlalchemy(df[col_name].dtype)
                columns.append(Column(col_name, col_type))  # type: ignore

            # Create table object
            table = Table(
                sanitized_table_name, metadata, *columns, extend_existing=True
            )

            # Drop table if exists (to handle re-uploads)
            with self.engine.begin() as conn:
                metadata.drop_all(conn, tables=[table], checkfirst=True)
                metadata.create_all(conn, tables=[table])

            # Insert data using pandas to_sql for better type handling
            if not df.empty:
                # Replace NaN with None for proper NULL handling
                df = df.replace({np.nan: None})

                # Convert DataFrame to list of dicts
                data_dicts = cast(List[Dict[str, Any]], df.to_dict(orient="records"))

                # Bulk insert
                with self.engine.begin() as conn:
                    conn.execute(table.insert(), data_dicts)  # type: ignore

            logger.info(
                f"Successfully created table '{sanitized_table_name}' with {len(df)} rows and inferred column types"
            )
            return len(df)

        except Exception as e:
            logger.error(f"Error creating table from CSV: {str(e)}")
            raise Exception(f"Failed to create table: {str(e)}")

    def get_table_data(self, table_name: str, limit: int = 100) -> Dict[str, Any]:
        """
        Retrieve data from a PostgreSQL table.

        Args:
            table_name: Name of the table to query
            limit: Maximum number of rows to return

        Returns:
            dict: Table data with columns and rows
        """
        try:
            if not self.engine:
                raise Exception("Database engine not initialized")

            # Query the table
            query = text(f'SELECT * FROM "{table_name}" LIMIT :limit')

            with self.engine.connect() as conn:
                result = conn.execute(query, {"limit": limit})
                columns = list(result.keys())
                rows = [dict(row._mapping) for row in result]

            return {
                "table_name": table_name,
                "columns": columns,
                "rows": rows,
                "total_returned": len(rows),
            }

        except Exception as e:
            logger.error(f"Error fetching table data: {str(e)}")
            raise Exception(f"Failed to fetch table data: {str(e)}")

    def delete_table(self, table_name: str) -> bool:
        """
        Delete a PostgreSQL table.

        Args:
            table_name: Name of the table to delete

        Returns:
            bool: True if successful
        """
        try:
            if not self.engine:
                raise Exception("Database engine not initialized")

            # Drop the table
            query = text(f'DROP TABLE IF EXISTS "{table_name}"')

            with self.engine.begin() as conn:
                conn.execute(query)

            logger.info(f"Successfully deleted table '{table_name}'")
            return True

        except Exception as e:
            logger.error(f"Error deleting table: {str(e)}")
            raise Exception(f"Failed to delete table: {str(e)}")
