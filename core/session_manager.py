from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a conversation session with context"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=lambda: {
        "account": None,
        "current_entity": None,
        "time_range": "SINCE 1 hour ago",
        "comparison_time_range": None,
        "active_incidents": [],
        "recent_queries": [],
        "entity_cache": {},  # Cache recently accessed entities
        "metric_cache": {},  # Cache recent metric queries
        "preferences": {
            "output_format": "concise",
            "include_charts": False,
            "timezone": "UTC"
        }
    })
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def set_context(self, key: str, value: Any):
        """Set a context value
        
        Args:
            key: Context key
            value: Value to set
        """
        self.context[key] = value
        self.update_activity()
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Context value or default
        """
        return self.context.get(key, default)
    
    def add_recent_query(self, query: str, result: Any):
        """Add a query to recent history
        
        Args:
            query: Query string (NRQL or description)
            result: Query result
        """
        recent = self.context.get("recent_queries", [])
        recent.insert(0, {
            "query": query,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Keep only last 10 queries
        self.context["recent_queries"] = recent[:10]
        self.update_activity()
    
    def cache_entity(self, guid: str, entity_data: Dict[str, Any]):
        """Cache entity data
        
        Args:
            guid: Entity GUID
            entity_data: Entity information
        """
        cache = self.context.get("entity_cache", {})
        cache[guid] = {
            "data": entity_data,
            "cached_at": datetime.utcnow().isoformat()
        }
        # Limit cache size
        if len(cache) > 50:
            # Remove oldest entries
            sorted_items = sorted(cache.items(), key=lambda x: x[1]["cached_at"])
            cache = dict(sorted_items[-50:])
        self.context["entity_cache"] = cache
    
    def get_cached_entity(self, guid: str, max_age_minutes: int = 5) -> Optional[Dict[str, Any]]:
        """Get cached entity data if fresh enough
        
        Args:
            guid: Entity GUID
            max_age_minutes: Maximum cache age in minutes
            
        Returns:
            Cached entity data or None if not found/stale
        """
        cache = self.context.get("entity_cache", {})
        if guid not in cache:
            return None
        
        cached = cache[guid]
        cached_time = datetime.fromisoformat(cached["cached_at"])
        if datetime.utcnow() - cached_time > timedelta(minutes=max_age_minutes):
            return None
        
        return cached["data"]


class SessionManager:
    """Manages conversation sessions"""
    
    def __init__(self, ttl_hours: int = 24):
        """Initialize session manager
        
        Args:
            ttl_hours: Session time-to-live in hours
        """
        self.sessions: Dict[str, Session] = {}
        self.ttl = timedelta(hours=ttl_hours)
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        """Get existing session or create new one
        
        Args:
            session_id: Optional session ID to retrieve
            
        Returns:
            Session instance
        """
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            if datetime.utcnow() - session.last_activity < self.ttl:
                session.update_activity()
                logger.debug(f"Retrieved existing session: {session_id}")
                return session
            else:
                # Session expired
                logger.info(f"Session {session_id} expired, creating new one")
                del self.sessions[session_id]
        
        # Create new session
        session = Session(session_id)
        self.sessions[session.id] = session
        logger.info(f"Created new session: {session.id}")
        
        # Clean up old sessions
        self._cleanup_expired()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID without creating
        
        Args:
            session_id: Session ID
            
        Returns:
            Session or None if not found/expired
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        if datetime.utcnow() - session.last_activity >= self.ttl:
            # Expired
            del self.sessions[session_id]
            return None
        
        return session
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions
        
        Returns:
            List of session summaries
        """
        now = datetime.utcnow()
        active = []
        
        for sid, session in list(self.sessions.items()):
            if now - session.last_activity < self.ttl:
                active.append({
                    "id": sid,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "account": session.get_context("account"),
                    "current_entity": session.get_context("current_entity")
                })
            else:
                # Remove expired
                del self.sessions[sid]
        
        return active
    
    def _cleanup_expired(self):
        """Remove expired sessions"""
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self.sessions.items()
            if now - session.last_activity > self.ttl
        ]
        
        for sid in expired:
            logger.debug(f"Removing expired session: {sid}")
            del self.sessions[sid]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    def clear_all_sessions(self):
        """Clear all sessions (useful for testing or admin)"""
        count = len(self.sessions)
        self.sessions.clear()
        logger.info(f"Cleared {count} sessions")