"""
Pydantic models for chat requests and responses.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class ChatRequest(BaseModel):
    """
    Model for chat request data.
    """
    session_id: str
    query: str
    invitation_code: str
    cached_intent: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """
    Model for chat response data.
    """
    assistant_response: Dict[str, Any]