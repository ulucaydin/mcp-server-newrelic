"""
Audit logging and monitoring for MCP server operations
"""

import json
import logging
import time
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from pathlib import Path
import structlog
from collections import deque
import hashlib

# Get structured logger
logger = structlog.get_logger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    # Authentication & Authorization
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    ACCOUNT_SWITCH = "account.switch"
    
    # Tool Invocations
    TOOL_CALL = "tool.call"
    TOOL_SUCCESS = "tool.success"
    TOOL_FAILURE = "tool.failure"
    
    # Resource Access
    RESOURCE_READ = "resource.read"
    RESOURCE_ACCESS_DENIED = "resource.access_denied"
    
    # API Operations
    NERDGRAPH_QUERY = "nerdgraph.query"
    NRQL_QUERY = "nrql.query"
    API_RATE_LIMIT = "api.rate_limit"
    
    # Configuration Changes
    CONFIG_CHANGE = "config.change"
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_ERROR = "plugin.error"
    
    # Security Events
    SECURITY_VIOLATION = "security.violation"
    INJECTION_ATTEMPT = "security.injection_attempt"
    
    # System Events
    SERVER_START = "server.start"
    SERVER_STOP = "server.stop"
    HEALTH_CHECK = "health.check"
    ERROR = "error"


@dataclass
class AuditEvent:
    """Represents an audit event"""
    timestamp: float
    event_type: AuditEventType
    user_id: Optional[str]
    session_id: Optional[str]
    account_id: Optional[str]
    tool_name: Optional[str]
    resource_uri: Optional[str]
    details: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['timestamp_iso'] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Handles audit logging with multiple backends"""
    
    def __init__(self, 
                 log_file: Optional[str] = None,
                 max_memory_events: int = 10000,
                 enable_console: bool = True,
                 enable_metrics: bool = True):
        """
        Initialize audit logger
        
        Args:
            log_file: Path to audit log file (JSON lines format)
            max_memory_events: Maximum events to keep in memory
            enable_console: Whether to log to console
            enable_metrics: Whether to update metrics
        """
        self.log_file = log_file
        self.max_memory_events = max_memory_events
        self.enable_console = enable_console
        self.enable_metrics = enable_metrics
        
        # In-memory event buffer for recent events
        self.recent_events = deque(maxlen=max_memory_events)
        
        # Event counters by type
        self.event_counts: Dict[str, int] = {}
        
        # Session tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize file logging if enabled
        if self.log_file:
            self._init_file_logging()
    
    def _init_file_logging(self):
        """Initialize file-based audit logging"""
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure structured logging to file
        self.file_logger = structlog.get_logger("audit.file")
        
        # Add file handler
        handler = logging.FileHandler(self.log_file)
        handler.setFormatter(logging.Formatter('%(message)s'))
        
        stdlib_logger = logging.getLogger("audit.file")
        stdlib_logger.addHandler(handler)
        stdlib_logger.setLevel(logging.INFO)
    
    async def log_event(self, event: AuditEvent):
        """Log an audit event"""
        # Add to memory buffer
        self.recent_events.append(event)
        
        # Update counters
        event_type = event.event_type.value
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # Log to console if enabled
        if self.enable_console:
            logger.info(
                "audit_event",
                event_type=event_type,
                tool=event.tool_name,
                success=event.success,
                duration_ms=event.duration_ms,
                user_id=event.user_id,
                session_id=event.session_id
            )
        
        # Log to file if enabled
        if self.log_file and hasattr(self, 'file_logger'):
            self.file_logger.info(event.to_json())
        
        # Update metrics if enabled
        if self.enable_metrics:
            await self._update_metrics(event)
        
        # Check for security events
        if event.event_type in [AuditEventType.SECURITY_VIOLATION, 
                               AuditEventType.INJECTION_ATTEMPT]:
            await self._handle_security_event(event)
    
    async def _update_metrics(self, event: AuditEvent):
        """Update metrics based on event"""
        from .health import get_health_monitor
        
        monitor = get_health_monitor()
        if not monitor:
            return
        
        # Record request metrics for tool calls
        if event.event_type == AuditEventType.TOOL_CALL and event.duration_ms:
            monitor.record_request(
                tool=event.tool_name or "unknown",
                duration=event.duration_ms / 1000.0,
                success=event.success
            )
    
    async def _handle_security_event(self, event: AuditEvent):
        """Handle security-related events"""
        logger.warning(
            "security_event_detected",
            event_type=event.event_type.value,
            details=event.details,
            user_id=event.user_id,
            ip_address=event.ip_address
        )
        
        # Could implement additional security responses here:
        # - Send alerts
        # - Block IP addresses
        # - Notify administrators
    
    def start_session(self, session_id: str, user_id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None):
        """Start tracking a session"""
        self.active_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "start_time": time.time(),
            "metadata": metadata or {},
            "event_count": 0,
            "last_activity": time.time()
        }
        
        asyncio.create_task(self.log_event(AuditEvent(
            timestamp=time.time(),
            event_type=AuditEventType.AUTH_SUCCESS,
            user_id=user_id,
            session_id=session_id,
            account_id=None,
            tool_name=None,
            resource_uri=None,
            details={"action": "session_start", **(metadata or {})},
            success=True
        )))
    
    def end_session(self, session_id: str):
        """End a session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            duration = time.time() - session["start_time"]
            
            asyncio.create_task(self.log_event(AuditEvent(
                timestamp=time.time(),
                event_type=AuditEventType.AUTH_SUCCESS,
                user_id=session.get("user_id"),
                session_id=session_id,
                account_id=None,
                tool_name=None,
                resource_uri=None,
                details={
                    "action": "session_end",
                    "duration_seconds": duration,
                    "event_count": session["event_count"]
                },
                success=True
            )))
            
            del self.active_sessions[session_id]
    
    def update_session_activity(self, session_id: str):
        """Update last activity time for a session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = time.time()
            self.active_sessions[session_id]["event_count"] += 1
    
    async def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """Clean up inactive sessions"""
        cutoff_time = time.time() - (timeout_minutes * 60)
        
        for session_id in list(self.active_sessions.keys()):
            session = self.active_sessions[session_id]
            if session["last_activity"] < cutoff_time:
                self.end_session(session_id)
    
    def get_recent_events(self, 
                         limit: int = 100,
                         event_types: Optional[List[AuditEventType]] = None,
                         session_id: Optional[str] = None,
                         user_id: Optional[str] = None) -> List[AuditEvent]:
        """Get recent events with optional filtering"""
        events = list(self.recent_events)
        
        # Apply filters
        if event_types:
            event_type_values = [et.value for et in event_types]
            events = [e for e in events if e.event_type.value in event_type_values]
        
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        # Sort by timestamp descending and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit statistics"""
        total_events = sum(self.event_counts.values())
        
        # Calculate event rate (events per minute)
        if self.recent_events:
            oldest_event = self.recent_events[0]
            newest_event = self.recent_events[-1]
            time_span = newest_event.timestamp - oldest_event.timestamp
            events_per_minute = (len(self.recent_events) / time_span * 60) if time_span > 0 else 0
        else:
            events_per_minute = 0
        
        return {
            "total_events": total_events,
            "events_by_type": dict(self.event_counts),
            "active_sessions": len(self.active_sessions),
            "events_in_memory": len(self.recent_events),
            "events_per_minute": round(events_per_minute, 2)
        }
    
    async def export_events(self, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           format: str = "json") -> str:
        """Export events for analysis"""
        events = list(self.recent_events)
        
        # Filter by time range
        if start_time:
            start_ts = start_time.timestamp()
            events = [e for e in events if e.timestamp >= start_ts]
        
        if end_time:
            end_ts = end_time.timestamp()
            events = [e for e in events if e.timestamp <= end_ts]
        
        if format == "json":
            return json.dumps([e.to_dict() for e in events], indent=2)
        elif format == "jsonl":
            return "\n".join(e.to_json() for e in events)
        else:
            raise ValueError(f"Unsupported format: {format}")


