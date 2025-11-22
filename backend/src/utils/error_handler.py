"""Common error handling utilities."""

from typing import Callable, Any, Optional
from functools import wraps
from fastapi import HTTPException

import logging

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Common error handling patterns for services and routers."""

    @staticmethod
    def handle_service_error(operation_name: str):
        """
        Decorator for handling service-level errors with consistent logging and HTTP exceptions.

        Args:
            operation_name: Name of the operation for logging and error messages

        Usage:
            @ErrorHandler.handle_service_error("create_table")
            async def create_table(...):
                ...
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                try:
                    return await func(*args, **kwargs)
                except HTTPException:
                    # Re-raise HTTP exceptions as-is
                    raise
                except Exception as e:
                    logger.error(f"Error in {operation_name}: {str(e)}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to {operation_name}: {str(e)}",
                    )

            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                try:
                    return func(*args, **kwargs)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Error in {operation_name}: {str(e)}", exc_info=True)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to {operation_name}: {str(e)}",
                    )

            # Return appropriate wrapper based on function type
            import inspect

            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    @staticmethod
    def log_operation(operation_name: str, user_id: Optional[str] = None, **kwargs):
        """
        Log operation start with contextual information.

        Args:
            operation_name: Name of the operation
            user_id: Optional user ID
            **kwargs: Additional context to log
        """
        context = f"user={user_id}" if user_id else ""
        extra_context = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        full_context = f"{context}, {extra_context}" if extra_context else context

        logger.info(f"🔄 Starting {operation_name} [{full_context}]")

    @staticmethod
    def log_success(operation_name: str, **kwargs):
        """
        Log successful operation completion.

        Args:
            operation_name: Name of the operation
            **kwargs: Additional context to log
        """
        context = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info(f"✅ Completed {operation_name} [{context}]")
