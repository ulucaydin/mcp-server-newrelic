"""
Tests for security module
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
import time

from core.security import (
    NRQLValidator, SecureKeyStorage, InputValidator, 
    RateLimiter, AuditLogger, check_rate_limit
)
from core.errors import ValidationError


class TestNRQLValidator:
    """Test NRQL query validation"""
    
    def test_valid_nrql_queries(self):
        """Test validation of valid NRQL queries"""
        valid_queries = [
            "SELECT count(*) FROM Transaction",
            "SELECT average(duration) FROM Transaction SINCE 1 hour ago",
            "SELECT * FROM Transaction WHERE appName = 'MyApp'",
            "SELECT percentile(duration, 95) FROM Transaction FACET name",
            "FROM Transaction SELECT count(*) WHERE error IS true"
        ]
        
        for query in valid_queries:
            result = NRQLValidator.validate_nrql(query)
            assert result == query
    
    def test_dangerous_keywords_detection(self):
        """Test detection of dangerous SQL keywords"""
        dangerous_queries = [
            "DELETE FROM Transaction",
            "DROP TABLE users",
            "UPDATE Transaction SET duration = 0",
            "INSERT INTO Transaction VALUES (1, 2, 3)",
            "CREATE TABLE new_table",
            "ALTER TABLE Transaction ADD COLUMN test"
        ]
        
        for query in dangerous_queries:
            with pytest.raises(ValidationError) as exc_info:
                NRQLValidator.validate_nrql(query)
            assert "dangerous keyword" in str(exc_info.value).lower()
    
    def test_sql_comment_detection(self):
        """Test detection of SQL comments"""
        queries_with_comments = [
            "SELECT * FROM Transaction -- comment",
            "SELECT * FROM Transaction /* comment */",
            "SELECT * FROM Transaction # comment"
        ]
        
        for query in queries_with_comments:
            with pytest.raises(ValidationError) as exc_info:
                NRQLValidator.validate_nrql(query)
            assert "sql comment" in str(exc_info.value).lower()
    
    def test_semicolon_detection(self):
        """Test detection of semicolons (statement separation)"""
        query = "SELECT * FROM Transaction; DELETE FROM Transaction"
        
        with pytest.raises(ValidationError) as exc_info:
            NRQLValidator.validate_nrql(query)
        assert "semicolon" in str(exc_info.value).lower()
    
    def test_string_escaping(self):
        """Test string escaping in NRQL"""
        # Test query with quotes
        query = "SELECT * FROM Transaction WHERE name = 'O\\'Brien'"
        result = NRQLValidator.validate_nrql(query)
        assert result == query
        
        # Test potential injection
        query = "SELECT * FROM Transaction WHERE name = ''; DELETE FROM users--'"
        with pytest.raises(ValidationError):
            NRQLValidator.validate_nrql(query)
    
    def test_case_insensitive_detection(self):
        """Test case-insensitive keyword detection"""
        dangerous_queries = [
            "DeLeTe FROM Transaction",
            "dRoP TABLE users",
            "UpDaTe Transaction SET x = 1"
        ]
        
        for query in dangerous_queries:
            with pytest.raises(ValidationError):
                NRQLValidator.validate_nrql(query)
    
    def test_validate_entity_guid(self):
        """Test entity GUID validation"""
        # Valid GUIDs
        valid_guids = [
            "MTIzNDU2fEFQTXxBUFBMSUNBVElPTnwxMjM0NTY3",
            "OTg3NjU0fElORlJBfEhPU1R8MTIzNDU2Nzg5",
            "MXxCUk9XU0VSfEFQUExJQ0FUSU9OfDE"
        ]
        
        for guid in valid_guids:
            result = NRQLValidator.validate_entity_guid(guid)
            assert result == guid
        
        # Invalid GUIDs
        invalid_guids = [
            "invalid-guid",
            "12345",
            "MTIzNDU2|APM|APPLICATION|1234567",  # Wrong separator
            "MTIzNDU2fEFQTXxBUFBMSUNBVElPTnwxMjM0NTY3' OR '1'='1",  # Injection attempt
            "../../../etc/passwd",  # Path traversal
            ""  # Empty
        ]
        
        for guid in invalid_guids:
            with pytest.raises(ValidationError):
                NRQLValidator.validate_entity_guid(guid)


class TestSecureKeyStorage:
    """Test secure key storage"""
    
    @pytest.fixture
    def temp_keyfile(self):
        """Create temporary keyfile"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            yield f.name
        # Cleanup
        if os.path.exists(f.name):
            os.unlink(f.name)
    
    def test_encrypt_decrypt_key(self):
        """Test key encryption and decryption"""
        storage = SecureKeyStorage()
        
        original_key = "NRAK-1234567890ABCDEF"
        encrypted = storage.encrypt_key(original_key)
        
        # Encrypted should be different from original
        assert encrypted != original_key
        assert isinstance(encrypted, str)
        
        # Should decrypt back to original
        decrypted = storage.decrypt_key(encrypted)
        assert decrypted == original_key
    
    def test_save_load_keys(self, temp_keyfile):
        """Test saving and loading encrypted keys"""
        storage = SecureKeyStorage(keyfile=temp_keyfile)
        
        # Store some keys
        storage.store_key("account1", "NRAK-ACCOUNT1KEY")
        storage.store_key("account2", "NRAK-ACCOUNT2KEY")
        
        # Save to file
        storage.save_keys()
        
        # Create new storage instance and load
        storage2 = SecureKeyStorage(keyfile=temp_keyfile)
        storage2.load_keys()
        
        # Verify keys
        assert storage2.get_key("account1") == "NRAK-ACCOUNT1KEY"
        assert storage2.get_key("account2") == "NRAK-ACCOUNT2KEY"
    
    def test_nonexistent_key(self):
        """Test getting nonexistent key"""
        storage = SecureKeyStorage()
        assert storage.get_key("nonexistent") is None
    
    def test_keyfile_permissions(self, temp_keyfile):
        """Test that keyfile is created with secure permissions"""
        storage = SecureKeyStorage(keyfile=temp_keyfile)
        storage.store_key("test", "NRAK-TESTKEY")
        storage.save_keys()
        
        # Check file permissions (should be readable only by owner)
        stat_info = os.stat(temp_keyfile)
        mode = stat_info.st_mode & 0o777
        assert mode == 0o600  # Read/write for owner only


