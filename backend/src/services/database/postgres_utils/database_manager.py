"""Database-level operations for PostgreSQL."""

from typing import List, Dict, Any
from sqlalchemy import create_engine, text, URL

from src.config import Settings
from .type_mapper import TypeMapper

import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database-level operations."""

    def __init__(self, settings: Settings):
        self.settings = settings.postgres_db
        self.type_mapper = TypeMapper()

    def create_database(self, database_name: str) -> bool:
        """
        Create a new PostgreSQL database.

        Args:
            database_name: Name of the database to create

        Returns:
            bool: True if successful
        """
        try:
            # Sanitize database name
            sanitized_db_name = self.type_mapper.sanitize_name(database_name)

            # Create connection to postgres database (default database)
            url = URL.create(
                drivername=self.settings.driver_name,
                username=self.settings.username,
                password=self.settings.password,
                host=self.settings.host,
                port=self.settings.port,
                database="postgres",
            )
            engine = create_engine(url, isolation_level="AUTOCOMMIT")

            # Check if database exists
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": sanitized_db_name},
                )
                exists = result.fetchone() is not None

                if exists:
                    logger.warning(f"Database '{sanitized_db_name}' already exists")
                    raise Exception(f"Database '{sanitized_db_name}' already exists")

                # Create database
                conn.execute(text(f'CREATE DATABASE "{sanitized_db_name}"'))

            logger.info(f"Successfully created database '{sanitized_db_name}'")
            engine.dispose()
            return True

        except Exception as e:
            logger.error(f"Error creating database: {str(e)}")
            raise Exception(f"Failed to create database: {str(e)}")

    def list_databases(self) -> List[Dict[str, Any]]:
        """
        List all PostgreSQL databases accessible to the current user.

        Returns:
            List[Dict[str, Any]]: List of databases with their details
        """
        try:
            url = URL.create(
                drivername=self.settings.driver_name,
                username=self.settings.username,
                password=self.settings.password,
                host=self.settings.host,
                port=self.settings.port,
                database="postgres",
            )
            engine = create_engine(url)

            with engine.connect() as conn:
                query = text(
                    """
                    SELECT 
                        datname as name,
                        pg_database_size(datname) as size_bytes,
                        pg_size_pretty(pg_database_size(datname)) as size
                    FROM pg_database
                    WHERE datistemplate = false
                    ORDER BY datname
                """
                )
                result = conn.execute(query)
                databases = [dict(row._mapping) for row in result]

            engine.dispose()
            logger.info(f"Found {len(databases)} databases")
            return databases

        except Exception as e:
            logger.error(f"Error listing databases: {str(e)}")
            raise Exception(f"Failed to list databases: {str(e)}")

    def delete_database(self, database_name: str) -> bool:
        """
        Delete a PostgreSQL database.

        Args:
            database_name: Name of the database to delete

        Returns:
            bool: True if successful
        """
        try:
            sanitized_db_name = self.type_mapper.sanitize_name(database_name)

            # Prevent deletion of system databases
            protected_dbs = ["postgres", "template0", "template1"]
            if sanitized_db_name in protected_dbs:
                raise Exception(f"Cannot delete system database '{sanitized_db_name}'")

            url = URL.create(
                drivername=self.settings.driver_name,
                username=self.settings.username,
                password=self.settings.password,
                host=self.settings.host,
                port=self.settings.port,
                database="postgres",
            )
            engine = create_engine(url, isolation_level="AUTOCOMMIT")

            with engine.connect() as conn:
                # Terminate existing connections
                conn.execute(
                    text(
                        """
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = :db_name
                        AND pid <> pg_backend_pid()
                    """
                    ),
                    {"db_name": sanitized_db_name},
                )

                # Drop database
                conn.execute(text(f'DROP DATABASE IF EXISTS "{sanitized_db_name}"'))

            logger.info(f"Successfully deleted database '{sanitized_db_name}'")
            engine.dispose()
            return True

        except Exception as e:
            logger.error(f"Error deleting database: {str(e)}")
            raise Exception(f"Failed to delete database: {str(e)}")

    def get_all_user_databases(self) -> List[str]:
        """
        Get all non-system databases.

        Returns:
            List of database names
        """
        try:
            url = URL.create(
                drivername=self.settings.driver_name,
                username=self.settings.username,
                password=self.settings.password,
                host=self.settings.host,
                port=self.settings.port,
                database="postgres",
            )
            engine = create_engine(url)

            with engine.connect() as conn:
                query = text(
                    """
                    SELECT datname
                    FROM pg_database
                    WHERE datistemplate = false
                    AND datname NOT IN ('postgres', 'template0', 'template1')
                    ORDER BY datname
                """
                )
                result = conn.execute(query)
                databases = [row[0] for row in result]

            engine.dispose()
            return databases

        except Exception as e:
            logger.error(f"Error getting user databases: {str(e)}")
            return []
