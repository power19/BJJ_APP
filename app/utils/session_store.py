from datetime import datetime
from typing import Dict, Optional

class SessionStore:
    _instance = None
    _sessions: Dict[str, dict] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionStore, cls).__new__(cls)
        return cls._instance

    def create_session(self, session_id: str, data: dict) -> None:
        """Create a new session"""
        self._sessions[session_id] = {
            **data,
            "created_at": datetime.now()
        }
        print(f"Created session {session_id} in store")

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session if it exists and hasn't expired"""
        session = self._sessions.get(session_id)
        if not session:
            print(f"No session found in store: {session_id}")
            return None

        # Check if session has expired (30 minutes)
        if (datetime.now() - session["created_at"]).total_seconds() > 1800:
            print(f"Session expired in store: {session_id}")
            self._sessions.pop(session_id, None)
            return None

        return session

    def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        self._sessions.pop(session_id, None)

# Create a global instance
session_store = SessionStore()