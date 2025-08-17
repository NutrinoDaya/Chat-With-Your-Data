import httpx
from typing import List, Dict, Any
from ..config import settings


class HTTPVLLMProvider:
    """HTTP proxy provider using values from config.yaml (via Settings).

    Pulls model name from `model_name` and base URL from `vllm.service_url`.
    Fallbacks are provided for robustness if keys are missing.
    """
    def __init__(self):
        vllm_cfg = (settings.vllm or {}) if hasattr(settings, 'vllm') else {}
        # Expect service_url like "http://vllm:8000" (without trailing slash/path)
        self.base_url: str = vllm_cfg.get("service_url", "http://vllm:8000").rstrip('/')
        self.model: str = getattr(settings, 'model_name', 'TinyLlama/TinyLlama-1.1B-Chat-v1.0')
        # Optional timeout in nested config, else default 60s
        self.timeout: float = float(vllm_cfg.get("http_timeout", 60))

    async def chat(self, messages: List[Dict[str, Any]], max_tokens: int = 256, temperature: float = 0.7) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, json=payload)
            # If model not found, attempt automatic model fallback
            if r.status_code in (400, 404) and 'does not exist' in r.text.lower():
                new_model = await self._pick_available_model(client)
                if new_model and new_model != self.model:
                    print(f"[HTTPVLLMProvider] Switching model '{self.model}' -> '{new_model}' (auto-detected)")
                    self.model = new_model
                    payload['model'] = self.model
                    r = await client.post(url, json=payload)
            if r.status_code == 404:
                # Fallback to legacy /v1/completions endpoint
                fallback_url = f"{self.base_url}/v1/completions"
                prompt = self._messages_to_prompt(messages)
                fb_payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                rf = await client.post(fallback_url, json=fb_payload)
                if rf.status_code in (400, 404) and 'does not exist' in rf.text.lower():
                    new_model = await self._pick_available_model(client)
                    if new_model and new_model != self.model:
                        print(f"[HTTPVLLMProvider] Switching model '{self.model}' -> '{new_model}' (auto-detected legacy)")
                        self.model = new_model
                        fb_payload['model'] = self.model
                        rf = await client.post(fallback_url, json=fb_payload)
                try:
                    rf.raise_for_status()
                except Exception:
                    print(f"[HTTPVLLMProvider] Fallback error {rf.status_code} body={rf.text[:500]}")
                    raise
                data = rf.json()
                # Legacy format: choices[0].text
                return (data.get("choices", [{}])[0].get("text", "").strip() or "")
            try:
                r.raise_for_status()
            except Exception:
                print(f"[HTTPVLLMProvider] Error {r.status_code} body={r.text[:500]}")
                raise
            data = r.json()
        return (data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or "")

    def _messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"[SYSTEM]\n{content}\n")
            elif role == "user":
                parts.append(f"[USER]\n{content}\n")
            else:
                parts.append(f"[ASSISTANT]\n{content}\n")
        parts.append("[ASSISTANT]\n")
        return "".join(parts)

    async def _pick_available_model(self, client: httpx.AsyncClient) -> str | None:
        try:
            resp = await client.get(f"{self.base_url}/v1/models")
            if resp.status_code != 200:
                return None
            data = resp.json()
            models = data.get('data') or []
            if not models:
                return None
            # Prefer first model id
            mid = models[0].get('id') or models[0].get('model')
            return mid
        except Exception:
            return None

    async def generate(self, prompt: str) -> str:
        return await self.chat([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ])