class TestInputValidator:
    """Test input validation"""
    
    def test_validate_account_id(self):
        """Test account ID validation"""
        # Valid account IDs
        valid_ids = [123456, "123456", 1, "1"]
        
        for account_id in valid_ids:
            result = InputValidator.validate_account_id(account_id)
            assert isinstance(result, int)
            assert result > 0
        
        # Invalid account IDs
        invalid_ids = [
            "abc123",  # Non-numeric
            -123,      # Negative
            0,         # Zero
            "",        # Empty string
            None,      # None
            "123.45",  # Float string
            "12 34",   # Space
        ]
        
        for account_id in invalid_ids:
            with pytest.raises(ValidationError):
                InputValidator.validate_account_id(account_id)
    
    def test_validate_api_key(self):
        """Test API key validation"""
        # Valid API keys
        valid_keys = [
            "NRAK-1234567890ABCDEF",
            "NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "NRIQ-1234567890abcdef"
        ]
        
        for key in valid_keys:
            result = InputValidator.validate_api_key(key)
            assert result == key
        
        # Invalid API keys
        invalid_keys = [
            "invalid-key",
            "NRAK_1234567890",  # Wrong separator
            "NRAK-",  # Too short
            "1234567890",  # No prefix
            "",  # Empty
            None,  # None
            "NRAK-<script>alert('xss')</script>",  # XSS attempt
        ]
        
        for key in invalid_keys:
            with pytest.raises(ValidationError):
                InputValidator.validate_api_key(key)
    
    def test_validate_time_range(self):
        """Test time range validation"""
        # Valid time ranges
        valid_ranges = [
            "SINCE 1 hour ago",
            "SINCE 30 minutes ago",
            "SINCE 7 days ago",
            "SINCE '2024-01-01 00:00:00'",
            "SINCE 1234567890",
            "BETWEEN 1 hour ago AND 30 minutes ago"
        ]
        
        for time_range in valid_ranges:
            result = InputValidator.validate_time_range(time_range)
            assert result == time_range
        
        # Invalid time ranges
        invalid_ranges = [
            "SINCE yesterday",  # Not NRQL format
            "1 hour ago",  # Missing SINCE
            "SINCE 1 hour ago; DELETE",  # Injection
            "",  # Empty
            "SINCE -1 hour ago",  # Negative (though might be valid?)
        ]
        
        for time_range in invalid_ranges:
            with pytest.raises(ValidationError):
                InputValidator.validate_time_range(time_range)
    
    def test_sanitize_string(self):
        """Test string sanitization"""
        # Test HTML/script removal
        assert InputValidator.sanitize_string("<script>alert('xss')</script>Hello") == "Hello"
        assert InputValidator.sanitize_string("Hello<br>World") == "HelloWorld"
        
        # Test length limit
        long_string = "a" * 2000
        sanitized = InputValidator.sanitize_string(long_string, max_length=100)
        assert len(sanitized) == 100
        
        # Test allowed characters
        assert InputValidator.sanitize_string("Hello@World#123") == "Hello@World#123"
        assert InputValidator.sanitize_string("Hello\x00World") == "HelloWorld"  # Null byte


