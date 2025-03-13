"""
Router for invitation code management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from backend.models.invitation import invitation_store


router = APIRouter()


class InvitationRequest(BaseModel):
    """Request model for validating invitation codes."""
    code: str
    session_id: str


class InvitationResponse(BaseModel):
    """Response model for invitation code validation."""
    valid: bool
    message: str
    remaining_requests: Optional[int] = None
    max_requests: Optional[int] = None


@router.post("/validate", response_model=InvitationResponse)
async def validate_invitation_code(request: InvitationRequest):
    """
    Validate an invitation code for a session.
    
    Args:
        request: The invitation code and session ID
        
    Returns:
        Validation result with remaining requests if valid
    """
    result = invitation_store.validate_code(request.code, request.session_id)
    
    # Convert to response model
    response = InvitationResponse(
        valid=result["valid"],
        message=result["message"]
    )
    
    # Add optional fields if valid
    if result["valid"]:
        response.remaining_requests = result["remaining_requests"]
        response.max_requests = result["max_requests"]
    
    return response


@router.post("/use", response_model=InvitationResponse)
async def use_invitation_request(request: InvitationRequest):
    """
    Use a request from an invitation code's quota.
    
    Args:
        request: The invitation code and session ID
        
    Returns:
        Updated remaining requests
        
    Raises:
        HTTPException: If the code is invalid or has no remaining requests
    """
    # validate the invitation code
    validation = invitation_store.validate_code(request.code, request.session_id)
    if not validation["valid"]:
        raise HTTPException(status_code=403, detail=validation["message"])
    remaining = invitation_store.use_request(request.code, request.session_id)
    return InvitationResponse(
        valid=True,
        message=f"Request used successfully. {remaining} requests remaining.",
        remaining_requests=remaining,
        max_requests=validation["max_requests"]
    )


# For admin/development purposes only - should be protected in production
@router.post("/create")
async def create_invitation():
    """Create a new invitation code (for development/testing only)."""
    code = invitation_store.create_invitation_code()
    return {"code": code}