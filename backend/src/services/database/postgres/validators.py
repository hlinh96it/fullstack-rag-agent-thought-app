"""CSV validation utilities."""

import csv
import io
from typing import Tuple, List
from fastapi import UploadFile, HTTPException

import logging

logger = logging.getLogger(__name__)


class CSVValidator:
    """Validates CSV files and extracts data."""

    @staticmethod
    async def validate_and_parse_csv(
        file: UploadFile,
    ) -> Tuple[List[str], List[List[str]]]:
        """
        Validate and parse a CSV file.

        Args:
            file: Uploaded CSV file

        Returns:
            Tuple of (headers, rows)

        Raises:
            HTTPException: If validation fails
        """
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed")

        # Read and parse CSV
        contents = await file.read()
        csv_data = io.StringIO(contents.decode("utf-8"))

        csv_reader = csv.reader(csv_data)
        headers = next(csv_reader)
        rows = list(csv_reader)

        if not headers or not rows:
            raise HTTPException(
                status_code=400, detail="CSV file is empty or has no data"
            )

        return headers, rows

    @staticmethod
    def sanitize_table_name(table_name: str) -> str:
        """
        Sanitize table name for PostgreSQL.

        Args:
            table_name: Original table name

        Returns:
            Sanitized table name
        """
        return "".join(
            c if c.isalnum() or c == "_" else "_" for c in table_name.lower()
        )
