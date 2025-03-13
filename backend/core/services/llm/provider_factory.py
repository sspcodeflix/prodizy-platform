"""
Factory for creating LLM provider instances.
"""

from typing import Dict, List, Optional, Any
from .base_provider import LLMProvider
from .openai_provider import OpenAIProvider

# Conditionally import other providers
try:
    from .anthropic_provider import AnthropicProvider
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from .llama_provider import LlamaProvider
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False


class LLMProviderFactory:
    """Factory for creating and managing LLM provider instances."""
    
    # Mapping of provider IDs to their implementation classes
    _provider_classes = {
        "openai": OpenAIProvider
    }
    
    # Initialize optional providers
    if ANTHROPIC_AVAILABLE:
        _provider_classes["anthropic"] = AnthropicProvider
    
    if LLAMA_AVAILABLE:
        _provider_classes["llama"] = LlamaProvider
    
    # Cache of provider instances
    _provider_instances: Dict[str, LLMProvider] = {}
    
    @classmethod
    def get_available_providers(cls) -> List[Dict[str, Any]]:
        """
        Get a list of available LLM providers.
        
        Returns:
            List of dictionaries with provider information
        """
        providers = []
        
        # OpenAI is always available
        providers.append({
            "id": "openai",
            "name": "OpenAI",
            "description": "GPT models from OpenAI (GPT-4o, GPT-4, GPT-3.5)",
            "requires_api_key": True
        })
        
        # Add Anthropic if available
        if ANTHROPIC_AVAILABLE:
            providers.append({
                "id": "anthropic",
                "name": "Anthropic",
                "description": "Claude models from Anthropic (Claude 3, Claude 3.5)",
                "requires_api_key": True
            })
        
        # Add Llama if available
        if LLAMA_AVAILABLE:
            providers.append({
                "id": "llama",
                "name": "Self-hosted Llama",
                "description": "Self-hosted Llama models via API endpoint",
                "requires_api_key": False,
                "requires_endpoint": True
            })
        
        return providers
    
    @classmethod
    def create_provider(
        cls, 
        provider_id: str, 
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """
        Create or retrieve a provider instance.
        
        Args:
            provider_id: The ID of the provider to create
            api_key: API key for the provider
            api_endpoint: API endpoint for self-hosted providers
            **kwargs: Additional provider-specific parameters
            
        Returns:
            An instance of the requested LLM provider
            
        Raises:
            ValueError: If the provider ID is unknown
        """
        # Check if the provider ID is valid
        if provider_id not in cls._provider_classes:
            raise ValueError(f"Unknown provider ID: {provider_id}")
        
        # Create a unique cache key that includes the provider ID and API key
        cache_key = f"{provider_id}:{api_key}:{api_endpoint}"
        
        # Return cached instance if available
        if cache_key in cls._provider_instances:
            return cls._provider_instances[cache_key]
        
        # Create provider instance based on type
        provider_class = cls._provider_classes[provider_id]
        
        if provider_id == "llama":
            # Llama provider requires an API endpoint
            provider = provider_class(api_endpoint=api_endpoint, api_key=api_key, **kwargs)
        else:
            # Standard API key-based providers
            provider = provider_class(api_key=api_key, **kwargs)
        
        # Cache the provider instance
        cls._provider_instances[cache_key] = provider
        
        return provider
    
    @classmethod
    def get_provider_models(cls, provider_id: str, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available models for a specific provider.
        
        Args:
            provider_id: The ID of the provider
            api_key: Optional API key for authenticated providers
            
        Returns:
            List of dictionaries with model information
            
        Raises:
            ValueError: If the provider ID is unknown
        """
        provider = cls.create_provider(provider_id, api_key)
        return provider.available_models