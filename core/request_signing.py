"""
Request signing and verification for enhanced security

This module provides cryptographic request signing to prevent replay attacks
and ensure request integrity when using the MCP server over HTTP.
"""

import hashlib
import hmac
import json
import time
import secrets
import base64
import logging
from typing import Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SignatureAlgorithm(Enum):
    """Supported signature algorithms"""
    HMAC_SHA256 = "HMAC-SHA256"
    HMAC_SHA512 = "HMAC-SHA512"


@dataclass
class SignedRequest:
    """Represents a signed request"""
    payload: Dict[str, Any]
    timestamp: int
    nonce: str
    signature: str
    algorithm: SignatureAlgorithm
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for transmission"""
        return {
            "payload": self.payload,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "signature": self.signature,
            "algorithm": self.algorithm.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignedRequest':
        """Create from dictionary"""
        return cls(
            payload=data["payload"],
            timestamp=data["timestamp"],
            nonce=data["nonce"],
            signature=data["signature"],
            algorithm=SignatureAlgorithm(data["algorithm"])
        )


class RequestSigner:
    """Signs and verifies requests using HMAC"""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: SignatureAlgorithm = SignatureAlgorithm.HMAC_SHA256,
        max_timestamp_drift: int = 300  # 5 minutes
    ):
        """
        Initialize request signer
        
        Args:
            secret_key: Secret key for signing
            algorithm: Signature algorithm to use
            max_timestamp_drift: Max allowed timestamp drift in seconds
        """
        self.secret_key = secret_key.encode('utf-8')
        self.algorithm = algorithm
        self.max_timestamp_drift = max_timestamp_drift
        
        # Nonce tracking to prevent replay attacks
        self._used_nonces: Dict[str, int] = {}
        self._cleanup_interval = 3600  # Cleanup old nonces every hour
        self._last_cleanup = time.time()
    
    def sign_request(
        self,
        payload: Dict[str, Any],
        timestamp: Optional[int] = None,
        nonce: Optional[str] = None
    ) -> SignedRequest:
        """
        Sign a request payload
        
        Args:
            payload: Request payload to sign
            timestamp: Request timestamp (defaults to current time)
            nonce: Request nonce (defaults to random)
            
        Returns:
            Signed request
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        if nonce is None:
            nonce = self._generate_nonce()
        
        # Create signature
        signature = self._create_signature(payload, timestamp, nonce)
        
        return SignedRequest(
            payload=payload,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
            algorithm=self.algorithm
        )
    
    def verify_request(self, signed_request: SignedRequest) -> bool:
        """
        Verify a signed request
        
        Args:
            signed_request: Request to verify
            
        Returns:
            True if signature is valid and request is not replayed
        """
        try:
            # Check timestamp freshness
            current_time = int(time.time())
            time_diff = abs(current_time - signed_request.timestamp)
            
            if time_diff > self.max_timestamp_drift:
                logger.warning(
                    f"Request timestamp too old/new: {time_diff}s drift "
                    f"(max {self.max_timestamp_drift}s)"
                )
                return False
            
            # Check for replay attack (nonce reuse)
            if self._is_nonce_used(signed_request.nonce, signed_request.timestamp):
                logger.warning(f"Nonce reuse detected: {signed_request.nonce}")
                return False
            
            # Verify signature
            expected_signature = self._create_signature(
                signed_request.payload,
                signed_request.timestamp,
                signed_request.nonce
            )
            
            if not self._constant_time_compare(signed_request.signature, expected_signature):
                logger.warning("Invalid request signature")
                return False
            
            # Mark nonce as used
            self._mark_nonce_used(signed_request.nonce, signed_request.timestamp)
            
            # Cleanup old nonces periodically
            self._cleanup_old_nonces()
            
            return True
            
        except Exception as e:
            logger.error(f"Request verification failed: {e}")
            return False
    
    def _create_signature(
        self,
        payload: Dict[str, Any],
        timestamp: int,
        nonce: str
    ) -> str:
        """Create HMAC signature for request"""
        
        # Create canonical string to sign
        canonical_string = self._create_canonical_string(payload, timestamp, nonce)
        
        # Select hash algorithm
        if self.algorithm == SignatureAlgorithm.HMAC_SHA256:
            hash_func = hashlib.sha256
        elif self.algorithm == SignatureAlgorithm.HMAC_SHA512:
            hash_func = hashlib.sha512
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret_key,
            canonical_string.encode('utf-8'),
            hash_func
        ).digest()
        
        # Base64 encode for transmission
        return base64.b64encode(signature).decode('ascii')
    
    def _create_canonical_string(
        self,
        payload: Dict[str, Any],
        timestamp: int,
        nonce: str
    ) -> str:
        """Create canonical string representation for signing"""
        
        # Sort payload keys for consistent ordering
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        # Combine components
        canonical_parts = [
            self.algorithm.value,
            str(timestamp),
            nonce,
            payload_str
        ]
        
        return '\n'.join(canonical_parts)
    
    def _generate_nonce(self) -> str:
        """Generate a cryptographically secure random nonce"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii')
    
    def _is_nonce_used(self, nonce: str, timestamp: int) -> bool:
        """Check if nonce has been used recently"""
        if nonce in self._used_nonces:
            return True
        return False
    
    def _mark_nonce_used(self, nonce: str, timestamp: int):
        """Mark nonce as used"""
        self._used_nonces[nonce] = timestamp
    
    def _cleanup_old_nonces(self):
        """Remove old nonces to prevent memory leak"""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        # Remove nonces older than max drift time
        cutoff_time = current_time - self.max_timestamp_drift
        old_nonces = [
            nonce for nonce, timestamp in self._used_nonces.items()
            if timestamp < cutoff_time
        ]
        
        for nonce in old_nonces:
            del self._used_nonces[nonce]
        
        self._last_cleanup = current_time
        
        if old_nonces:
            logger.debug(f"Cleaned up {len(old_nonces)} old nonces")
    
    def _constant_time_compare(self, a: str, b: str) -> bool:
        """Compare two strings in constant time to prevent timing attacks"""
        return hmac.compare_digest(a, b)


class RequestSigningMiddleware:
    """Middleware for signing/verifying HTTP requests"""
    
    def __init__(self, signer: RequestSigner):
        self.signer = signer
    
    def sign_outgoing_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign an outgoing request
        
        Args:
            request_data: Request data to sign
            
        Returns:
            Request with signature headers
        """
        signed_request = self.signer.sign_request(request_data)
        
        return {
            "data": signed_request.payload,
            "headers": {
                "X-Signature": signed_request.signature,
                "X-Timestamp": str(signed_request.timestamp),
                "X-Nonce": signed_request.nonce,
                "X-Algorithm": signed_request.algorithm.value
            }
        }
    
    def verify_incoming_request(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify an incoming signed request
        
        Args:
            payload: Request payload
            headers: Request headers containing signature
            
        Returns:
            True if request is valid
        """
        try:
            # Extract signature components from headers
            signature = headers.get("X-Signature")
            timestamp_str = headers.get("X-Timestamp")
            nonce = headers.get("X-Nonce")
            algorithm_str = headers.get("X-Algorithm")
            
            if not all([signature, timestamp_str, nonce, algorithm_str]):
                logger.warning("Missing signature headers")
                return False
            
            timestamp = int(timestamp_str)
            algorithm = SignatureAlgorithm(algorithm_str)
            
            # Create signed request object
            signed_request = SignedRequest(
                payload=payload,
                timestamp=timestamp,
                nonce=nonce,
                signature=signature,
                algorithm=algorithm
            )
            
            return self.signer.verify_request(signed_request)
            
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid signature headers: {e}")
            return False


class TokenManager:
    """Manages API tokens with signing capabilities"""
    
    def __init__(self, master_secret: str):
        self.master_secret = master_secret
        self._signers: Dict[str, RequestSigner] = {}
    
    def create_token(
        self,
        client_id: str,
        permissions: Optional[Dict[str, Any]] = None,
        expires_at: Optional[int] = None
    ) -> str:
        """
        Create a signed API token
        
        Args:
            client_id: Client identifier
            permissions: Optional permissions dict
            expires_at: Optional expiration timestamp
            
        Returns:
            Base64-encoded signed token
        """
        token_data = {
            "client_id": client_id,
            "permissions": permissions or {},
            "issued_at": int(time.time()),
            "expires_at": expires_at
        }
        
        # Sign token with master secret
        master_signer = RequestSigner(self.master_secret)
        signed_token = master_signer.sign_request(token_data)
        
        # Encode for transmission
        token_json = json.dumps(signed_token.to_dict())
        return base64.b64encode(token_json.encode('utf-8')).decode('ascii')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode an API token
        
        Args:
            token: Base64-encoded signed token
            
        Returns:
            Token data if valid, None otherwise
        """
        try:
            # Decode token
            token_json = base64.b64decode(token.encode('ascii')).decode('utf-8')
            token_dict = json.loads(token_json)
            signed_request = SignedRequest.from_dict(token_dict)
            
            # Verify with master secret
            master_signer = RequestSigner(self.master_secret)
            if not master_signer.verify_request(signed_request):
                return None
            
            # Check expiration
            payload = signed_request.payload
            if payload.get("expires_at"):
                if int(time.time()) > payload["expires_at"]:
                    logger.warning("Token has expired")
                    return None
            
            return payload
            
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return None
    
    def get_signer_for_client(self, client_id: str) -> RequestSigner:
        """
        Get or create a request signer for a client
        
        Args:
            client_id: Client identifier
            
        Returns:
            RequestSigner instance for the client
        """
        if client_id not in self._signers:
            # Derive client-specific secret from master secret
            client_secret = hmac.new(
                self.master_secret.encode('utf-8'),
                f"client:{client_id}".encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            self._signers[client_id] = RequestSigner(client_secret)
        
        return self._signers[client_id]


# Example usage:
"""
# Server side - verify incoming requests
signer = RequestSigner("your-secret-key")
middleware = RequestSigningMiddleware(signer)

# In request handler
if middleware.verify_incoming_request(request_payload, request_headers):
    # Process request
    pass
else:
    # Reject request
    return {"error": "Invalid signature"}

# Client side - sign outgoing requests
signed_request = middleware.sign_outgoing_request({
    "method": "run_nrql_query",
    "params": {"nrql": "SELECT count(*) FROM Transaction"}
})

# Send request with signed_request["headers"]
"""