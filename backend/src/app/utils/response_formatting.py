"""
Response Formatting Utilities

This module handles formatting of query results into appropriate response formats
including text, table, and chart responses.
"""

import pandas as pd
from typing import Dict, Any, List


def format_sql_result(df: pd.DataFrame, question: str, sql: str) -> str:
    """
    Format SQL query results into readable text.
    
    Args:
        df: DataFrame with query results
        question: Original user question
        sql: SQL query executed
        
    Returns:
        Formatted text response
    """
    if df.empty:
        return "No data found for your query."
    
    # Handle single value results
    if len(df) == 1 and len(df.columns) == 1:
        value = df.iloc[0, 0]
        if pd.isna(value):
            return "No data available."
        return f"Result: {value:,}" if isinstance(value, (int, float)) else f"Result: {value}"
    
    # Handle multiple results
    if len(df) <= 10:  # Show all results if small dataset
        result_items = []
        for _, row in df.iterrows():
            if len(df.columns) == 1:
                result_items.append(f"• {row.iloc[0]}")
            else:
                item_parts = []
                for col, val in row.items():
                    if pd.notna(val):
                        if isinstance(val, (int, float)) and col.lower() in ['revenue', 'amount', 'total', 'value']:
                            item_parts.append(f"{col}: {val:,.2f}")
                        else:
                            item_parts.append(f"{col}: {val}")
                result_items.append(f"• {', '.join(item_parts)}")
        
        return f"Found {len(df)} results:\n" + "\n".join(result_items)
    else:
        # Show top results and summary
        top_results = []
        for i, (_, row) in enumerate(df.head(5).iterrows()):
            if len(df.columns) == 1:
                top_results.append(f"• {row.iloc[0]}")
            else:
                item_parts = []
                for col, val in row.items():
                    if pd.notna(val):
                        if isinstance(val, (int, float)) and col.lower() in ['revenue', 'amount', 'total', 'value']:
                            item_parts.append(f"{col}: {val:,.2f}")
                        else:
                            item_parts.append(f"{col}: {val}")
                top_results.append(f"• {', '.join(item_parts)}")
        
        return f"Found {len(df)} results (showing top 5):\n" + "\n".join(top_results)


def create_table_response(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Create table response format from DataFrame.
    
    Args:
        df: DataFrame with query results
        
    Returns:
        Table response dictionary with columns and rows
    """
    if df.empty:
        return {"columns": [], "rows": []}
    
    # Convert DataFrame to table format
    columns = df.columns.tolist()
    rows = df.values.tolist()
    
    # Format numeric values appropriately
    formatted_rows = []
    for row in rows:
        formatted_row = []
        for val in row:
            if pd.isna(val):
                formatted_row.append(None)
            elif isinstance(val, (int, float)):
                # Round to 2 decimal places for currency/amounts
                formatted_row.append(round(val, 2) if val != int(val) else int(val))
            else:
                formatted_row.append(str(val))
        formatted_rows.append(formatted_row)
    
    return {"columns": columns, "rows": formatted_rows}


def should_use_chart(df: pd.DataFrame, mode: str, message: str) -> bool:
    """
    Determine if response should include a chart.
    
    Args:
        df: DataFrame with query results
        mode: Detected response mode
        message: Original user message
        
    Returns:
        True if chart should be generated
    """
    wants_chart = mode == "chart" or any(word in message.lower() for word in 
                                        ["chart", "graph", "plot", "visualize", "visualization"])
    
    # Chart is appropriate if:
    # 1. User explicitly requested it, AND
    # 2. Data has at least 2 columns, AND  
    # 3. Data has some rows
    return wants_chart and df.shape[1] >= 2 and len(df) > 0


def determine_chart_columns(df: pd.DataFrame) -> tuple[str, str]:
    """
    Determine appropriate X and Y columns for charting.
    
    Args:
        df: DataFrame with query results
        
    Returns:
        Tuple of (x_column, y_column)
    """
    columns = df.columns.tolist()
    
    # Default to first two columns
    x_col, y_col = columns[0], columns[1]
    
    # Prefer categorical for X and numeric for Y
    for col in columns:
        if df[col].dtype in ['object', 'string', 'category']:
            x_col = col
            break
    
    for col in columns:
        if df[col].dtype in ['int64', 'float64', 'int32', 'float32']:
            y_col = col
            break
    
    return x_col, y_col


def format_chart_filename(path: str) -> str:
    """
    Extract and format chart filename for frontend consumption.
    
    Args:
        path: Full chart file path
        
    Returns:
        Chart filename for frontend
    """
    return path.split('/')[-1] if '/' in path else path


def validate_dataframe(df: pd.DataFrame) -> bool:
    """
    Validate DataFrame for response processing.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        True if DataFrame is valid for processing
    """
    return df is not None and not df.empty and len(df.columns) > 0
