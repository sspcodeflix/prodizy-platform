"""
Models and utilities for invitation code management.
"""

from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import time
import uuid
import hashlib


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
    """Store and manage invitation codes."""
    
    def __init__(self):
        """Initialize the invitation store."""
        self._invitations: Dict[str, InvitationCode] = {}
        
        # Add some default invitation codes for development
        self.create_invitation_code(max_requests=10, expiry_seconds=3600)
        self.create_invitation_code(max_requests=20, expiry_seconds=7200)
    
    def create_invitation_code(self, max_requests: int = 10, expiry_seconds: int = 3600) -> str:
        """
        Create a new invitation code.
        
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
        invitation = InvitationCode(
            code=code,
            created_at=now,
            expires_at=now + expiry_seconds,
            max_requests=max_requests,
            remaining_requests=max_requests
        )
        
        self._invitations[code] = invitation
        return code
    
    def validate_code(self, code: str, session_id: str) -> Dict[str, any]:
        """
        Validate an invitation code and return its status.
        
        Args:
            code: The invitation code to validate
            session_id: The session ID using this code
            
        Returns:
            Dictionary with validation status:
            {
                "valid": bool,
                "message": str,
                "remaining_requests": int (if valid),
                "max_requests": int (if valid)
            }
        """
        # Check if code exists
        if code not in self._invitations:
            return {"valid": False, "message": "Invalid invitation code."}
        
        invitation = self._invitations[code]
        
        # Check if code is active
        if not invitation.is_active:
            return {"valid": False, "message": "This invitation code has been deactivated."}
        
        # Check if code has expired
        if time.time() > invitation.expires_at:
            return {"valid": False, "message": "This invitation code has expired."}
        
        # Check if the session has already used this code
        new_session = session_id not in invitation.used_by_sessions
        
        # If it's a new session but the code has no remaining requests
        if new_session and invitation.remaining_requests <= 0:
            return {"valid": False, "message": "This invitation code has reached its request limit."}
        
        # Code is valid
        return {
            "valid": True,
            "message": "Valid invitation code.",
            "remaining_requests": invitation.remaining_requests,
            "max_requests": invitation.max_requests,
            "new_session": new_session
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
        if code not in self._invitations:
            return None
        
        invitation = self._invitations[code]
        
        # Add session to used sessions if not already there
        if session_id not in invitation.used_by_sessions:
            invitation.used_by_sessions.append(session_id)
        
        # Decrement remaining requests
        if invitation.remaining_requests > 0:
            invitation.remaining_requests -= 1
        
        # Update the invitation in the store
        self._invitations[code] = invitation
        
        return invitation.remaining_requests
    
    def get_invitation(self, code: str) -> Optional[InvitationCode]:
        """Get the invitation code object."""
        return self._invitations.get(code)


# Create a global invitation store instance
invitation_store = InvitationStore()