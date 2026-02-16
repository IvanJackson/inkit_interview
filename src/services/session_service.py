"""Session management service."""

import hashlib
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from src.models.session import SessionContext


class SessionService:
    """Thread-safe service for session management with persistence."""

    def __init__(self, session_timeout_hours: int = 24):
        """Initialize session service.

        Args:
            session_timeout_hours: Session timeout in hours (default: 24)
        """
        self.session_timeout_hours = session_timeout_hours
        self._sessions: Dict[str, SessionContext] = {}
        self._expired_sessions: Dict[str, SessionContext] = {}  # For restoration
        self._lock = threading.RLock()

    def create_session(self, browser_device_id: str) -> SessionContext:
        """Create a new session.

        Args:
            browser_device_id: Browser/device fingerprint

        Returns:
            New SessionContext instance
        """
        session = SessionContext(
            session_id=str(uuid.uuid4()),
            browser_device_id=browser_device_id,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            authenticated=True,  # Cookie-based identity (Phase 1)
        )

        with self._lock:
            self._sessions[session.session_id] = session

        return session

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Retrieve session and check for expiry.

        Args:
            session_id: Session ID

        Returns:
            SessionContext or None if not found/expired
        """
        with self._lock:
            session = self._sessions.get(session_id)

            if not session:
                return None

            # Check expiry
            if session.is_expired(self.session_timeout_hours):
                # Move to expired sessions for potential restoration
                self._persist_expired_session(session)
                del self._sessions[session_id]
                return None

            return session

    def update_session(self, session: SessionContext) -> None:
        """Update session and touch last_activity timestamp.

        Args:
            session: Session to update
        """
        with self._lock:
            session.touch()
            self._sessions[session.session_id] = session

    def get_or_create_session(
        self, session_id: Optional[str], browser_device_id: str
    ) -> SessionContext:
        """Get existing session or create new one.

        Args:
            session_id: Existing session ID (optional)
            browser_device_id: Browser/device fingerprint

        Returns:
            SessionContext instance
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                # Validate device match
                if session.browser_device_id != browser_device_id:
                    # Device switch - require re-authentication
                    session.authenticated = False

                return session

        # Create new session
        return self.create_session(browser_device_id)

    def restore_session(
        self, session_id: str, browser_device_id: str
    ) -> Optional[SessionContext]:
        """Restore an expired session.

        Args:
            session_id: Session ID to restore
            browser_device_id: Browser/device fingerprint for validation

        Returns:
            Restored SessionContext or None if not found or device mismatch
        """
        with self._lock:
            expired_session = self._expired_sessions.get(session_id)

            if not expired_session:
                return None

            # Validate device match
            if expired_session.browser_device_id != browser_device_id:
                # Different device - require re-authentication
                return None

            # Restore session
            restored = SessionContext(
                session_id=expired_session.session_id,
                current_image_id=expired_session.current_image_id,
                conversation_topic=expired_session.conversation_topic,
                browser_device_id=expired_session.browser_device_id,
                created_at=expired_session.created_at,
                last_activity=datetime.utcnow(),  # Reset activity
                authenticated=True,
                expired=False,
            )

            # Move back to active sessions
            self._sessions[restored.session_id] = restored
            del self._expired_sessions[session_id]

            return restored

    def generate_browser_device_id(
        self, user_agent: str, accept_language: str = "", remote_addr: str = ""
    ) -> str:
        """Generate browser/device fingerprint for tab isolation.

        Args:
            user_agent: User-Agent header
            accept_language: Accept-Language header
            remote_addr: Remote IP address

        Returns:
            Unique device ID hash
        """
        fingerprint = f"{user_agent}|{accept_language}|{remote_addr}"
        return hashlib.sha256(fingerprint.encode()).hexdigest()[:32]

    def _persist_expired_session(self, session: SessionContext) -> None:
        """Persist expired session for potential restoration (internal).

        Args:
            session: Session to persist
        """
        session.expired = True
        self._expired_sessions[session.session_id] = session

    def validate_device(
        self, session: SessionContext, current_device_id: str
    ) -> bool:
        """Validate device match for security.

        Args:
            session: Session to validate
            current_device_id: Current device fingerprint

        Returns:
            True if device matches
        """
        return session.browser_device_id == current_device_id
