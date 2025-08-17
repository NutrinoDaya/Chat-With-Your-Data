"""
Conversation Management Utilities

This module handles conversation history, session management, and context building
for maintaining conversational state across chat interactions.
"""

from typing import Dict, List, Any
from datetime import datetime


# Store conversation history per session (in production, use Redis or DB)
conversation_history: Dict[str, List[Dict[str, Any]]] = {}


def add_message_to_history(session_id: str, message: str, role: str = "user") -> None:
    """
    Add a message to conversation history for a session.
    
    Args:
        session_id: Session identifier
        message: Message content
        role: Message role ('user' or 'assistant')
    """
    if session_id not in conversation_history:
        conversation_history[session_id] = []
    
    conversation_history[session_id].append({
        "role": role,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only last 10 messages for context
    if len(conversation_history[session_id]) > 10:
        conversation_history[session_id] = conversation_history[session_id][-10:]


def get_conversation_history(session_id: str) -> List[Dict[str, Any]]:
    """
    Get conversation history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of conversation messages
    """
    return conversation_history.get(session_id, [])


def clear_conversation_history(session_id: str) -> bool:
    """
    Clear conversation history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        True if history was cleared, False if session didn't exist
    """
    if session_id in conversation_history:
        del conversation_history[session_id]
        return True
    return False


def build_conversation_context(session_id: str, max_messages: int = 3) -> str:
    """
    Build conversation context string from recent messages.
    
    Args:
        session_id: Session identifier
        max_messages: Maximum number of recent messages to include
        
    Returns:
        Formatted conversation context string
    """
    messages = conversation_history.get(session_id, [])
    if not messages:
        return ""
    
    recent_messages = messages[-max_messages:]
    context_lines = []
    
    for msg in recent_messages:
        role = msg['role'].capitalize()
        message = msg['message']
        context_lines.append(f"{role}: {message}")
    
    return "\n".join(context_lines)


def create_cache_key(message: str, source: str, mode: str, session_id: str) -> str:
    """
    Create a cache key that includes conversation context.
    
    Args:
        message: User message
        source: Data source
        mode: Response mode
        session_id: Session identifier
        
    Returns:
        Cache key string
    """
    # Include recent conversation context in cache key
    recent_messages = conversation_history.get(session_id, [])[-3:]
    recent_context = " ".join([msg["message"] for msg in recent_messages])
    
    return f"{message}|{source}|{mode}|{hash(recent_context) % 10000}"


def get_session_stats() -> Dict[str, Any]:
    """
    Get statistics about active conversation sessions.
    
    Returns:
        Dictionary with session statistics
    """
    total_sessions = len(conversation_history)
    total_messages = sum(len(messages) for messages in conversation_history.values())
    
    active_sessions = sum(1 for messages in conversation_history.values() 
                         if messages and 
                         (datetime.now() - datetime.fromisoformat(messages[-1]["timestamp"])).days < 1)
    
    return {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "total_messages": total_messages,
        "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0
    }
