"""
API client utilities for communicating with the backend.
"""

import requests
from typing import Dict, Any

def chat_with_bot(query: str, session_id: str, api_url: str, api_key: str) -> Dict[str, Any]:
    """
    Send a chat query to the Prodizy Platform API.
    
    Args:
        query: The user's query text
        session_id: The session identifier
        api_url: The API base URL
        api_key: The API key for authorization
        
    Returns:
        The assistant's response data as a dictionary
    """
    payload = {
        "session_id": session_id,
        "query": query,
        "invitation_code": "streamlit-user"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.post(
            f"{api_url}chat/mlflow",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
    except requests.RequestException as e:
        # Return an error-like dict
        return {
            "intent": "error",
            "confirmation": "needs_clarification",
            "message": f"❌ Error: {str(e)}"
        }

    # Parse JSON and return the assistant_response object
    response_json = response.json()
    assistant_response = response_json.get("assistant_response", {})
    return assistant_response