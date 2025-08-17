"""
Query Detection Utilities

This module contains functions for detecting query intent, source, and mode
from user messages to route them to appropriate handlers.
"""

import re
from typing import Optional


def detect_source_from_query(message: str) -> str:
    """
    Detect data source from user query based on keywords.
    
    Args:
        message: User query string
        
    Returns:
        Source identifier: 'financial' or 'devices'
    """
    m = message.lower()
    
    # Financial keywords
    financial_keywords = [
        "order", "orders", "revenue", "sales", "customer", "customers", "payment", "paid", 
        "amount", "money", "price", "invoice", "billing", "financial", "transaction"
    ]
    
    # Device keywords  
    device_keywords = [
        "device", "devices", "sensor", "sensors", "uptime", "online", "offline", 
        "status", "location", "iot", "telemetry", "metrics", "monitoring"
    ]
    
    financial_score = sum(1 for k in financial_keywords if k in m)
    device_score = sum(1 for k in device_keywords if k in m)
    
    if financial_score > device_score:
        return "financial"
    elif device_score > financial_score:
        return "devices"
    else:
        # Default to financial if unclear
        return "financial"


def detect_mode_from_query(message: str) -> str:
    """
    Detect desired response mode from user query.
    
    Args:
        message: User query string
        
    Returns:
        Mode identifier: 'chart', 'table', 'text', or 'auto'
    """
    m = message.lower()
    
    # Chart indicators
    chart_keywords = ["chart", "graph", "plot", "visualize", "visualization", "show me a chart", "create a graph"]
    if any(k in m for k in chart_keywords):
        return "chart"
    
    # Table indicators  
    table_keywords = ["table", "list", "show all", "breakdown", "by location", "by customer", "by status", "group by"]
    if any(k in m for k in table_keywords):
        return "table"
    
    # Text/count indicators (single values)
    text_keywords = ["how many", "count", "total", "sum", "average", "avg", "what is", "tell me"]
    if any(k in m for k in text_keywords):
        return "text"
        
    return "auto"


def needs_sql(message: str) -> bool:
    """
    Determine if query requires SQL execution vs RAG retrieval.
    
    Args:
        message: User query string
        
    Returns:
        True if SQL is needed for aggregation/analysis queries
    """
    agg_keywords = [
        "how many", "how much", "count", "total", "sum", "average", "avg", "mean", 
        "min", "max", "revenue", "sales order", "sales orders", "orders did we get", 
        "orders did we receive", "number of orders"
    ]
    return any(keyword in message.lower() for keyword in agg_keywords)


def is_greeting_or_social(message: str) -> bool:
    """
    Check if message is a greeting, thanks, or social interaction.
    
    Args:
        message: User query string
        
    Returns:
        True if message is a social interaction
    """
    message_lower = message.lower().strip()
    greeting_patterns = [
        "thank you", "thanks", "thank", "bye", "goodbye", "hello", "hi", "hey",
        "good morning", "good afternoon", "good evening", "how are you"
    ]
    
    return any(pattern in message_lower for pattern in greeting_patterns)


def get_greeting_response(message: str) -> str:
    """
    Generate appropriate response for greeting/social messages.
    
    Args:
        message: User query string
        
    Returns:
        Appropriate greeting response
    """
    message_lower = message.lower().strip()
    
    if "thank" in message_lower:
        return "You're welcome! Feel free to ask any questions about your data."
    elif any(word in message_lower for word in ["bye", "goodbye"]):
        return "Goodbye! Have a great day!"
    else:
        return "Hello! I'm here to help you analyze your data. What would you like to know?"
