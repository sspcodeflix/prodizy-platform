"""
Anthropic (Claude) LLM provider implementation.
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from .base_provider import LLMProvider

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider implementation."""
    
    def __init__(self, api_key: str = None):
        """Initialize the Anthropic provider with an API key."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "Anthropic Python SDK is not installed. "
                "Please install it with: pip install anthropic"
            )
        
        self._api_key = api_key
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None
    
    @property
    def provider_name(self) -> str:
        """Get the name of the provider."""
        return "Anthropic (Claude)"
    
    @property
    def available_models(self) -> List[Dict[str, Any]]:
        """Get available Anthropic Claude models."""
        return [
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "max_tokens": 4096,
                "description": "Most powerful Claude model for complex tasks requiring deep expertise.",
                "default_temperature": 0.0
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "max_tokens": 4096,
                "description": "Balanced model for most tasks with excellent performance.",
                "default_temperature": 0.0
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "max_tokens": 4096,
                "description": "Fastest and most compact Claude model for responsive applications.",
                "default_temperature": 0.0
            },
            {
                "id": "claude-3.5-sonnet-20240620",
                "name": "Claude 3.5 Sonnet",
                "max_tokens": 8192,
                "description": "Latest Claude model with enhanced reasoning capabilities.",
                "default_temperature": 0.0
            }
        ]
    
    def generate_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        model_id: str = "claude-3-sonnet-20240229",
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate a response using Anthropic's Claude API."""
        if not self.client:
            raise ValueError("Anthropic client is not initialized. Please provide a valid API key.")
        
        try:
            # Convert messages from OpenAI format to Anthropic format
            anthropic_messages = self._convert_messages(messages)
            
            # Build request parameters
            request_params = {
                "model": model_id,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
            }
            
            # Add any additional Anthropic-specific parameters
            for key, value in kwargs.items():
                if key not in request_params:
                    request_params[key] = value
            
            # Call the Anthropic API
            response = self.client.messages.create(**request_params)
            
            # Extract and return the response text
            return response.content[0].text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Anthropic API Error: {str(e)}")
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate Anthropic API key by testing a simple request."""
        if not ANTHROPIC_AVAILABLE:
            return False
        
        try:
            # Create a temporary client with the API key
            temp_client = anthropic.Anthropic(api_key=api_key)
            
            # List available models to verify the key works
            temp_client.models.list()
            return True
        except Exception:
            return False
    
    def _convert_messages(self, openai_messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Convert messages from OpenAI format to Anthropic format."""
        anthropic_messages = []
        
        for message in openai_messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                # System messages are treated differently in Anthropic
                anthropic_messages.append({
                    "role": "user",
                    "content": f"<system>\n{content}\n</system>"
                })
            elif role == "user":
                anthropic_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                anthropic_messages.append({"role": "assistant", "content": content})
            # Skip 'function' role messages as Anthropic doesn't support them directly
        
        return anthropic_messages