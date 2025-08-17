from __future__ import annotations
from typing import List, Dict
from ..providers.embedding_provider import EmbeddingProvider
from ..services.qdrant_store import QdrantStore

async def semantic_search(embedder: EmbeddingProvider, vs: QdrantStore, source: str, query: str, top_k: int = 6):
    vec = (await embedder.embed([query]))[0]
    hits = vs.search(source, vec, top_k)
    return hits