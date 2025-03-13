"""
Base LLM provider interface.
All LLM providers should implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of the provider."""
        pass
    
    @property
    @abstractmethod
    def available_models(self) -> List[Dict[str, Any]]:
        """
        Get a list of available models from this provider.
        
        Returns:
            List of dictionaries with model information:
            [
                {
                    "id": "model-id",
                    "name": "User-friendly model name",
                    "max_tokens": 8192,
                    "description": "Short description of the model",
                    "default_temperature": 0.0
                },
                ...
            ]
        """
        pass
    
    @abstractmethod
    def generate_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        model_id: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate a response using the specified LLM model.
        
        Args:
            messages: List of message objects (role, content) to send to the LLM
            model_id: The specific model ID to use
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The generated response text
        """
        pass
    
    @abstractmethod
    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate if the provided API key is valid for this provider.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass