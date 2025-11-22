"""Type mapping utilities for PostgreSQL."""

import pandas as pd
from sqlalchemy import Integer, Float, Boolean, DateTime, Text, String

import logging

logger = logging.getLogger(__name__)


class TypeMapper:
    """Handles type mapping between pandas and SQLAlchemy."""

    @staticmethod
    def pandas_dtype_to_sqlalchemy(dtype) -> type:
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
            return Text
        else:
            return String

    @staticmethod
    def sanitize_name(name: str) -> str:
        """
        Sanitize table or column names for PostgreSQL.

        Args:
            name: Original name

        Returns:
            Sanitized name
        """
        sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name.lower())
        # Ensure it starts with a letter or underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = f"col_{sanitized}"
        return sanitized or "unnamed"
