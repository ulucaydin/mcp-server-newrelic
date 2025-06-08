"""
Standardized error handling and error codes for the MCP server
"""

from enum import Enum
from typing import Optional, Dict, Any, Union
import json
import traceback
import logging

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for the MCP server"""
    
    # General errors (1000-1999)
    UNKNOWN_ERROR = 1000
    INTERNAL_ERROR = 1001
    NOT_IMPLEMENTED = 1002
    SERVICE_UNAVAILABLE = 1003
    
    # Authentication/Authorization errors (2000-2999)
    AUTHENTICATION_FAILED = 2001
    INVALID_API_KEY = 2002
    PERMISSION_DENIED = 2003
    ACCOUNT_NOT_FOUND = 2004
    SESSION_EXPIRED = 2005
    
    # Validation errors (3000-3999)
    INVALID_INPUT = 3001
    MISSING_REQUIRED_FIELD = 3002
    INVALID_FORMAT = 3003
    VALUE_OUT_OF_RANGE = 3004
    INVALID_NRQL_QUERY = 3005
    INVALID_TIME_RANGE = 3006
    INVALID_GUID = 3007
    
    # Resource errors (4000-4999)
    RESOURCE_NOT_FOUND = 4001
    ENTITY_NOT_FOUND = 4002
    METRIC_NOT_FOUND = 4003
    APPLICATION_NOT_FOUND = 4004
    
    # Rate limiting errors (5000-5999)
    RATE_LIMIT_EXCEEDED = 5001
    QUERY_TOO_COMPLEX = 5002
    RESULT_SET_TOO_LARGE = 5003
    
    # External service errors (6000-6999)
    NERDGRAPH_ERROR = 6001
    NERDGRAPH_TIMEOUT = 6002
    NERDGRAPH_INVALID_RESPONSE = 6003
    
    # Security errors (7000-7999)
    SECURITY_VIOLATION = 7001
    NRQL_INJECTION_DETECTED = 7002
    INVALID_ENCRYPTION = 7003


class MCPError(Exception):
    """Base exception for MCP server errors"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize MCP error
        
        Args:
            code: Error code
            message: Human-readable error message
            details: Additional error details
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format"""
        error_dict = {
            "error": {
                "code": self.code.value,
                "name": self.code.name,
                "message": self.message,
                "details": self.details
            }
        }
        
        # Add cause information if available
        if self.cause:
            error_dict["error"]["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause)
            }
        
        return error_dict
    
    def to_json(self) -> str:
        """Convert error to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


# Specific error classes
class ValidationError(MCPError):
    """Input validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, cause: Optional[Exception] = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)[:100]  # Truncate long values
        
        super().__init__(
            ErrorCode.INVALID_INPUT,
            message,
            details,
            cause
        )


class AuthenticationError(MCPError):
    """Authentication/authorization errors"""
    
    def __init__(self, message: str = "Authentication failed", 
                 cause: Optional[Exception] = None):
        super().__init__(
            ErrorCode.AUTHENTICATION_FAILED,
            message,
            cause=cause
        )


class RateLimitError(MCPError):
    """Rate limiting errors"""
    
    def __init__(self, message: str = "Rate limit exceeded", 
                 reset_time: Optional[float] = None,
                 limit: Optional[int] = None):
        details = {}
        if reset_time:
            details["reset_time"] = reset_time
        if limit:
            details["limit"] = limit
        
        super().__init__(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            message,
            details
        )


class NerdGraphError(MCPError):
    """NerdGraph API errors"""
    
    def __init__(self, message: str, graphql_errors: Optional[list] = None,
                 query: Optional[str] = None):
        details = {}
        if graphql_errors:
            details["graphql_errors"] = graphql_errors
        if query:
            details["query"] = query[:500]  # Truncate long queries
        
        super().__init__(
            ErrorCode.NERDGRAPH_ERROR,
            message,
            details
        )


class SecurityError(MCPError):
    """Security-related errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.SECURITY_VIOLATION):
        super().__init__(
            error_code,
            message
        )


class ErrorHandler:
    """Centralized error handling utilities"""
    
    @staticmethod
    def handle_error(error: Exception) -> Dict[str, Any]:
        """
        Convert any exception to a standardized error response
        
        Args:
            error: Exception to handle
            
        Returns:
            Standardized error dictionary
        """
        if isinstance(error, MCPError):
            return error.to_dict()
        
        # Handle specific exception types
        if isinstance(error, ValueError):
            return ValidationError(str(error)).to_dict()
        
        if isinstance(error, KeyError):
            return MCPError(
                ErrorCode.MISSING_REQUIRED_FIELD,
                f"Missing required field: {error}"
            ).to_dict()
        
        if isinstance(error, TimeoutError):
            return MCPError(
                ErrorCode.SERVICE_UNAVAILABLE,
                "Request timed out"
            ).to_dict()
        
        # Log unexpected errors
        logger.error(f"Unexpected error: {error}", exc_info=True)
        
        # Generic error response
        return MCPError(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred",
            {"type": type(error).__name__}
        ).to_dict()
    
    @staticmethod
    def wrap_tool_errors(func):
        """
        Decorator to wrap tool functions with error handling
        
        Usage:
            @ErrorHandler.wrap_tool_errors
            async def my_tool(param: str) -> Dict[str, Any]:
                # Tool implementation
        """
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_response = ErrorHandler.handle_error(e)
                
                # Log the error with context
                logger.error(
                    f"Error in tool {func.__name__}: {e}",
                    extra={
                        "tool": func.__name__,
                        "args": args,
                        "kwargs": kwargs,
                        "error": error_response
                    }
                )
                
                # Return error as JSON string for consistency
                return json.dumps(error_response)
        
        return wrapper
    
    @staticmethod
    def format_nerdgraph_errors(errors: list) -> str:
        """
        Format NerdGraph errors into a readable message
        
        Args:
            errors: List of GraphQL errors
            
        Returns:
            Formatted error message
        """
        if not errors:
            return "Unknown NerdGraph error"
        
        messages = []
        for error in errors:
            if isinstance(error, dict):
                message = error.get('message', 'Unknown error')
                path = error.get('path', [])
                if path:
                    message += f" (at {'.'.join(map(str, path))})"
                messages.append(message)
            else:
                messages.append(str(error))
        
        return "; ".join(messages)


class ErrorContext:
    """Context manager for error handling with additional context"""
    
    def __init__(self, operation: str, **context):
        """
        Initialize error context
        
        Args:
            operation: Description of the operation
            **context: Additional context information
        """
        self.operation = operation
        self.context = context
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            # Add context to the error
            logger.error(
                f"Error during {self.operation}",
                exc_info=True,
                extra={"context": self.context}
            )
            
            # Re-raise with context if it's an MCPError
            if isinstance(exc_val, MCPError):
                exc_val.details.update(self.context)
            
            # Don't suppress the exception
            return False