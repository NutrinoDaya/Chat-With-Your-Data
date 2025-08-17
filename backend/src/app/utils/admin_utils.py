"""
Admin Utilities

This module provides administrative functions for data management,
table operations, and system maintenance.
"""

from typing import List, Dict, Any
from ..deps import sql
from ..ingest.upserter import upsert_record


def get_database_tables() -> List[Dict[str, Any]]:
    """
    Get list of all tables in the database.
    
    Returns:
        List of table information dictionaries
    """
    try:
        df = sql.query("SHOW TABLES")
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"[admin_error] Failed to list tables: {e}")
        return []


def get_table_info(table_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific table.
    
    Args:
        table_name: Name of the table to inspect
        
    Returns:
        Dictionary with table information
    """
    try:
        # Get table schema
        schema_df = sql.query(f"DESCRIBE {table_name}")
        schema = schema_df.to_dict(orient="records")
        
        # Get row count
        count_df = sql.query(f"SELECT COUNT(*) as row_count FROM {table_name}")
        row_count = count_df.iloc[0]['row_count']
        
        return {
            "table_name": table_name,
            "row_count": row_count,
            "schema": schema
        }
    except Exception as e:
        print(f"[admin_error] Failed to get table info for {table_name}: {e}")
        return {"error": str(e)}


def ingest_data_record(data: dict, source: str) -> Dict[str, str]:
    """
    Ingest a single data record into the appropriate table.
    
    Args:
        data: Data record to ingest
        source: Source identifier for routing
        
    Returns:
        Status dictionary
    """
    try:
        upsert_record(data, str(data), source)
        return {"status": "accepted", "source": source}
    except Exception as e:
        print(f"[admin_error] Failed to ingest data for source {source}: {e}")
        return {"status": "error", "error": str(e)}


def validate_data_record(data: dict, source: str) -> Dict[str, Any]:
    """
    Validate data record before ingestion.
    
    Args:
        data: Data record to validate
        source: Source identifier
        
    Returns:
        Validation result dictionary
    """
    errors = []
    
    # Basic validation
    if not isinstance(data, dict):
        errors.append("Data must be a dictionary")
    
    if not data:
        errors.append("Data cannot be empty")
    
    # Source-specific validation
    if source == "financial":
        required_fields = ["customer", "amount"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
    
    elif source == "devices":
        required_fields = ["device_id", "status"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "source": source
    }


def get_ingestion_stats() -> Dict[str, Any]:
    """
    Get statistics about data ingestion across all sources.
    
    Returns:
        Dictionary with ingestion statistics
    """
    stats = {}
    
    tables = ["financial_orders", "device_metrics"]
    
    for table in tables:
        try:
            count_df = sql.query(f"SELECT COUNT(*) as total_records FROM {table}")
            total_records = count_df.iloc[0]['total_records']
            
            # Get recent records (last 24 hours)
            recent_df = sql.query(f"""
                SELECT COUNT(*) as recent_records 
                FROM {table} 
                WHERE ts >= datetime('now', '-1 day')
            """)
            recent_records = recent_df.iloc[0]['recent_records'] if len(recent_df) > 0 else 0
            
            stats[table] = {
                "total_records": total_records,
                "recent_records": recent_records
            }
        except Exception as e:
            stats[table] = {"error": str(e)}
    
    return stats
