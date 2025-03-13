"""
OpenAI LLM provider implementation.
"""

import openai
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from .base_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""
    
    def __init__(self, api_key: str = None):
        """Initialize the OpenAI provider with an API key."""
        if api_key:
            openai.api_key = api_key
        self._api_key = api_key
    
    @property
    def provider_name(self) -> str:
        """Get the name of the provider."""
        return "OpenAI"
    
    @property
    def available_models(self) -> List[Dict[str, Any]]:
        """Get available OpenAI models."""
        return [
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "max_tokens": 8192,
                "description": "Most capable model for complex tasks, reasoning, and creative content.",
                "default_temperature": 0.0
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "max_tokens": 4096,
                "description": "Improved version of GPT-4 with better performance.",
                "default_temperature": 0.0
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "max_tokens": 4096,
                "description": "Good balance of capability and cost efficiency.",
                "default_temperature": 0.0
            }
        ]
    
    def generate_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        model_id: str = "gpt-4o",
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate a response using OpenAI's API."""
        try:
            request_params = {
                "model": model_id,
                "messages": messages,
                "temperature": temperature
            }
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            for key, value in kwargs.items():
                request_params[key] = value
            response = openai.ChatCompletion.create(**request_params)
            return response.choices[0].message["content"].strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OpenAI Error: {str(e)}")
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate OpenAI API key by testing a simple request."""
        original_key = openai.api_key
        try:
            openai.api_key = api_key
            openai.Model.list(limit=1)
            return True
        except Exception:
            return False
        finally:
            openai.api_key = original_key