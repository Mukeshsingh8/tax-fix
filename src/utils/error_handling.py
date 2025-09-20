"""
Error handling utilities for agents.
"""

import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from functools import wraps


def create_error_response(
    content: str,
    confidence: float = 0.0,
    reasoning: Optional[str] = None,
    fallback_content: str = "I encountered an error. Please try again."
) -> Dict[str, Any]:
    """Create standardized error response data."""
    return {
        "content": content or fallback_content,
        "confidence": confidence,
        "reasoning": reasoning or "Error occurred during processing",
    }


def safe_agent_method(
    fallback_content: str = "I encountered an error. Please try again.",
    fallback_confidence: float = 0.0,
    log_errors: bool = True
):
    """
    Decorator to handle errors in agent methods with consistent error responses.
    
    Args:
        fallback_content: Default error message to show user
        fallback_confidence: Confidence level for error responses
        log_errors: Whether to log the error details
    """
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                if log_errors and hasattr(self, 'logger'):
                    self.logger.error(f"Error in {func.__name__}: {e}")
                
                # Create standardized error response
                if hasattr(self, 'create_response'):
                    return await self.create_response(
                        content=fallback_content,
                        confidence=fallback_confidence,
                        reasoning=f"Error in {func.__name__}: {str(e)}"
                    )
                else:
                    # Fallback for non-agent classes
                    return create_error_response(
                        content=fallback_content,
                        confidence=fallback_confidence,
                        reasoning=f"Error in {func.__name__}: {str(e)}"
                    )
        return wrapper
    return decorator


async def safe_execute(
    operation: Callable[..., Awaitable[Any]],
    *args,
    fallback_result: Any = None,
    logger: Optional[logging.Logger] = None,
    operation_name: str = "operation",
    **kwargs
) -> Any:
    """
    Safely execute an async operation with error handling.
    
    Args:
        operation: The async function to execute
        *args: Positional arguments for the operation
        fallback_result: Value to return if operation fails
        logger: Logger instance for error reporting
        operation_name: Name for logging purposes
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Operation result or fallback_result if it fails
    """
    try:
        return await operation(*args, **kwargs)
    except Exception as e:
        if logger:
            logger.error(f"Error in {operation_name}: {e}")
        return fallback_result
