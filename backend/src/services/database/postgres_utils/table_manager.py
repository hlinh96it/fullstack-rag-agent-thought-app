"""Table-level operations for PostgreSQL."""

from typing import List, Dict, Any, Optional, cast
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
    MetaData,
)

from src.config import Settings
from .type_mapper import TypeMapper

import logging

logger = logging.getLogger(__name__)


class TableManager:
    """Manages table-level operations."""

    def __init__(self, settings: Settings, engine):
        self.settings = settings.postgres_db
        self.engine = engine
        self.type_mapper = TypeMapper()

    def create_table_from_csv(
        self,
        table_name: str,
        headers: List[str],
        rows: List[List[str]],
        database_name: Optional[str] = None,
    ) -> int:
        """
        Create a new table from CSV data using pandas type inference.

        Args:
            table_name: Name of the table to create
            headers: List of column names
            rows: List of data rows
            database_name: Optional database name

        Returns:
            int: Number of rows inserted
        """
        try:
            # Use specified database or default
            engine_to_use = self._get_engine(database_name)

            # Create DataFrame for type inference
            df = pd.DataFrame(rows, columns=headers)
            df = df.convert_dtypes()

            # Sanitize names
            sanitized_table_name = self.type_mapper.sanitize_name(table_name)
            column_mapping = {
                col: self.type_mapper.sanitize_name(col) for col in headers
            }
            df.rename(columns=column_mapping, inplace=True)

            # Create table with auto-detected types
            metadata = MetaData()
            columns = [Column("id", Integer, primary_key=True, autoincrement=True)]

            for col_name in df.columns:
                col_type = self.type_mapper.pandas_dtype_to_sqlalchemy(
                    df[col_name].dtype
                )
                columns.append(Column(col_name, col_type))

            table = Table(
                sanitized_table_name, metadata, *columns, extend_existing=True
            )

            # Drop and create table
            with engine_to_use.begin() as conn:
                metadata.drop_all(conn, tables=[table], checkfirst=True)
                metadata.create_all(conn, tables=[table])

            # Insert data
            if not df.empty:
                df = df.replace({np.nan: None})
                data_dicts = cast(List[Dict[str, Any]], df.to_dict(orient="records"))

                with engine_to_use.begin() as conn:
                    conn.execute(table.insert(), data_dicts)

            # Cleanup temporary engine
            if database_name and engine_to_use != self.engine:
                engine_to_use.dispose()

            logger.info(
                f"Successfully created table '{sanitized_table_name}' with {len(df)} rows"
            )
            return len(df)

        except Exception as e:
            logger.error(f"Error creating table from CSV: {str(e)}")
            raise Exception(f"Failed to create table: {str(e)}")

    def get_table_data(
        self, table_name: str, limit: int = 100, database_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve data from a table.

        Args:
            table_name: Table name
            limit: Maximum rows
            database_name: Optional database name

        Returns:
            dict: Table data with columns and rows
        """
        try:
            engine_to_use = self._get_engine(database_name)

            query = text(f'SELECT * FROM "{table_name}" LIMIT :limit')

            with engine_to_use.connect() as conn:
                result = conn.execute(query, {"limit": limit})
                columns = list(result.keys())
                rows = [dict(row._mapping) for row in result]

            if database_name and engine_to_use != self.engine:
                engine_to_use.dispose()

            return {
                "table_name": table_name,
                "database_name": database_name or self.settings.database_name,
                "columns": columns,
                "rows": rows,
                "total_returned": len(rows),
            }

        except Exception as e:
            logger.error(f"Error fetching table data: {str(e)}")
            raise Exception(f"Failed to fetch table data: {str(e)}")

    def delete_table(self, table_name: str) -> bool:
        """
        Delete a table.

        Args:
            table_name: Table name

        Returns:
            bool: True if successful
        """
        try:
            if not self.engine:
                raise Exception("Database engine not initialized")

            query = text(f'DROP TABLE IF EXISTS "{table_name}"')

            with self.engine.begin() as conn:
                conn.execute(query)

            logger.info(f"Successfully deleted table '{table_name}'")
            return True

        except Exception as e:
            logger.error(f"Error deleting table: {str(e)}")
            raise Exception(f"Failed to delete table: {str(e)}")

    def get_tables_in_database(self, database_name: str) -> List[Dict[str, Any]]:
        """
        Get all tables in a specific database.

        Args:
            database_name: Database name

        Returns:
            List of table information
        """
        try:
            url = URL.create(
                drivername=self.settings.driver_name,
                username=self.settings.username,
                password=self.settings.password,
                host=self.settings.host,
                port=self.settings.port,
                database=database_name,
            )
            engine = create_engine(url, pool_pre_ping=True)

            tables_info = []

            with engine.connect() as conn:
                inspector = inspect(engine)
                table_names = inspector.get_table_names()

                for table_name in table_names:
                    columns = inspector.get_columns(table_name)
                    column_names = [col["name"] for col in columns]

                    result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                    row_count = result.scalar()

                    tables_info.append(
                        {
                            "table_name": table_name,
                            "columns": column_names,
                            "column_count": len(column_names),
                            "row_count": row_count,
                        }
                    )

            engine.dispose()
            return tables_info

        except Exception as e:
            logger.error(
                f"Error getting tables from database '{database_name}': {str(e)}"
            )
            return []

    def _get_engine(self, database_name: Optional[str] = None):
        """Get engine for specific database or use default."""
        if database_name:
            url = URL.create(
                drivername=self.settings.driver_name,
                username=self.settings.username,
                password=self.settings.password,
                host=self.settings.host,
                port=self.settings.port,
                database=database_name,
            )
            return create_engine(
                url,
                echo=False,
                pool_size=self.settings.pool_size,
                max_overflow=self.settings.max_overflow,
                pool_pre_ping=True,
            )
        return self.engine
