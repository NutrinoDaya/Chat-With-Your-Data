from __future__ import annotations
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from typing import List, Dict, Any
from ..config import Settings
from ..schemas import DataSource, SearchHit

COLLECTIONS = {
    "financial": "financial_chunks",
    "devices": "devices_chunks",
}

class QdrantStore:
    def __init__(self, settings: Settings, embedder):
        self.s = settings
        self.c = QdrantClient(url=self.s.qdrant_url, api_key=self.s.qdrant_api_key)
        self.embedder = embedder
        # Use configured dimension, fallback to 768 for bge-base model
        self.dim = self.s.embedding_dimension
        self._ensure_collection(self.s.qdrant_collection_financial, self.dim)
        self._ensure_collection(self.s.qdrant_collection_devices, self.dim)

    def _ensure_collection(self, name: str, size: int):
        collections = self.c.get_collections().collections
        exists = any(c.name == name for c in collections)
        
        if exists:
            # Check if dimensions match
            info = self.c.get_collection(name)
            current_size = info.config.params.vectors.size
            if current_size != size:
                # Collection exists with wrong dimension - recreate it
                self.c.delete_collection(name)
                exists = False
                
        if not exists:
            self.c.create_collection(
                collection_name=name,
                vectors_config=qm.VectorParams(size=size, distance=qm.Distance.COSINE),
            )

    def collection_for(self, source: DataSource) -> str:
        return self.s.qdrant_collection_financial if source == "financial" else self.s.qdrant_collection_devices

    async def upsert_texts(self, source: DataSource, texts: List[str], payloads: List[Dict[str, Any]]):
        vecs = await self.embedder.embed(texts)
        pts = []
        for idx, (vec, payload) in enumerate(zip(vecs, payloads)):
            # Use hash of record_id if available, otherwise use sequential number
            point_id = hash(str(payload.get('record_id', f'point_{idx}'))) % (2**63)
            pts.append(qm.PointStruct(
                id=point_id,  # Use integer ID
                vector=vec,
                payload=payload
            ))
        self.c.upsert(self.collection_for(source), points=pts)

    def search(self, source: DataSource, query_vector: List[float], top_k: int = 6) -> List[SearchHit]:
        res = self.c.search(self.collection_for(source), query_vector=query_vector, limit=top_k, with_payload=True)
        hits: List[SearchHit] = []
        for r in res:
            hits.append(SearchHit(score=float(r.score), payload=dict(r.payload or {}), id=r.id))
        return hits