class TestRateLimiter:
    """Test rate limiting"""
    
    def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality"""
        limiter = RateLimiter(max_requests=3, window_seconds=1)
        key = "test_user"
        
        # First 3 requests should succeed
        assert limiter.check_limit(key) is True
        assert limiter.check_limit(key) is True
        assert limiter.check_limit(key) is True
        
        # 4th request should fail
        assert limiter.check_limit(key) is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should succeed again
        assert limiter.check_limit(key) is True
    
    def test_different_keys(self):
        """Test rate limiting with different keys"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # Different keys should have separate limits
        assert limiter.check_limit("user1") is True
        assert limiter.check_limit("user2") is True
        assert limiter.check_limit("user1") is True
        assert limiter.check_limit("user2") is True
        
        # Both should be limited now
        assert limiter.check_limit("user1") is False
        assert limiter.check_limit("user2") is False
    
    def test_cleanup(self):
        """Test cleanup of old entries"""
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        
        # Add some entries
        limiter.check_limit("user1")
        limiter.check_limit("user2")
        
        # Wait for expiry
        time.sleep(1.1)
        
        # Trigger cleanup
        limiter.cleanup()
        
        # Buckets should be empty
        assert len(limiter._buckets) == 0
    
    def test_global_rate_limit_function(self):
        """Test global rate limit function"""
        # Reset global limiter
        from core.security import _rate_limiter
        _rate_limiter._buckets.clear()
        
        # Test with default settings
        account_id = "123456"
        
        # Should succeed initially
        assert check_rate_limit(account_id) is True
        
        # Make many requests to hit limit
        for _ in range(200):
            check_rate_limit(account_id)
        
        # Should eventually be limited
        assert check_rate_limit(account_id) is False


class TestAuditLogger:
    """Test audit logging"""
    
    @pytest.fixture
    def temp_logfile(self):
        """Create temporary log file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            yield f.name
        # Cleanup
        if os.path.exists(f.name):
            os.unlink(f.name)
    
    def test_log_security_event(self, temp_logfile):
        """Test logging security events"""
        logger = AuditLogger(logfile=temp_logfile)
        
        # Log some events
        logger.log_security_event("injection_attempt", {
            "query": "SELECT * FROM x; DELETE",
            "source_ip": "192.168.1.1",
            "account_id": "123456"
        })
        
        logger.log_security_event("rate_limit_exceeded", {
            "account_id": "789012",
            "requests_count": 150
        })
        
        # Read log file
        with open(temp_logfile, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        
        # Check first event
        assert "injection_attempt" in lines[0]
        assert "192.168.1.1" in lines[0]
        
        # Check second event
        assert "rate_limit_exceeded" in lines[1]
        assert "789012" in lines[1]
    
    def test_log_with_pii_redaction(self, temp_logfile):
        """Test that PII is redacted in logs"""
        logger = AuditLogger(logfile=temp_logfile, redact_pii=True)
        
        # Log event with potential PII
        logger.log_security_event("api_key_validation_failed", {
            "api_key": "NRAK-1234567890ABCDEF",
            "email": "user@example.com",
            "account_id": "123456"
        })
        
        # Read log
        with open(temp_logfile, 'r') as f:
            content = f.read()
        
        # API key should be redacted
        assert "NRAK-1234567890ABCDEF" not in content
        assert "NRAK-***" in content or "[REDACTED]" in content
        
        # Email might be partially redacted
        assert "user@example.com" not in content or "u***@example.com" in content