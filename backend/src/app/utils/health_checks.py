"""
Health Check Utilities

This module provides health check functionality for downstream services
including LLM availability and system status monitoring.
"""

import httpx
from typing import Dict, Any
from fastapi import HTTPException


async def check_llm_health(llm_client) -> Dict[str, str]:
    """
    Check downstream LLM service health with fallback probing.
    
    Args:
        llm_client: LLM client instance
        
    Returns:
        Dictionary with health status
        
    Raises:
        HTTPException: If LLM service is unavailable
    """
    base = llm_client.base_url.rstrip("/")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # First try /health if exposed
        try:
            r = await client.get(f"{base}/health")
            if r.status_code == 200:
                return {"status": "ok", "method": "health_endpoint"}
        except Exception:
            pass
        
        # Fallback probe with minimal chat request
        try:
            r = await client.post(f"{base}/v1/chat/completions", json={
                "model": llm_client.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1
            })
            r.raise_for_status()
            return {"status": "ok", "method": "chat_probe"}
        except Exception as e:
            raise HTTPException(
                status_code=503, 
                detail=f"LLM service unavailable: {e}"
            )


async def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health status.
    
    Returns:
        Dictionary with system health information
    """
    from ..deps import check_services
    
    try:
        # Check all services
        service_status = await check_services()
        
        return {
            "status": "healthy",
            "services": service_status,
            "timestamp": "now"  # Would use actual timestamp in production
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "now"
        }


def format_health_response(status: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Format health check response consistently.
    
    Args:
        status: Overall health status
        details: Additional health details
        
    Returns:
        Formatted health response
    """
    response = {"status": status}
    
    if details:
        response.update(details)
    
    return response
