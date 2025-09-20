"""
Base service class providing common functionality for all services.
"""

from abc import ABC
from typing import Optional, Any, Dict
from ..core.config import get_settings
from ..core.logging import get_logger


class BaseService(ABC):
    """
    Base class for all services providing common initialization and utilities.
    
    Eliminates the repetitive patterns found across services:
    - Logger initialization
    - Settings loading
    - Common utility methods
    """
    
    def __init__(self, service_name: Optional[str] = None):
        """
        Initialize base service with common patterns.
        
        Args:
            service_name: Optional service name for logging. 
                         Defaults to class name if not provided.
        """
        # Set up logging with consistent naming
        self.service_name = service_name or self.__class__.__name__
        self.logger = get_logger(f"services.{self.service_name.lower()}")
        
        # Load settings (used by 4+ services)
        self.settings = get_settings()
        
        # Log initialization
        self.logger.info(f"{self.service_name} initialized")
    
    def log_operation_start(self, operation: str, **kwargs) -> None:
        """Log the start of an operation with context."""
        context = " | ".join([f"{k}={v}" for k, v in kwargs.items()]) if kwargs else ""
        self.logger.debug(f"Starting {operation}" + (f" | {context}" if context else ""))
    
    def log_operation_success(self, operation: str, result_info: str = "") -> None:
        """Log successful completion of an operation."""
        self.logger.debug(f"Completed {operation}" + (f" | {result_info}" if result_info else ""))
    
    def log_operation_error(self, operation: str, error: Exception) -> None:
        """Log operation failure with error details."""
        self.logger.error(f"Failed {operation}: {str(error)}")
    
    def validate_required_settings(self, *setting_names: str) -> None:
        """
        Validate that required settings are present.
        
        Args:
            *setting_names: Names of settings attributes to check
            
        Raises:
            ValueError: If any required setting is missing
        """
        missing = []
        for setting_name in setting_names:
            value = getattr(self.settings, setting_name, None)
            if not value:
                missing.append(setting_name)
        
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")


class DatabaseMixin:
    """Mixin for services that need database access patterns."""
    
    def safe_database_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Execute database operation with consistent error handling.
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: The database operation function to execute
            *args, **kwargs: Arguments to pass to the operation function
            
        Returns:
            Operation result or None if failed
        """
        try:
            self.log_operation_start(operation_name, **kwargs)
            result = operation_func(*args, **kwargs)
            self.log_operation_success(operation_name, f"result_type={type(result).__name__}")
            return result
        except Exception as e:
            self.log_operation_error(operation_name, e)
            return None


class LLMMixin:
    """Mixin for services that interact with LLM providers."""
    
    def validate_llm_response(self, response: Any, expected_type: type = dict) -> bool:
        """
        Validate LLM response structure.
        
        Args:
            response: The LLM response to validate
            expected_type: Expected type of the response
            
        Returns:
            True if response is valid, False otherwise
        """
        if response is None:
            self.logger.warning("LLM returned None response")
            return False
        
        if not isinstance(response, expected_type):
            self.logger.warning(f"LLM response type mismatch: expected {expected_type}, got {type(response)}")
            return False
        
        return True
    
    def create_llm_fallback_response(self, operation: str) -> Dict[str, Any]:
        """
        Create a safe fallback response for LLM operations.
        
        Args:
            operation: Name of the operation that failed
            
        Returns:
            Safe fallback response
        """
        self.logger.warning(f"Using fallback response for {operation}")
        return {
            "success": False,
            "error": f"LLM operation failed: {operation}",
            "fallback": True
        }


class ValidationMixin:
    """Mixin for services that need validation patterns."""
    
    def validate_and_log(self, data: Any, validation_func, operation: str) -> tuple[bool, Any]:
        """
        Validate data with consistent logging.
        
        Args:
            data: Data to validate
            validation_func: Function to perform validation
            operation: Operation name for logging
            
        Returns:
            Tuple of (is_valid, validated_data)
        """
        try:
            self.log_operation_start(f"validate_{operation}")
            validated_data = validation_func(data)
            self.log_operation_success(f"validate_{operation}")
            return True, validated_data
        except Exception as e:
            self.log_operation_error(f"validate_{operation}", e)
            return False, None
