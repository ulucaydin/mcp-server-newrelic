"""
Error message sanitization to prevent information leakage

This module provides utilities to sanitize error messages before sending
them to clients, preventing exposure of sensitive internal details.
"""

import re
import logging
from typing import Union, Dict, Any, Optional, List
from enum import Enum

from .errors import (
    ValidationError, SecurityError, CacheError, ConfigurationError,
    PluginError, AuthenticationError, RateLimitError
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for sanitization"""
    PUBLIC = "public"       # Safe to expose to users
    INTERNAL = "internal"   # Should be sanitized
    SENSITIVE = "sensitive" # Must be completely hidden


class ErrorSanitizer:
    """Sanitizes error messages to prevent information leakage"""
    
    # Patterns that indicate sensitive information
    SENSITIVE_PATTERNS = [
        r'password[=:\s]\S+',
        r'token[=:\s]\S+',
        r'key[=:\s]\S+',
        r'secret[=:\s]\S+',
        r'NRAK-[A-Z0-9]{40}',  # New Relic API keys
        r'/[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+\.py',  # File paths
        r'line \d+',  # Line numbers
        r'Traceback \(most recent call last\):',  # Stack traces
        r'File "[^"]+", line \d+',  # Stack trace lines
        r'at 0x[0-9a-f]+',  # Memory addresses
        r'Connection refused|Connection timed out',  # Network details
        r'No such file or directory',  # File system details
        r'Permission denied',  # Permission details
    ]
    
    # Safe error categories that can be shown to users
    PUBLIC_ERROR_TYPES = {
        ValidationError: "Invalid input provided",
        SecurityError: "Security validation failed", 
        AuthenticationError: "Authentication failed",
        RateLimitError: "Rate limit exceeded",
        CacheError: "Cache operation failed",
        ConfigurationError: "Configuration error",
        PluginError: "Plugin operation failed"
    }
    
    # Generic messages for different error categories
    GENERIC_MESSAGES = {
        "validation": "Invalid input provided. Please check your parameters.",
        "security": "Security validation failed. Please review your request.",
        "authentication": "Authentication failed. Please check your credentials.",
        "authorization": "Access denied. Insufficient permissions.",
        "rate_limit": "Too many requests. Please wait before trying again.",
        "network": "Network error occurred. Please try again later.",
        "internal": "An internal error occurred. Please contact support.",
        "configuration": "Configuration error. Please check your settings.",
        "plugin": "Plugin error occurred. Please check plugin configuration.",
        "cache": "Cache operation failed. Please try again.",
        "database": "Database operation failed. Please try again later.",
        "external_api": "External service error. Please try again later."
    }
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize error sanitizer
        
        Args:
            debug_mode: If True, show more detailed errors (dev/staging only)
        """
        self.debug_mode = debug_mode
        
        # Compile regex patterns for performance
        self._sensitive_regex = re.compile(
            '|'.join(self.SENSITIVE_PATTERNS),
            re.IGNORECASE
        )
    
    def sanitize_error(
        self,
        error: Union[Exception, str],
        context: Optional[str] = None,
        error_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sanitize an error for client consumption
        
        Args:
            error: Exception or error message
            context: Additional context for the error
            error_id: Unique error ID for tracking
            
        Returns:
            Sanitized error response
        """
        
        # Handle different input types
        if isinstance(error, Exception):
            error_type = type(error).__name__
            error_message = str(error)
            is_public_error = type(error) in self.PUBLIC_ERROR_TYPES
        else:
            error_type = "Error"
            error_message = str(error)
            is_public_error = False
        
        # Determine sanitization level
        severity = self._classify_error_severity(error, error_message)
        
        # Create base response
        response = {
            "error": True,
            "error_type": error_type,
            "error_id": error_id,
            "context": context
        }
        
        # Sanitize message based on severity and debug mode
        if severity == ErrorSeverity.PUBLIC or (is_public_error and not self._contains_sensitive_info(error_message)):
            # Safe to show original message
            response["message"] = self._clean_message(error_message)
            response["details"] = self._extract_safe_details(error)
            
        elif severity == ErrorSeverity.INTERNAL and self.debug_mode:
            # Show detailed info in debug mode only
            response["message"] = self._clean_message(error_message)
            response["debug_info"] = {
                "original_error": error_message,
                "error_type": error_type
            }
            
        else:
            # Use generic message for sensitive errors
            response["message"] = self._get_generic_message(error, error_type)
            
            # Log actual error for internal tracking
            logger.error(
                f"Error sanitized (ID: {error_id}): {error_type}: {error_message}",
                extra={"error_id": error_id, "context": context}
            )
        
        return response
    
    def _classify_error_severity(
        self,
        error: Union[Exception, str],
        message: str
    ) -> ErrorSeverity:
        """Classify error severity level"""
        
        # Check if it's a known public error type
        if isinstance(error, Exception) and type(error) in self.PUBLIC_ERROR_TYPES:
            return ErrorSeverity.PUBLIC
        
        # Check for sensitive patterns
        if self._contains_sensitive_info(message):
            return ErrorSeverity.SENSITIVE
        
        # Default to internal
        return ErrorSeverity.INTERNAL
    
    def _contains_sensitive_info(self, message: str) -> bool:
        """Check if message contains sensitive information"""
        return bool(self._sensitive_regex.search(message))
    
    def _clean_message(self, message: str) -> str:
        """Clean message by removing sensitive patterns"""
        # Replace sensitive patterns with placeholders
        cleaned = self._sensitive_regex.sub('[REDACTED]', message)
        
        # Limit message length
        if len(cleaned) > 200:
            cleaned = cleaned[:197] + "..."
        
        return cleaned
    
    def _extract_safe_details(self, error: Union[Exception, str]) -> Optional[Dict[str, Any]]:
        """Extract safe details from error"""
        if not isinstance(error, Exception):
            return None
        
        details = {}
        
        # Add safe attributes based on error type
        if isinstance(error, ValidationError):
            if hasattr(error, 'field'):
                details['field'] = error.field
            if hasattr(error, 'value') and not self._contains_sensitive_info(str(error.value)):
                details['invalid_value'] = str(error.value)[:50]
        
        elif isinstance(error, RateLimitError):
            if hasattr(error, 'limit'):
                details['rate_limit'] = error.limit
            if hasattr(error, 'window'):
                details['window_seconds'] = error.window
        
        elif isinstance(error, AuthenticationError):
            details['help'] = "Please check your API key and permissions"
        
        return details if details else None
    
    def _get_generic_message(self, error: Union[Exception, str], error_type: str) -> str:
        """Get appropriate generic message for error"""
        
        # Map error types to categories
        if isinstance(error, Exception):
            error_class = type(error)
            if error_class in self.PUBLIC_ERROR_TYPES:
                return self.PUBLIC_ERROR_TYPES[error_class]
        
        # Use pattern matching for generic categories
        error_lower = error_type.lower()
        
        if 'validation' in error_lower or 'invalid' in error_lower:
            return self.GENERIC_MESSAGES["validation"]
        elif 'security' in error_lower or 'forbidden' in error_lower:
            return self.GENERIC_MESSAGES["security"]
        elif 'auth' in error_lower:
            return self.GENERIC_MESSAGES["authentication"]
        elif 'rate' in error_lower or 'limit' in error_lower:
            return self.GENERIC_MESSAGES["rate_limit"]
        elif 'network' in error_lower or 'connection' in error_lower:
            return self.GENERIC_MESSAGES["network"]
        elif 'config' in error_lower:
            return self.GENERIC_MESSAGES["configuration"]
        elif 'plugin' in error_lower:
            return self.GENERIC_MESSAGES["plugin"]
        elif 'cache' in error_lower:
            return self.GENERIC_MESSAGES["cache"]
        else:
            return self.GENERIC_MESSAGES["internal"]


class SafeErrorHandler:
    """Context manager for safe error handling"""
    
    def __init__(
        self,
        sanitizer: ErrorSanitizer,
        context: str,
        error_id: Optional[str] = None
    ):
        self.sanitizer = sanitizer
        self.context = context
        self.error_id = error_id
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value:
            # Sanitize and log the error
            sanitized = self.sanitizer.sanitize_error(
                exc_value, 
                self.context,
                self.error_id
            )
            
            # Store sanitized error for later retrieval
            self.sanitized_error = sanitized
            
            # Return True to suppress the exception
            return True
        return False


# Global sanitizer instance
_sanitizer = None

def get_error_sanitizer(debug_mode: bool = False) -> ErrorSanitizer:
    """Get global error sanitizer instance"""
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = ErrorSanitizer(debug_mode=debug_mode)
    return _sanitizer


def sanitize_error_response(
    error: Union[Exception, str],
    context: Optional[str] = None,
    error_id: Optional[str] = None,
    debug_mode: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to sanitize error responses
    
    Args:
        error: Exception or error message
        context: Additional context
        error_id: Unique error ID
        debug_mode: Whether to include debug info
        
    Returns:
        Sanitized error response
    """
    sanitizer = get_error_sanitizer(debug_mode=debug_mode)
    return sanitizer.sanitize_error(error, context, error_id)


# Example usage:
"""
try:
    # Some operation that might fail
    result = dangerous_operation()
except Exception as e:
    # Sanitize error before returning to client
    error_response = sanitize_error_response(
        error=e,
        context="user_operation",
        error_id="REQ-12345",
        debug_mode=os.getenv("DEBUG_MODE") == "true"
    )
    return {"success": False, **error_response}

# Or using context manager:
with SafeErrorHandler(get_error_sanitizer(), "api_call", "REQ-12345") as handler:
    result = risky_api_call()
    
if hasattr(handler, 'sanitized_error'):
    return {"success": False, **handler.sanitized_error}
"""