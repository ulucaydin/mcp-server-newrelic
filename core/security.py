"""
Security utilities for the MCP server
"""

import re
import os
import base64
import hashlib
import hmac
from typing import Dict, Any, Optional, List, Union
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Security-related errors"""
    pass


class NRQLValidator:
    """Validates and sanitizes NRQL queries to prevent injection"""
    
    # Dangerous NRQL keywords that could modify data
    DANGEROUS_KEYWORDS = {
        'DELETE', 'DROP', 'UPDATE', 'INSERT', 'CREATE', 'ALTER',
        'GRANT', 'REVOKE', 'TRUNCATE', 'EXEC', 'EXECUTE'
    }
    
    # Allowed NRQL functions (whitelist approach)
    ALLOWED_FUNCTIONS = {
        # Aggregation functions
        'average', 'count', 'latest', 'max', 'median', 'min', 'percentage',
        'percentile', 'rate', 'stddev', 'sum', 'uniqueCount',
        
        # Time functions
         'buckets', 'eventTypes', 'getField', 'keyset',
        
        # Math functions
        'abs', 'ceil', 'exp', 'floor', 'ln', 'log', 'log10', 'pow',
        'round', 'sqrt',
        
        # String functions
        'concat', 'length', 'lower', 'upper', 'substring',
        
        # Date functions
        'dayOfMonth', 'dayOfWeek', 'dayOfYear', 'hour', 'minute',
        'month', 'quarter', 'second', 'weekOfYear', 'year',
        
        # Utility functions
        'apdex', 'histogram', 'funnel'
    }
    
    @staticmethod
    def validate_nrql(query: str) -> str:
        """
        Validate and sanitize NRQL query
        
        Args:
            query: NRQL query string
            
        Returns:
            Sanitized query
            
        Raises:
            SecurityError: If query contains dangerous patterns
        """
        if not query or not isinstance(query, str):
            raise SecurityError("Invalid NRQL query format")
        
        # Remove comments
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        query = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
        
        # Check for dangerous keywords
        query_upper = query.upper()
        for keyword in NRQLValidator.DANGEROUS_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_upper):
                raise SecurityError(f"Dangerous keyword '{keyword}' not allowed in NRQL")
        
        # Check for common injection patterns
        if re.search(r'[;\x00-\x1f\x7f-\x9f]', query):
            raise SecurityError("Invalid characters detected in NRQL query")
        
        # Validate quotes are balanced
        single_quotes = query.count("'")
        double_quotes = query.count('"')
        if single_quotes % 2 != 0 or double_quotes % 2 != 0:
            raise SecurityError("Unbalanced quotes in NRQL query")
        
        # Check for excessive complexity
        if len(query) > 10000:
            raise SecurityError("NRQL query too long (max 10000 characters)")
        
        # Check for nested queries (not supported in NRQL anyway)
        if query.upper().count('SELECT') > 1:
            raise SecurityError("Nested queries not allowed")
        
        return query.strip()
    
    @staticmethod
    def sanitize_string_literal(value: str) -> str:
        """
        Sanitize a string value for use in NRQL
        
        Args:
            value: String to sanitize
            
        Returns:
            Escaped string safe for NRQL
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Escape single quotes by doubling them
        value = value.replace("'", "''")
        
        # Remove control characters
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        
        return value
    
    @staticmethod
    def validate_identifier(identifier: str) -> str:
        """
        Validate an identifier (table name, column name, etc.)
        
        Args:
            identifier: Identifier to validate
            
        Returns:
            Validated identifier
            
        Raises:
            SecurityError: If identifier is invalid
        """
        if not identifier or not isinstance(identifier, str):
            raise SecurityError("Invalid identifier")
        
        # Allow alphanumeric, underscore, dash, and dot (for namespaced metrics)
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_.\-]*$', identifier):
            raise SecurityError(f"Invalid identifier: {identifier}")
        
        if len(identifier) > 255:
            raise SecurityError("Identifier too long")
        
        return identifier


