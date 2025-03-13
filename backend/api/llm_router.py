"""
Router for LLM service diagnostics and management.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import requests

from backend.core.services.llm_service import (
    get_available_providers,
    get_provider_models,
    validate_provider_credentials
)
from backend.core.config import settings

router = APIRouter()

@router.get("/status", response_model=Dict[str, Any])
async def check_llm_status():
    """Check the status of connected LLM providers."""
    statuses = {}
    
    # Check OpenAI
    try:
        openai_key = settings.OPENAI_API_KEY
        if openai_key:
            openai_valid = validate_provider_credentials("openai", openai_key)
            statuses["openai"] = {
                "status": "available" if openai_valid else "invalid_credentials",
                "api_configured": True
            }
        else:
            statuses["openai"] = {"status": "not_configured"}
    except Exception as e:
        statuses["openai"] = {"status": "error", "message": str(e)}
    
    # Check Anthropic if available
    try:
        anthropic_key = settings.ANTHROPIC_API_KEY
        if anthropic_key:
            anthropic_valid = validate_provider_credentials("anthropic", anthropic_key)
            statuses["anthropic"] = {
                "status": "available" if anthropic_valid else "invalid_credentials",
                "api_configured": True
            }
        else:
            statuses["anthropic"] = {"status": "not_configured"}
    except Exception as e:
        statuses["anthropic"] = {"status": "error", "message": str(e)}
    
    # Check Llama/Ollama
    try:
        llama_endpoint = settings.LLAMA_API_ENDPOINT
        if llama_endpoint:
            llama_valid = validate_provider_credentials(
                "llama", 
                api_endpoint=llama_endpoint
            )
            
            if llama_valid:
                # Try to get available models
                models = get_provider_models("llama")
                model_names = [m.get("id") for m in models]
                statuses["llama"] = {
                    "status": "available",
                    "endpoint": llama_endpoint,
                    "models": model_names
                }
            else:
                statuses["llama"] = {
                    "status": "endpoint_error",
                    "message": "Endpoint validation failed"
                }
        else:
            statuses["llama"] = {"status": "not_configured"}
    except Exception as e:
        statuses["llama"] = {"status": "error", "message": str(e)}
    
    return {"providers": statuses}

@router.get("/providers", response_model=Dict[str, List[Dict[str, Any]]])
async def list_llm_providers():
    """Get a list of available LLM providers."""
    return {"providers": get_available_providers()}