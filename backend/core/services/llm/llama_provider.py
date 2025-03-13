"""
Self-hosted Llama model provider implementation with enhanced error handling.
"""

import json
import requests
import logging
from typing import List, Dict, Any, Optional
from .base_provider import LLMProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llama_provider")

class LlamaProvider(LLMProvider):
    """Provider for self-hosted Llama models via API endpoint."""
    
    def __init__(self, api_endpoint: str = None, api_key: str = None):
        """
        Initialize the Llama provider.
        
        Args:
            api_endpoint: URL of the Llama API endpoint (e.g., http://localhost:11434/v1)
            api_key: Optional API key for authentication
        """
        self._api_endpoint = api_endpoint
        self._api_key = api_key
        logger.info(f"Initializing LlamaProvider with endpoint: {api_endpoint}")
        
        # Validate endpoint format
        if api_endpoint and not api_endpoint.endswith("/v1"):
            logger.warning(f"API endpoint '{api_endpoint}' might be incorrectly formatted. Expected format: 'http://hostname:port/v1'")
    
    @property
    def provider_name(self) -> str:
        """Get the name of the provider."""
        return "Self-hosted Llama"
    
    @property
    def available_models(self) -> List[Dict[str, Any]]:
        """Get available Llama models."""
        models = [
            {
                "id": "llama3",
                "name": "Llama 3 (8B)",
                "max_tokens": 4096,
                "description": "Efficient 8B parameter Llama 3 model.",
                "default_temperature": 0.0
            },
            {
                "id": "llama-3-70b",
                "name": "Llama 3 (70B)",
                "max_tokens": 4096,
                "description": "Powerful 70B parameter Llama 3 model for complex tasks.",
                "default_temperature": 0.0
            },
            {
                "id": "code-llama",
                "name": "Code Llama",
                "max_tokens": 4096,
                "description": "Specialized model for coding and technical tasks.",
                "default_temperature": 0.0
            }
        ]
        
        # Check if we can get the actual models from Ollama
        if self._api_endpoint:
            try:
                response = requests.get(
                    f"{self._api_endpoint}/models",
                    headers=self._get_headers(),
                    timeout=5
                )
                
                if response.ok:
                    available_models = response.json().get("models", [])
                    if available_models:
                        models = []
                        for model in available_models:
                            model_id = model.get("id", "unknown")
                            models.append({
                                "id": model_id,
                                "name": model_id,
                                "max_tokens": 4096,
                                "description": f"Ollama model: {model_id}",
                                "default_temperature": 0.0
                            })
                        logger.info(f"Found {len(models)} models from Ollama")
            except Exception as e:
                logger.error(f"Error fetching models from Ollama: {str(e)}")
                
        return models
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional authentication."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers
    
    def _format_error_response(self, message: str) -> str:
        """Format an error message as a valid JSON response."""
        error_response = {
            "intent": "error",
            "confirmation": "needs_clarification",
            "message": message
        }
        return json.dumps(error_response)
    
    def generate_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        model_id: str = "llama3",
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate a response using the Llama API."""
        logger.info(f"Generating chat response with model: {model_id}")
        
        # Validate API endpoint
        if not self._api_endpoint:
            error_msg = "Llama API endpoint is not configured. Please set LLAMA_API_ENDPOINT in your environment."
            logger.error(error_msg)
            return self._format_error_response(error_msg)
        
        try:
            # Build the request payload
            payload = {
                "model": model_id,
                "messages": messages,
                "temperature": temperature
            }
            
            # Add optional parameters if provided
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            # Add any additional parameters
            for key, value in kwargs.items():
                payload[key] = value
            
            # Log request details
            logger.info(f"Sending request to {self._api_endpoint}/chat/completions")
            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
            
            # Check if Ollama is running before making the request
            try:
                health_check = requests.get(
                    # Ollama doesn't have a dedicated health endpoint, so we just check the base URL
                    self._api_endpoint.replace("/v1", ""), 
                    timeout=3
                )
                if not health_check.ok:
                    error_msg = f"Ollama server not responding properly (status: {health_check.status_code})"
                    logger.error(error_msg)
                    return self._format_error_response(error_msg)
            except requests.RequestException as e:
                error_msg = f"Ollama server not available: {str(e)}"
                logger.error(error_msg)
                return self._format_error_response(
                    "Llama API endpoint not found. Please make sure Ollama is running on the correct port."
                )
            
            # Make the API request
            response = requests.post(
                f"{self._api_endpoint}/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=120  # Longer timeout for self-hosted models
            )
            
            # Handle HTTP errors
            if not response.ok:
                error_msg = f"Llama API returned error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                if response.status_code == 404:
                    return self._format_error_response(
                        "Llama model endpoint not found. Make sure the model is available in Ollama (try 'ollama list')."
                    )
                return self._format_error_response(error_msg)
            
            # Parse the response
            result = response.json()
            logger.debug(f"Response: {json.dumps(result, indent=2)}")
            
            # Extract response content
            try:
                content = result["choices"][0]["message"]["content"].strip()
                
                # Check if content is already in JSON format
                try:
                    json.loads(content)
                    # If it parses as JSON, return it directly
                    return content
                except json.JSONDecodeError:
                    # Not JSON, wrap it in our standard format
                    mlflow_response = {
                        "intent": "other_intent",
                        "confirmation": "confirmed",
                        "message": content
                    }
                    return json.dumps(mlflow_response)
            except (KeyError, IndexError) as e:
                error_msg = f"Unexpected response format from Llama API: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Response was: {json.dumps(result, indent=2)}")
                return self._format_error_response(error_msg)
                
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error to Llama API: {str(e)}"
            logger.error(error_msg)
            return self._format_error_response(
                "Could not connect to Llama API. Please ensure Ollama is running."
            )
        except requests.exceptions.Timeout as e:
            error_msg = f"Request to Llama API timed out: {str(e)}"
            logger.error(error_msg)
            return self._format_error_response(
                "Request to Llama API timed out. The model might be loading or the server is overloaded."
            )
        except Exception as e:
            error_msg = f"Unexpected error with Llama API: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            return self._format_error_response(f"Llama API Error: {str(e)}")
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate access to the Llama API.
        
        For self-hosted models, this checks connectivity rather than a specific API key.
        """
        if not self._api_endpoint:
            return False
        
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            logger.info(f"Validating connection to Llama API at {self._api_endpoint}")
            
            # Try to access the models endpoint to verify connectivity
            response = requests.get(
                f"{self._api_endpoint}/models",
                headers=headers,
                timeout=10
            )
            
            is_valid = response.status_code == 200
            logger.info(f"Llama API connection validation: {'Success' if is_valid else 'Failed'}")
            return is_valid
        except Exception as e:
            logger.error(f"Error validating Llama API connection: {str(e)}")
            return False