class AuditContext:
    """Context manager for audit logging"""
    
    def __init__(self, 
                 audit_logger: AuditLogger,
                 event_type: AuditEventType,
                 **kwargs):
        """
        Initialize audit context
        
        Args:
            audit_logger: AuditLogger instance
            event_type: Type of event being audited
            **kwargs: Additional event attributes
        """
        self.audit_logger = audit_logger
        self.event_type = event_type
        self.kwargs = kwargs
        self.start_time = None
        self.success = True
        self.error_message = None
        self.details = {}
    
    async def __aenter__(self):
        """Enter context"""
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context and log event"""
        duration_ms = (time.time() - self.start_time) * 1000 if self.start_time else None
        
        if exc_type:
            self.success = False
            self.error_message = str(exc_val)
        
        event = AuditEvent(
            timestamp=self.start_time or time.time(),
            event_type=self.event_type,
            success=self.success,
            error_message=self.error_message,
            duration_ms=duration_ms,
            details=self.details,
            **self.kwargs
        )
        
        await self.audit_logger.log_event(event)
        
        # Don't suppress exceptions
        return False
    
    def add_detail(self, key: str, value: Any):
        """Add detail to the audit event"""
        self.details[key] = value
    
    def set_success(self, success: bool, error_message: Optional[str] = None):
        """Set success status"""
        self.success = success
        self.error_message = error_message


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> Optional[AuditLogger]:
    """Get the global audit logger instance"""
    return _audit_logger


def initialize_audit_logger(**kwargs) -> AuditLogger:
    """Initialize the global audit logger"""
    global _audit_logger
    
    # Default configuration
    config = {
        "log_file": os.getenv("AUDIT_LOG_FILE", "logs/audit.jsonl"),
        "max_memory_events": int(os.getenv("AUDIT_MAX_MEMORY_EVENTS", "10000")),
        "enable_console": os.getenv("AUDIT_ENABLE_CONSOLE", "true").lower() == "true",
        "enable_metrics": os.getenv("AUDIT_ENABLE_METRICS", "true").lower() == "true"
    }
    
    # Override with provided kwargs
    config.update(kwargs)
    
    _audit_logger = AuditLogger(**config)
    
    logger.info("Audit logger initialized", config=config)
    return _audit_logger


# Decorator for auditing function calls
def audit_tool(tool_name: str):
    """Decorator to audit tool calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            audit_logger = get_audit_logger()
            if not audit_logger:
                # No audit logger, just call function
                return await func(*args, **kwargs)
            
            # Extract context from kwargs if available
            session_id = kwargs.get("_session_id")
            user_id = kwargs.get("_user_id")
            account_id = kwargs.get("target_account_id") or kwargs.get("account_id")
            
            # Create audit context
            async with AuditContext(
                audit_logger,
                AuditEventType.TOOL_CALL,
                tool_name=tool_name,
                session_id=session_id,
                user_id=user_id,
                account_id=str(account_id) if account_id else None
            ) as audit_ctx:
                # Add tool arguments (excluding sensitive data)
                safe_args = {k: v for k, v in kwargs.items() 
                           if not k.startswith("_") and k not in ["api_key", "password"]}
                audit_ctx.add_detail("arguments", safe_args)
                
                # Update session activity
                if session_id:
                    audit_logger.update_session_activity(session_id)
                
                # Call the actual function
                result = await func(*args, **kwargs)
                
                # Log success
                audit_ctx.set_success(True)
                
                return result
        
        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator