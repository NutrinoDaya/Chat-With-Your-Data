"""
Utility modules for the Chat-With-Your-Data backend.

This package contains modular utility functions that support the main application logic.
Each module has a specific responsibility to maintain clean code architecture.

Modules:
- query_detection: Query intent, source, and mode detection
- sql_generation: SQL query building and processing 
- response_formatting: Result formatting and presentation
- conversation_manager: Session and conversation history management
- rag_processing: RAG query processing and context handling
- health_checks: System health monitoring utilities
"""

__version__ = "1.0.0"
__author__ = "Chat-With-Your-Data Team"

# Import key functions for easy access
from .query_detection import (
    detect_source_from_query,
    detect_mode_from_query,
    is_greeting_or_social,
    get_greeting_response
)

from .sql_generation import (
    build_rule_sql,
    extract_limit_number,
    add_limit_to_llm_sql
)

from .response_formatting import (
    format_sql_result,
    create_table_response
)

from .conversation_manager import (
    add_message_to_history,
    get_conversation_history,
    build_conversation_context
)

__all__ = [
    # Query detection
    "detect_source_from_query",
    "detect_mode_from_query", 
    "is_greeting_or_social",
    "get_greeting_response",
    
    # SQL generation
    "build_rule_sql",
    "extract_limit_number",
    "add_limit_to_llm_sql",
    
    # Response formatting
    "format_sql_result",
    "create_table_response",
    
    # Conversation management
    "add_message_to_history",
    "get_conversation_history",
    "build_conversation_context"
]
