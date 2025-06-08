"""
Tests for error message sanitization
"""

import pytest
import os
from unittest.mock import Mock, patch

from core.error_sanitizer import (
    ErrorSanitizer, SafeErrorHandler, ErrorSeverity,
    sanitize_error_response, get_error_sanitizer
)
from core.errors import (
    ValidationError, SecurityError, AuthenticationError,
    RateLimitError, CacheError
)


class TestErrorSanitizer:
    """Test error sanitization functionality"""
    
    def test_public_error_not_sanitized(self):
        """Test that public errors are not sanitized"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        error = ValidationError("Invalid email format")
        result = sanitizer.sanitize_error(error)
        
        assert result["error"] is True
        assert result["message"] == "Invalid email format"
        assert result["error_type"] == "ValidationError"
    
    def test_sensitive_api_key_redacted(self):
        """Test that API keys are redacted from error messages"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        error = Exception("Failed to connect with key NRAK-1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ1234")
        result = sanitizer.sanitize_error(error)
        
        assert "[REDACTED]" in result["message"]
        assert "NRAK-" not in result["message"]
    
    def test_file_paths_redacted(self):
        """Test that file paths are redacted"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        error = Exception("File not found: /etc/passwd")
        result = sanitizer.sanitize_error(error)
        
        assert "[REDACTED]" in result["message"]
        assert "/etc/passwd" not in result["message"]
    
    def test_stack_traces_redacted(self):
        """Test that stack trace information is redacted"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        error_msg = """Traceback (most recent call last):
  File "/app/core/client.py", line 42, in query
    response = self.session.post(url)
