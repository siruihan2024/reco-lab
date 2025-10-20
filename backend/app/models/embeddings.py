# app/models/embeddings.py
from typing import List
import httpx
from app.config import EMBED_BASE_URL, EMBED_MODEL, OPENAI_API_KEY

class EmbeddingClient:
    def __init__(self, base_url: str = EMBED_BASE_URL, model: str = EMBED_MODEL, api_key: str = OPENAI_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    async def embed(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "input": texts}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]