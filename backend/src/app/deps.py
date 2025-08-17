from .config import settings

def get_settings():
    return settings

from .providers.http_vllm_provider import HTTPVLLMProvider
from .providers.embedding_provider import EmbeddingProvider
from .services.qdrant_store import QdrantStore
from .services.sql_store import SQLStore
import asyncio, httpx

llm = HTTPVLLMProvider()
embedder = EmbeddingProvider(settings)
vs = QdrantStore(settings, embedder)
sql = SQLStore(settings)

async def check_services():
    """Basic startup health checks.
    - Ping Qdrant root endpoint
    - Perform a trivial embedding to ensure model loaded
    - Run a simple DuckDB query
    (Best‑effort: failures are logged but don't block startup.)
    """
    results = {}
    # Qdrant
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.qdrant_url}/collections")
            r.raise_for_status()
        results['qdrant'] = 'ok'
    except Exception as e:
        results['qdrant'] = f'error: {e}'
    # Embedding
    try:
        _ = await embedder.embed(["health check"])
        results['embeddings'] = 'ok'
    except Exception as e:
        results['embeddings'] = f'error: {e}'
    # DuckDB
    try:
        sql.con.execute("SELECT 1").fetchall()
        results['duckdb'] = 'ok'
    except Exception as e:
        results['duckdb'] = f'error: {e}'
    # Log
    print("[startup checks]", results)
    return results