ValueError: Invalid URL"""
        
        result = sanitizer.sanitize_error(error_msg)
        
        assert "Traceback" not in result["message"]
        assert "/app/core/client.py" not in result["message"]
        assert "line 42" not in result["message"]
    
    def test_debug_mode_shows_details(self):
        """Test that debug mode shows more details"""
        sanitizer = ErrorSanitizer(debug_mode=True)
        
        error = Exception("Internal processing error")
        result = sanitizer.sanitize_error(error, error_id="TEST-123")
        
        assert "debug_info" in result
        assert result["debug_info"]["original_error"] == "Internal processing error"
    
    def test_production_mode_hides_details(self):
        """Test that production mode hides internal details"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        error = Exception("Database connection failed: host 'secret-db' unreachable")
        result = sanitizer.sanitize_error(error)
        
        # Should get generic message, not specific database details
        assert "An internal error occurred" in result["message"]
        assert "secret-db" not in result["message"]
    
    def test_validation_error_details_preserved(self):
        """Test that validation error details are safely preserved"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        # Create validation error with safe field info
        error = ValidationError("Invalid email format")
        error.field = "email"
        error.value = "not-an-email"
        
        result = sanitizer.sanitize_error(error)
        
        assert result["details"]["field"] == "email"
        assert result["details"]["invalid_value"] == "not-an-email"
    
    def test_validation_error_sensitive_value_redacted(self):
        """Test that sensitive values in validation errors are redacted"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        # Create validation error with sensitive value
        error = ValidationError("Invalid API key")
        error.field = "api_key"
        error.value = "NRAK-SECRET123456789"
        
        result = sanitizer.sanitize_error(error)
        
        assert result["details"]["field"] == "api_key"
        # Sensitive value should not be included
        assert "invalid_value" not in result["details"]
    
    def test_rate_limit_error_details(self):
        """Test that rate limit error details are included"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        error = RateLimitError("Rate limit exceeded")
        error.limit = 100
        error.window = 60
        
        result = sanitizer.sanitize_error(error)
        
        assert result["details"]["rate_limit"] == 100
        assert result["details"]["window_seconds"] == 60
    
    def test_authentication_error_helpful_message(self):
        """Test that authentication errors include helpful info"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        error = AuthenticationError("Invalid credentials")
        result = sanitizer.sanitize_error(error)
        
        assert result["details"]["help"] == "Please check your API key and permissions"
    
    def test_message_length_limit(self):
        """Test that long messages are truncated"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        long_message = "Error: " + "x" * 300
        error = ValidationError(long_message)
        
        result = sanitizer.sanitize_error(error)
        
        assert len(result["message"]) <= 200
        assert result["message"].endswith("...")
    
    def test_context_and_error_id_preserved(self):
        """Test that context and error ID are preserved"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        error = ValidationError("Test error")
        result = sanitizer.sanitize_error(
            error, 
            context="test_operation", 
            error_id="ERR-12345"
        )
        
        assert result["context"] == "test_operation"
        assert result["error_id"] == "ERR-12345"
    
    def test_generic_message_mapping(self):
        """Test that error types map to appropriate generic messages"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        test_cases = [
            (Exception("NetworkError: Connection failed"), "Network error occurred"),
            (Exception("ConfigurationError: Bad config"), "Configuration error"),
            (Exception("PluginError: Plugin failed"), "Plugin error occurred"),
            (Exception("CacheError: Cache miss"), "Cache operation failed"),
        ]
        
        for error, expected_pattern in test_cases:
            result = sanitizer.sanitize_error(error)
            assert expected_pattern.lower() in result["message"].lower()


class TestSafeErrorHandler:
    """Test safe error handler context manager"""
    
    def test_error_caught_and_sanitized(self):
        """Test that errors are caught and sanitized"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        with SafeErrorHandler(sanitizer, "test_context", "ERR-123") as handler:
            raise ValueError("Test error with secret key NRAK-123")
        
        assert hasattr(handler, 'sanitized_error')
        assert handler.sanitized_error["error"] is True
        assert "NRAK-123" not in handler.sanitized_error["message"]
        assert handler.sanitized_error["context"] == "test_context"
        assert handler.sanitized_error["error_id"] == "ERR-123"
    
    def test_no_error_no_sanitization(self):
        """Test that no error means no sanitization"""
        sanitizer = ErrorSanitizer(debug_mode=False)
        
        with SafeErrorHandler(sanitizer, "test_context") as handler:
            result = "success"
        
        assert not hasattr(handler, 'sanitized_error')


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_sanitize_error_response_function(self):
        """Test the convenience function"""
        error = ValidationError("Invalid input")
        
        result = sanitize_error_response(
            error=error,
            context="api_call",
            error_id="REQ-456",
            debug_mode=False
        )
        
        assert result["error"] is True
        assert result["context"] == "api_call"
        assert result["error_id"] == "REQ-456"
    
    def test_get_error_sanitizer_singleton(self):
        """Test that get_error_sanitizer returns singleton"""
        sanitizer1 = get_error_sanitizer()
        sanitizer2 = get_error_sanitizer()
        
        assert sanitizer1 is sanitizer2
    
    @patch.dict(os.environ, {'DEBUG_MODE': 'true'})
    def test_debug_mode_from_environment(self):
        """Test debug mode configuration from environment"""
        # This would typically be configured in the application startup
        debug_mode = os.getenv('DEBUG_MODE') == 'true'
        sanitizer = ErrorSanitizer(debug_mode=debug_mode)
        
        error = Exception("Internal error")
        result = sanitizer.sanitize_error(error)
        
        # In debug mode, should include debug info
        assert sanitizer.debug_mode is True


class TestErrorSeverityClassification:
    """Test error severity classification"""
    
    def test_public_error_classification(self):
        """Test that known public errors are classified correctly"""
        sanitizer = ErrorSanitizer()
        
        public_errors = [
            ValidationError("Invalid email"),
            SecurityError("Invalid token"),
            AuthenticationError("Bad credentials"),
            RateLimitError("Too many requests"),
            CacheError("Cache miss")
        ]
        
        for error in public_errors:
            severity = sanitizer._classify_error_severity(error, str(error))
            assert severity == ErrorSeverity.PUBLIC
    
    def test_sensitive_error_classification(self):
        """Test that errors with sensitive info are classified correctly"""
        sanitizer = ErrorSanitizer()
        
        sensitive_message = "Connection failed to host secret-db with password=secret123"
        severity = sanitizer._classify_error_severity(
            Exception(sensitive_message), 
            sensitive_message
        )
        
        assert severity == ErrorSeverity.SENSITIVE
    
    def test_internal_error_classification(self):
        """Test that generic errors are classified as internal"""
        sanitizer = ErrorSanitizer()
        
        internal_message = "Unexpected processing error in module X"
        severity = sanitizer._classify_error_severity(
            Exception(internal_message),
            internal_message
        )
        
        assert severity == ErrorSeverity.INTERNAL