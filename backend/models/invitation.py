"""
Models and utilities for invitation code management using SQLite.
"""

from pydantic import BaseModel
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import time
import uuid
import hashlib
import sqlite3
import json
import os


class InvitationCode(BaseModel):
    """Model representing an invitation code."""

    code: str
    created_at: float  # Unix timestamp
    expires_at: float  # Unix timestamp
    max_requests: int = 10
    remaining_requests: int = 10
    is_active: bool = True
    used_by_sessions: List[str] = []


class InvitationStore:
    """Store and manage invitation codes using SQLite."""

    def __init__(self, db_path="invitation_store.db"):
        """Initialize the invitation store with SQLite database."""
        self.db_path = db_path
        self._init_db()

        # Add a default invitation code if the database is empty
        if not self._get_all_codes():
            self.create_invitation_code(max_requests=10, expiry_seconds=3600)

    def _init_db(self):
        """Initialize the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create the invitations table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invitations (
            code TEXT PRIMARY KEY,
            created_at REAL,
            expires_at REAL,
            max_requests INTEGER,
            remaining_requests INTEGER,
            is_active INTEGER,
            used_by_sessions TEXT
        )
        """)

        conn.commit()
        conn.close()

    def _get_all_codes(self):
        """Get all invitation codes from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM invitations")
        codes = cursor.fetchall()
        conn.close()
        return [code[0] for code in codes]

    def create_invitation_code(
        self, max_requests: int = 10, expiry_seconds: int = 3600
    ) -> str:
        """
        Create a new invitation code and store it in the database.

        Args:
            max_requests: Maximum number of requests allowed with this code
            expiry_seconds: Number of seconds until the code expires

        Returns:
            The generated invitation code
        """
        # Generate a unique code
        raw_code = str(uuid.uuid4())
        # Create a shorter hashed version (first 8 chars of SHA-256)
        code = hashlib.sha256(raw_code.encode()).hexdigest()[:8]

        now = time.time()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO invitations VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                code,
                now,
                now + expiry_seconds,
                max_requests,
                max_requests,
                1,  # is_active (1 = True)
                json.dumps([]),  # used_by_sessions as JSON
            ),
        )

        conn.commit()
        conn.close()

        return code

    def validate_code(self, code: str, session_id: str) -> Dict[str, Any]:
        """
        Validate an invitation code and return its status.

        Args:
            code: The invitation code to validate
            session_id: The session ID using this code

        Returns:
            Dictionary with validation status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if code exists
        cursor.execute("SELECT * FROM invitations WHERE code = ?", (code,))
        invitation_data = cursor.fetchone()

        if not invitation_data:
            conn.close()
            return {"valid": False, "message": "Invalid invitation code."}

        # Unpack data
        (
            code,
            created_at,
            expires_at,
            max_requests,
            remaining_requests,
            is_active,
            used_by_sessions_json,
        ) = invitation_data

        is_active = bool(is_active)
        used_by_sessions = json.loads(used_by_sessions_json)

        # Check if code is active
        if not is_active:
            conn.close()
            return {
                "valid": False,
                "message": "This invitation code has been deactivated.",
            }

        # Check if code has expired
        if time.time() > expires_at:
            conn.close()
            return {"valid": False, "message": "This invitation code has expired."}

        # Check if the session has already used this code
        new_session = session_id not in used_by_sessions

        # If it's a new session but the code has no remaining requests
        if new_session and remaining_requests <= 0:
            conn.close()
            return {
                "valid": False,
                "message": "This invitation code has reached its request limit.",
            }

        conn.close()
        # Code is valid
        return {
            "valid": True,
            "message": "Valid invitation code.",
            "remaining_requests": remaining_requests,
            "max_requests": max_requests,
            "new_session": new_session,
        }

    def use_request(self, code: str, session_id: str) -> Optional[int]:
        """
        Decrement the remaining requests for a code and return the new count.

        Args:
            code: The invitation code
            session_id: The session ID using the code

        Returns:
            The number of remaining requests, or None if the code is invalid
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get the current invitation data
        cursor.execute(
            "SELECT remaining_requests, used_by_sessions FROM invitations WHERE code = ?",
            (code,),
        )
        result = cursor.fetchone()

        if not result:
            conn.close()
            return None

        remaining_requests, used_by_sessions_json = result
        used_by_sessions = json.loads(used_by_sessions_json)

        # Add session to used sessions if not already there
        if session_id not in used_by_sessions:
            used_by_sessions.append(session_id)

        # Decrement remaining requests
        if remaining_requests > 0:
            remaining_requests -= 1

        # Update the invitation in the database
        cursor.execute(
            "UPDATE invitations SET remaining_requests = ?, used_by_sessions = ? WHERE code = ?",
            (remaining_requests, json.dumps(used_by_sessions), code),
        )

        conn.commit()
        conn.close()

        return remaining_requests

    def get_invitation(self, code: str) -> Optional[InvitationCode]:
        """Get the invitation code object from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM invitations WHERE code = ?", (code,))
        invitation_data = cursor.fetchone()

        conn.close()

        if not invitation_data:
            return None

        # Unpack data and convert to InvitationCode model
        (
            code,
            created_at,
            expires_at,
            max_requests,
            remaining_requests,
            is_active,
            used_by_sessions_json,
        ) = invitation_data

        return InvitationCode(
            code=code,
            created_at=created_at,
            expires_at=expires_at,
            max_requests=max_requests,
            remaining_requests=remaining_requests,
            is_active=bool(is_active),
            used_by_sessions=json.loads(used_by_sessions_json),
        )


invitation_store = InvitationStore(
    db_path=os.getenv("INVITATION_DB_PATH", "invitation_store.db")
)
