from __future__ import annotations
import httpx
import torch
import numpy as np
from typing import List
from transformers import AutoTokenizer, AutoModel
from ..config import Settings

class EmbeddingProvider:
    def __init__(self, settings: Settings):
        self.s = settings
        if "bge" in settings.embeddings_model.lower():
            self.tokenizer = AutoTokenizer.from_pretrained(settings.embeddings_model)
            self.model = AutoModel.from_pretrained(settings.embeddings_model)
            if torch.cuda.is_available():
                self.model = self.model.cuda()
            self.model = self.model.eval()
            
    async def embed(self, texts: List[str]) -> List[List[float]]:
        if "bge" in self.s.embeddings_model.lower():
            return await self._bge_embed(texts)
        elif self.s.provider == "openai":
            return await self._openai_embed(texts)
        return await self._ollama_embed(texts)

    async def _bge_embed(self, texts: List[str]) -> List[List[float]]:
        # Add special tokens for BGE model
        encoded_texts = ["Represent this sentence for retrieval: " + text for text in texts]
        # Tokenize and prepare inputs
        inputs = self.tokenizer(
            encoded_texts,
            padding=True,
            truncation=True,
            return_tensors='pt',
            max_length=512
        )
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
            
        # Generate embeddings
        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0].cpu().numpy()  # Use [CLS] token embedding
            # Normalize embeddings
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            return embeddings.tolist()

    async def _openai_embed(self, texts: List[str]) -> List[List[float]]:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.s.OPENAI_API_KEY}"},
                json={"model": self.s.embeddings_model, "input": texts},
            )
            r.raise_for_status()
            data = r.json()["data"]
            return [d["embedding"] for d in data]

    async def _ollama_embed(self, texts: List[str]) -> List[List[float]]:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.s.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": self.s.embeddings_model, "input": texts},
            )
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and "embedding" in data:
                return [data["embedding"]]
            return [d["embedding"] for d in data.get("data", [])]