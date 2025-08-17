"""Schema and sample query ingestion for hybrid RAG+SQL analytics."""

from typing import List, Dict, Any
import asyncio
from ..services.qdrant_store import QdrantStore
from ..providers.embedding_provider import EmbeddingProvider
from ..config import settings

# Schema documentation and sample queries
SCHEMA_DOCS = [
    {
        "table": "financial_orders", 
        "description": "Financial transaction records from sales orders",
        "schema": "financial_orders(order_id BIGINT, customer TEXT, amount DOUBLE, currency TEXT, ts TIMESTAMP, status TEXT)",
        "sample_data": "order_id=1001, customer='Acme LLC', amount=1250.50, currency='USD', ts='2024-08-16 14:30:00', status='PAID'",
        "common_queries": [
            "Count orders: SELECT COUNT(*) FROM financial_orders WHERE DATE_TRUNC('day', ts) = CURRENT_DATE",
            "Revenue today: SELECT SUM(amount) FROM financial_orders WHERE DATE_TRUNC('day', ts) = CURRENT_DATE", 
            "Revenue by customer: SELECT customer, SUM(amount) FROM financial_orders WHERE DATE_TRUNC('day', ts) = CURRENT_DATE GROUP BY customer",
            "Orders by status: SELECT status, COUNT(*) FROM financial_orders WHERE DATE_TRUNC('day', ts) = CURRENT_DATE GROUP BY status",
            "Average order value: SELECT AVG(amount) FROM financial_orders WHERE DATE_TRUNC('day', ts) = CURRENT_DATE"
        ]
    },
    {
        "table": "device_metrics",
        "description": "IoT device telemetry and status monitoring data", 
        "schema": "device_metrics(device_id TEXT, status TEXT, uptime_minutes DOUBLE, location TEXT, ts TIMESTAMP)",
        "sample_data": "device_id='dev-1001', status='ONLINE', uptime_minutes=1320.5, location='DXB-01', ts='2024-08-16 14:30:00'",
        "common_queries": [
            "Online devices: SELECT COUNT(*) FROM device_metrics WHERE status='ONLINE' AND DATE_TRUNC('day', ts) = CURRENT_DATE",
            "Devices by status: SELECT status, COUNT(*) FROM device_metrics WHERE DATE_TRUNC('day', ts) = CURRENT_DATE GROUP BY status",
            "Average uptime: SELECT AVG(uptime_minutes) FROM device_metrics WHERE DATE_TRUNC('day', ts) = CURRENT_DATE",
            "Uptime by location: SELECT location, AVG(uptime_minutes) FROM device_metrics WHERE DATE_TRUNC('day', ts) = CURRENT_DATE GROUP BY location",
            "Device count by location: SELECT location, COUNT(DISTINCT device_id) FROM device_metrics WHERE DATE_TRUNC('day', ts) = CURRENT_DATE GROUP BY location"
        ]
    }
]

QUERY_PATTERNS = [
    {
        "pattern": "how many orders",
        "intent": "count_orders", 
        "sql_template": "SELECT COUNT(*) FROM financial_orders WHERE DATE_TRUNC('day', ts) = CURRENT_DATE",
        "description": "Count total number of orders for today"
    },
    {
        "pattern": "revenue today",
        "intent": "revenue_daily",
        "sql_template": "SELECT SUM(amount) FROM financial_orders WHERE DATE_TRUNC('day', ts) = CURRENT_DATE", 
        "description": "Calculate total revenue for today"
    },
    {
        "pattern": "how many devices online",
        "intent": "devices_online",
        "sql_template": "SELECT COUNT(*) FROM device_metrics WHERE status='ONLINE' AND DATE_TRUNC('day', ts) = CURRENT_DATE",
        "description": "Count devices currently online today"
    },
    {
        "pattern": "average uptime",
        "intent": "avg_uptime", 
        "sql_template": "SELECT AVG(uptime_minutes) FROM device_metrics WHERE DATE_TRUNC('day', ts) = CURRENT_DATE",
        "description": "Calculate average device uptime for today"
    }
]

async def ingest_schemas_and_patterns():
    """Ingest schema docs and query patterns into Qdrant for retrieval."""
    embedder = EmbeddingProvider(settings)
    vs = QdrantStore(settings, embedder)
    
    print("[schema_ingestion] Starting schema and pattern ingestion...")
    
    # Ingest schema documentation
    for schema_doc in SCHEMA_DOCS:
        # Create comprehensive text for embedding
        text = f"""
Table: {schema_doc['table']}
Description: {schema_doc['description']}
Schema: {schema_doc['schema']}
Sample Data: {schema_doc['sample_data']}
Common Queries:
{chr(10).join(schema_doc['common_queries'])}
        """.strip()
        
        meta = {
            "type": "schema",
            "table": schema_doc['table'],
            "description": schema_doc['description'],
            "schema": schema_doc['schema'],
            "record_id": f"schema_{schema_doc['table']}"
        }
        
        await vs.upsert_texts("financial" if "financial" in schema_doc['table'] else "devices", [text], [meta])
    
    # Ingest query patterns  
    for pattern in QUERY_PATTERNS:
        text = f"""
Query Pattern: {pattern['pattern']}
Intent: {pattern['intent']}
SQL Template: {pattern['sql_template']}
Description: {pattern['description']}
        """.strip()
        
        meta = {
            "type": "query_pattern",
            "pattern": pattern['pattern'],
            "intent": pattern['intent'], 
            "sql_template": pattern['sql_template'],
            "record_id": f"pattern_{pattern['intent']}"
        }
        
        # Store patterns in both collections for cross-source retrieval
        await vs.upsert_texts("financial", [text], [meta])
        await vs.upsert_texts("devices", [text], [meta])
    
    print(f"[schema_ingestion] Ingested {len(SCHEMA_DOCS)} schemas and {len(QUERY_PATTERNS)} query patterns")

async def retrieve_schema_context(query: str, source: str, embedder: EmbeddingProvider, vs: QdrantStore, top_k: int = 3) -> str:
    """Retrieve relevant schema docs and query patterns for a user query."""
    try:
        query_embedding = await embedder.embed([query])
        hits = await vs.search(source, query_embedding[0], top_k)
        
        context_parts = []
        for hit in hits:
            if hit.payload.get("type") == "schema":
                context_parts.append(f"TABLE SCHEMA: {hit.payload.get('schema')}")
                context_parts.append(f"DESCRIPTION: {hit.payload.get('description')}")
            elif hit.payload.get("type") == "query_pattern":
                context_parts.append(f"PATTERN: {hit.payload.get('pattern')} -> {hit.payload.get('sql_template')}")
        
        return "\n".join(context_parts)
    except Exception as e:
        print(f"[retrieve_schema_context] Error: {e}")
        return ""

if __name__ == "__main__":
    asyncio.run(ingest_schemas_and_patterns())