class SecureKeyStorage:
    """Secure storage for API keys and sensitive data"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize secure storage
        
        Args:
            master_key: Master key for encryption (uses env var if not provided)
        """
        self.master_key = master_key or os.getenv('MCP_MASTER_KEY')
        if not self.master_key:
            # Generate a key from machine-specific data if not provided
            self.master_key = self._generate_machine_key()
        
        self._cipher = self._create_cipher(self.master_key)
    
    def _generate_machine_key(self) -> str:
        """Generate a machine-specific key"""
        # Combine various machine-specific attributes
        machine_id = f"{os.name}-{os.getenv('USER', 'default')}-{os.getenv('HOSTNAME', 'localhost')}"
        return base64.urlsafe_b64encode(
            hashlib.sha256(machine_id.encode()).digest()
        ).decode()
    
    def _create_cipher(self, key: str) -> Fernet:
        """Create a Fernet cipher from a key"""
        # Derive a proper key from the input
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'mcp-newrelic-salt',  # In production, use a random salt
            iterations=100000,
        )
        key_bytes = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(key_bytes)
    
    def encrypt(self, data: Union[str, Dict]) -> str:
        """
        Encrypt sensitive data
        
        Args:
            data: Data to encrypt (string or dict)
            
        Returns:
            Encrypted data as base64 string
        """
        if isinstance(data, dict):
            data = json.dumps(data)
        
        return self._cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> Union[str, Dict]:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            Decrypted data
        """
        decrypted = self._cipher.decrypt(encrypted_data.encode()).decode()
        
        # Try to parse as JSON
        try:
            return json.loads(decrypted)
        except json.JSONDecodeError:
            return decrypted


class InputValidator:
    """Validates user inputs to prevent various attacks"""
    
    @staticmethod
    def validate_account_id(account_id: Any) -> int:
        """Validate New Relic account ID"""
        if account_id is None:
            raise ValueError("Account ID is required")
        
        try:
            account_id = int(account_id)
            if account_id <= 0 or account_id > 999999999:
                raise ValueError("Invalid account ID range")
            return account_id
        except (ValueError, TypeError):
            raise ValueError(f"Invalid account ID: {account_id}")
    
    @staticmethod
    def validate_guid(guid: str) -> str:
        """Validate entity GUID format"""
        if not isinstance(guid, str) or not guid:
            raise ValueError("Invalid GUID format")
        
        # New Relic GUIDs are base64 encoded
        if not re.match(r'^[A-Za-z0-9+/]+=*\|[A-Z0-9_]+\|[A-Z0-9_]+$', guid):
            raise ValueError(f"Invalid New Relic GUID format: {guid}")
        
        return guid
    
    @staticmethod
    def validate_time_range(time_range: str) -> str:
        """Validate NRQL time range"""
        if not isinstance(time_range, str):
            raise ValueError("Time range must be a string")
        
        # Allow common NRQL time patterns
        patterns = [
            r'^SINCE \d+ (second|minute|hour|day|week|month)s? ago$',
            r'^SINCE \d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$',
            r'^BETWEEN \d+ (second|minute|hour|day|week|month)s? ago AND \d+ (second|minute|hour|day|week|month)s? ago$',
            r'^SINCE yesterday$',
            r'^SINCE today$',
            r'^SINCE this (week|month|quarter|year)$',
            r'^SINCE last (week|month|quarter|year)$'
        ]
        
        time_range = time_range.strip()
        if not any(re.match(pattern, time_range, re.IGNORECASE) for pattern in patterns):
            raise ValueError(f"Invalid time range format: {time_range}")
        
        return time_range
    
    @staticmethod
    def validate_limit(limit: Any, max_limit: int = 2000) -> int:
        """Validate result limit"""
        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError("Limit must be positive")
            if limit > max_limit:
                logger.warning(f"Limit {limit} exceeds maximum {max_limit}, using {max_limit}")
                limit = max_limit
            return limit
        except (ValueError, TypeError):
            raise ValueError(f"Invalid limit: {limit}")
    
    @staticmethod
    def validate_api_key(api_key: str) -> str:
        """Validate New Relic API key format"""
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("API key is required")
        
        # New Relic API keys have specific prefixes
        valid_prefixes = ['NRAK-', 'NRII-', 'NRAA-', 'NRIQ-']
        if not any(api_key.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError("Invalid New Relic API key format")
        
        if len(api_key) < 20 or len(api_key) > 100:
            raise ValueError("Invalid API key length")
        
        return api_key


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}
    
    def check_rate_limit(self, key: str) -> bool:
        """
        Check if request is within rate limit
        
        Args:
            key: Identifier for rate limiting (e.g., account ID)
            
        Returns:
            True if within limit, False otherwise
        """
        import time
        now = time.time()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside window
        self.requests[key] = [
            timestamp for timestamp in self.requests[key]
            if now - timestamp < self.window_seconds
        ]
        
        # Check if within limit
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True
    
    def get_reset_time(self, key: str) -> Optional[float]:
        """Get time when rate limit resets for a key"""
        if key not in self.requests or not self.requests[key]:
            return None
        
        oldest_request = min(self.requests[key])
        return oldest_request + self.window_seconds


class AuditLogger:
    """Audit logger for security-sensitive operations"""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize audit logger"""
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)
    
    def log_tool_access(self, tool_name: str, user: str, params: Dict[str, Any], 
                       success: bool, error: Optional[str] = None):
        """Log tool access for audit trail"""
        # Sanitize sensitive data
        safe_params = self._sanitize_params(params)
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'tool': tool_name,
            'user': user,
            'params': safe_params,
            'success': success,
            'error': error
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from parameters"""
        sensitive_keys = {'api_key', 'password', 'secret', 'token'}
        
        safe_params = {}
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_params[key] = '***REDACTED***'
            elif isinstance(value, dict):
                safe_params[key] = self._sanitize_params(value)
            else:
                safe_params[key] = value
        
        return safe_params


# Global instances
_rate_limiter = RateLimiter()
_audit_logger = AuditLogger()


def check_rate_limit(account_id: Union[str, int]) -> bool:
    """Check if account is within rate limit"""
    return _rate_limiter.check_rate_limit(str(account_id))


def audit_log(tool_name: str, user: str, params: Dict[str, Any], 
              success: bool, error: Optional[str] = None):
    """Log tool access for audit"""
    _audit_logger.log_tool_access(tool_name, user, params, success, error)