"""
SQL Generation Utilities

This module handles SQL query generation, parsing, and enhancement
including rule-based SQL generation and LLM-generated SQL post-processing.
"""

import re
from typing import Optional, Tuple
from datetime import datetime, timedelta


def extract_limit_number(message: str) -> Optional[int]:
    """
    Extract LIMIT number from user query using regex patterns.
    
    Args:
        message: User query string
        
    Returns:
        Limit number if found, None otherwise
    """
    patterns = [
        r'\btop\s+(\d+)\b',      # "top 5"
        r'\bfirst\s+(\d+)\b',    # "first 10"
        r'\blimit\s+(\d+)\b',    # "limit 20"
        r'\bshow\s+(\d+)\b',     # "show 3"
        r'\b(\d+)\s+(?:customers?|orders?|results?)\b'  # "5 customers"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue
    
    return None


def build_time_filter(message: str) -> Tuple[str, str]:
    """
    Build time-based WHERE clause from user query.
    
    Args:
        message: User query string
        
    Returns:
        Tuple of (where_clause, description)
    """
    m = message.lower()
    now = datetime.now()
    
    # Today
    if "today" in m:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return f"ts >= '{today_start.isoformat()}'", "today"
    
    # This week
    elif "this week" in m or "week" in m:
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        return f"ts >= '{week_start.isoformat()}'", "this week"
    
    # This month
    elif "this month" in m or "month" in m:
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return f"ts >= '{month_start.isoformat()}'", "this month"
    
    # Last 7 days
    elif "last 7 days" in m or "past week" in m:
        week_ago = now - timedelta(days=7)
        return f"ts >= '{week_ago.isoformat()}'", "last 7 days"
    
    # Last 30 days
    elif "last 30 days" in m or "past month" in m:
        month_ago = now - timedelta(days=30)
        return f"ts >= '{month_ago.isoformat()}'", "last 30 days"
    
    # Default: no time filter
    return "1=1", "all time"


def build_rule_sql(message: str, source: str) -> Optional[str]:
    """
    Build SQL for common financial/device queries using rule-based patterns.
    
    Args:
        message: User query string
        source: Data source ('financial' or 'devices')
        
    Returns:
        SQL query string if pattern matched, None otherwise
    """
    m = message.lower()
    time_filter, time_desc = build_time_filter(message)
    
    # Extract LIMIT if specified
    limit_num = extract_limit_number(message)
    limit_clause = f" LIMIT {limit_num}" if limit_num else ""
    
    if source == 'financial':
        tbl = 'financial_orders'
        
        # Enhanced customer detection
        group_by_customer = (
            'by customer' in m or 'per customer' in m or 
            ('top' in m and 'customer' in m) or 
            ('customer' in m and ('breakdown' in m or 'list' in m or 'show' in m)) or
            'customers by' in m or 'revenue by customer' in m or 'revenues by customer' in m or
            ('top' in m and 'customers' in m) or 'customers with' in m
        )
        wants_status_breakdown = 'status' in m or 'paid' in m or 'refunded' in m or 'cancelled' in m
        
        # Count orders with time filter
        if 'how many' in m and 'order' in m:
            return f"SELECT COUNT(*) AS order_count FROM {tbl} WHERE {time_filter};"
        
        # Revenue queries with enhanced customer detection
        if 'revenue' in m or 'sales' in m or 'income' in m:
            if group_by_customer:
                return f"SELECT customer, COALESCE(SUM(amount), 0) AS total_revenue FROM {tbl} WHERE {time_filter} AND amount IS NOT NULL GROUP BY customer ORDER BY total_revenue DESC{limit_clause};"
            return f"SELECT COALESCE(SUM(amount), 0) AS total_revenue FROM {tbl} WHERE {time_filter} AND amount IS NOT NULL;"
        
        # Average order value with time filter
        if ('average' in m or 'avg' in m or 'mean' in m) and ('order' in m or 'amount' in m):
            return f"SELECT AVG(amount) AS average_order_value FROM {tbl} WHERE {time_filter};"
        
        # Status breakdown with time filter
        if wants_status_breakdown:
            return f"SELECT status, COUNT(*) AS order_count FROM {tbl} WHERE {time_filter} GROUP BY status ORDER BY order_count DESC{limit_clause};"
            
    elif source == 'devices':
        tbl = 'device_metrics'
        if 'average' in m and ('uptime' in m or 'uptime_minutes' in m):
            return f"SELECT AVG(uptime_minutes) AS average_uptime_minutes FROM {tbl} WHERE {time_filter};"
        if 'uptime' in m and ('by location' in m or 'per location' in m):
            return f"SELECT location, AVG(uptime_minutes) AS average_uptime_minutes FROM {tbl} WHERE {time_filter} GROUP BY location ORDER BY average_uptime_minutes DESC;"
        if 'how many' in m and 'device' in m:
            return f"SELECT COUNT(DISTINCT device_id) AS device_count FROM {tbl} WHERE {time_filter};"
        if 'status' in m or 'online' in m or 'offline' in m:
            return f"SELECT status, COUNT(*) AS device_count FROM {tbl} WHERE {time_filter} GROUP BY status ORDER BY device_count DESC;"
    
    return None


def extract_sql(text: str) -> Optional[str]:
    """
    Extract SQL query from LLM response text.
    
    Args:
        text: LLM response containing SQL
        
    Returns:
        Clean SQL query string if found, None otherwise
    """
    # Remove code fences
    cleaned = text.replace('```sql', '```').replace('```SQL', '```')
    if '```' in cleaned:
        parts = cleaned.split('```')
        for p in parts:
            p = p.strip()
            if p and ('SELECT' in p.upper() or 'WITH' in p.upper()):
                return p
    
    # Direct SQL without fences
    if 'SELECT' in text.upper() or 'WITH' in text.upper():
        lines = text.split('\n')
        sql_lines = []
        for line in lines:
            if any(keyword in line.upper() for keyword in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT']):
                sql_lines.append(line.strip())
        if sql_lines:
            return '\n'.join(sql_lines)
    
    return None


def normalize_sql(sql_text: str, table_name: str) -> str:
    """
    Normalize SQL query for consistency and safety.
    
    Args:
        sql_text: Raw SQL query
        table_name: Expected table name
        
    Returns:
        Normalized SQL query
    """
    # Replace common table name variations
    variations = ['orders', 'order', 'financial_order', 'device_metric', 'devices', 'metrics']
    for var in variations:
        sql_text = re.sub(r'\b' + var + r'\b', table_name, sql_text, flags=re.IGNORECASE)
    
    # Ensure proper semicolon termination
    sql_text = sql_text.strip()
    if not sql_text.endswith(';'):
        sql_text += ';'
    
    return sql_text


def add_limit_to_llm_sql(sql_text: str, message: str) -> str:
    """
    Post-process LLM-generated SQL to add missing LIMIT clauses.
    
    Args:
        sql_text: LLM-generated SQL query
        message: Original user message
        
    Returns:
        SQL with LIMIT clause added if needed
    """
    limit_number = extract_limit_number(message)
    if limit_number and "LIMIT" not in sql_text.upper():
        # Add LIMIT clause to LLM-generated SQL
        sql_text = sql_text.rstrip(';') + f" LIMIT {limit_number};"
        print(f"[llm_sql_fix] Added LIMIT {limit_number} to LLM-generated SQL")
    
    return sql_text


# Source to table mapping
SOURCE_TABLES = {
    "financial": "financial_orders",
    "devices": "device_metrics",
}
