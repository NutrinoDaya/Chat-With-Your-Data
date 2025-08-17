from __future__ import annotations
from typing import List, Dict
from ..config import settings
from ..providers.embedding_provider import EmbeddingProvider

def embed_record(text: str) -> list:
    # Synchronous wrapper for embedding (for ETL)
    import asyncio
    provider = EmbeddingProvider(settings)
    return asyncio.run(provider.embed([text]))[0]