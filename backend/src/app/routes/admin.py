"""
Admin API Routes

This module provides administrative endpoints for data management and system monitoring.
Business logic has been extracted to admin_utils for maintainability.
"""

from fastapi import APIRouter, HTTPException

from ..schemas import IngestRecord
from ..utils.admin_utils import (
    get_database_tables,
    get_table_info,
    ingest_data_record,
    validate_data_record,
    get_ingestion_stats
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tables")
def list_tables():
    """Get list of all database tables."""
    tables = get_database_tables()
    return {"tables": tables}


@router.get("/tables/{table_name}")
def get_table_details(table_name: str):
    """Get detailed information about a specific table."""
    table_info = get_table_info(table_name)
    
    if "error" in table_info:
        raise HTTPException(status_code=404, detail=f"Table not found or error: {table_info['error']}")
    
    return table_info


@router.get("/stats")
def get_admin_stats():
    """Get administrative statistics and system overview."""
    ingestion_stats = get_ingestion_stats()
    tables = get_database_tables()
    
    return {
        "tables_count": len(tables),
        "ingestion_stats": ingestion_stats,
        "status": "operational"
    }


@router.post("/ingest")
def ingest(rec: IngestRecord):
    """Ingest a data record with validation."""
    # Validate data first
    validation = validate_data_record(rec.data, rec.source)
    
    if not validation["valid"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Validation failed: {validation['errors']}"
        )
    
    # Ingest the record
    result = ingest_data_record(rec.data, rec.source)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/ingest/financial")
def ingest_financial(rec: dict):
    """Ingest financial data record."""
    validation = validate_data_record(rec, "financial")
    
    if not validation["valid"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Validation failed: {validation['errors']}"
        )
    
    result = ingest_data_record(rec, "financial")
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/ingest/devices")
def ingest_devices(rec: dict):
    """Ingest device data record."""
    validation = validate_data_record(rec, "devices")
    
    if not validation["valid"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Validation failed: {validation['errors']}"
        )
    
    result = ingest_data_record(rec, "devices")
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/validate")
def validate_data(data: dict, source: str):
    """Validate data record without ingesting."""
    validation = validate_data_record(data, source)
    return validation