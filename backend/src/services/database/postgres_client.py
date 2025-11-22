from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, inspect, text, URL
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config import Settings
from src.services.database.postgres_utils import DatabaseManager, TableManager

import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class PostgreSQLDBClient:
    """PostgreSQL database implementation for data analytics"""

    def __init__(self, settings: Settings):
        self.settings = settings.postgres_db
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None

        # Initialize utility managers
        self.database_manager: Optional[DatabaseManager] = None
        self.table_manager: Optional[TableManager] = None

        self.startup()

    def startup(self) -> None:
        """Initialize the database connection."""
        try:
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
                pool_pre_ping=True,
            )
            self.session_factory = sessionmaker(
                bind=self.engine, expire_on_commit=False
            )

            # Test connection
            assert self.engine is not None
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("👌  Database connection test successfully")

            # Check table exists
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            Base.metadata.create_all(bind=self.engine)

            update_tables = inspector.get_table_names()
            new_tables = set(update_tables) - set(existing_tables)

            if new_tables:
                logger.info(f"🍽️  Create new tables: {', '.join(new_tables)}")
            else:
                logger.info("All tables already exist")

            # Initialize managers with settings and engine
            self.database_manager = DatabaseManager(Settings())
            self.table_manager = TableManager(Settings(), self.engine)

            logger.info("👌  PostgreSQL database initilized sucessfully")

        except Exception as e:
            logger.error(f"❌  Failed to initialize PostgreSQL database: {e}")

    # Delegate database operations to DatabaseManager
    def create_database(self, database_name: str) -> bool:
        """Create a new PostgreSQL database."""
        assert self.database_manager is not None
        return self.database_manager.create_database(database_name)

    def list_databases(self) -> List[Dict[str, Any]]:
        """List all PostgreSQL databases."""
        assert self.database_manager is not None
        return self.database_manager.list_databases()

    def delete_database(self, database_name: str) -> bool:
        """Delete a PostgreSQL database."""
        assert self.database_manager is not None
        return self.database_manager.delete_database(database_name)

    def get_all_user_databases(self) -> List[str]:
        """Get all non-system databases."""
        assert self.database_manager is not None
        return self.database_manager.get_all_user_databases()

    # Delegate table operations to TableManager
    def create_table_from_csv(
        self,
        table_name: str,
        headers: List[str],
        rows: List[List[str]],
        database_name: Optional[str] = None,
    ) -> int:
        """Create a new table from CSV data."""
        assert self.table_manager is not None
        return self.table_manager.create_table_from_csv(
            table_name, headers, rows, database_name
        )

    def get_table_data(
        self, table_name: str, limit: int = 100, database_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve data from a PostgreSQL table."""
        assert self.table_manager is not None
        return self.table_manager.get_table_data(table_name, limit, database_name)

    def delete_table(self, table_name: str) -> bool:
        """Delete a PostgreSQL table."""
        assert self.table_manager is not None
        return self.table_manager.delete_table(table_name)

    def get_tables_in_database(self, database_name: str) -> List[Dict[str, Any]]:
        """Get all tables in a specific database."""
        assert self.table_manager is not None
        return self.table_manager.get_tables_in_database(database_name)
