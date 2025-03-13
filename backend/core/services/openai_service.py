"""
Service module for OpenAI API interactions.
Handles generating chat responses using the OpenAI API.
"""

import openai
from typing import List, Dict
from fastapi import HTTPException
from backend.core.config import settings

# Configure OpenAI with API key from settings
openai.api_key = settings.OPENAI_API_KEY

def generate_chat_response(messages: List[Dict[str, str]]) -> str:
    """
    Generate a response using OpenAI's API.
    
    Args:
        messages: List of message objects (role, content) to send to OpenAI
        
    Returns:
        The generated response text
        
    Raises:
        HTTPException: If there's an error with the OpenAI API
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.0
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI Error: {str(e)}")