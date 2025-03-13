"""
Session management utilities for storing conversation history and session data.
"""

from collections import defaultdict
from typing import Dict, List, Any

# Stores conversation for fluid multi-turn chat
session_store = defaultdict(list)

# Stores session data (key-value pairs) like last run ID, last experiment ID, etc.
session_data = defaultdict(dict)

def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """
    Get conversation history for a session.
    
    Args:
        session_id: The unique session identifier
        
    Returns:
        List of conversation messages
    """
    return session_store[session_id]

def append_to_conversation(session_id: str, role: str, content: str) -> None:
    """
    Append a message to the conversation history.
    
    Args:
        session_id: The unique session identifier
        role: Message role (user/assistant)
        content: Message content
    """
    session_store[session_id].append({"role": role, "content": content})

def get_session_data(session_id: str) -> Dict[str, Any]:
    """
    Get session data for a session.
    
    Args:
        session_id: The unique session identifier
        
    Returns:
        Session data dictionary
    """
    if session_id not in session_data:
        session_data[session_id] = {}
    return session_data[session_id]

def set_session_data(session_id: str, key: str, value: Any) -> None:
    """
    Set a key-value pair in the session data.
    
    Args:
        session_id: The unique session identifier
        key: Data key
        value: Data value
    """
    if session_id not in session_data:
        session_data[session_id] = {}
    session_data[session_id][key] = value