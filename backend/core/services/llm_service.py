"""
Main LLM service module for integration with the application.
Handles model selection and configuration for LLM providers.
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from backend.core.config import settings
from .llm.provider_factory import LLMProviderFactory


def get_available_providers() -> List[Dict[str, Any]]:
    """
    Get a list of available LLM providers.
    
    Returns:
        List of dictionaries with provider information
    """
    return LLMProviderFactory.get_available_providers()


def get_provider_models(provider_id: str, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get available models for a specific provider.
    
    Args:
        provider_id: The ID of the provider
        api_key: Optional API key for the provider
        
    Returns:
        List of dictionaries with model information
    """
    try:
        # If no API key provided, use the default from settings
        if not api_key and provider_id == "openai":
            api_key = settings.OPENAI_API_KEY
        elif not api_key and provider_id == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY
        
        return LLMProviderFactory.get_provider_models(provider_id, api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}")


def generate_chat_response(
    messages: List[Dict[str, str]],
    provider_id: str = "openai",
    model_id: Optional[str] = None,
    api_key: Optional[str] = None,
    api_endpoint: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    **kwargs
) -> str:
    """
    Generate a response using the specified LLM provider and model.
    
    Args:
        messages: List of message objects (role, content)
        provider_id: The LLM provider to use
        model_id: The specific model ID to use
        api_key: Optional API key for the provider
        api_endpoint: Optional API endpoint for self-hosted models
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
        max_tokens: Maximum number of tokens to generate
        **kwargs: Additional provider-specific parameters
        
    Returns:
        The generated response text
    """
    try:
        # If no API key provided, use the default from settings
        if not api_key and provider_id == "openai":
            api_key = settings.OPENAI_API_KEY
        elif not api_key and provider_id == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY
        
        # If no model ID provided, determine the default model for the provider
        if not model_id:
            if provider_id == "openai":
                model_id = "gpt-4o"
            elif provider_id == "anthropic":
                model_id = "claude-3-sonnet-20240229"
            elif provider_id == "llama":
                model_id = "llama3"
        
        # If using Llama and no endpoint is provided, use the default from settings
        if provider_id == "llama" and not api_endpoint:
            api_endpoint = settings.LLAMA_API_ENDPOINT
        
        # Create the provider instance
        provider = LLMProviderFactory.create_provider(
            provider_id=provider_id,
            api_key=api_key,
            api_endpoint=api_endpoint
        )
        
        # Generate the response
        return provider.generate_chat_response(
            messages=messages,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


def validate_provider_credentials(
    provider_id: str,
    api_key: Optional[str] = None,
    api_endpoint: Optional[str] = None
) -> bool:
    """
    Validate credentials for a specific LLM provider.
    
    Args:
        provider_id: The ID of the provider
        api_key: API key to validate
        api_endpoint: API endpoint for self-hosted providers
        
    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        # Create a provider instance
        if provider_id == "llama":
            provider = LLMProviderFactory.create_provider(
                provider_id=provider_id,
                api_key=api_key,
                api_endpoint=api_endpoint
            )
        else:
            provider = LLMProviderFactory.create_provider(
                provider_id=provider_id,
                api_key=api_key
            )
        
        # Validate the API key
        return provider.validate_api_key(api_key)
    except Exception:
        return False