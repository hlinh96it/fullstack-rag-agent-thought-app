"""Common response formatters for API endpoints."""

from typing import Any, Dict, List, Optional


class ResponseFormatter:
    """Standardized response formats for API endpoints."""

    @staticmethod
    def success(
        message: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Format a successful response.

        Args:
            message: Success message
            data: Optional data payload
            **kwargs: Additional fields to include

        Returns:
            Formatted response dictionary
        """
        response = {"message": message, "status": "success"}
        if data:
            response.update(data)
        if kwargs:
            response.update(kwargs)
        return response

    @staticmethod
    def list_response(
        items: List[Any],
        total: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Format a list response with metadata.

        Args:
            items: List of items
            total: Optional total count
            **kwargs: Additional metadata

        Returns:
            Formatted list response
        """
        response = {
            "items": items,
            "count": len(items),
        }
        if total is not None:
            response["total"] = total
        if kwargs:
            response.update(kwargs)
        return response

    @staticmethod
    def error(message: str, details: Optional[str] = None) -> Dict[str, Any]:
        """
        Format an error response.

        Args:
            message: Error message
            details: Optional error details

        Returns:
            Formatted error response
        """
        response = {"message": message, "status": "error"}
        if details:
            response["details"] = details
        return response
