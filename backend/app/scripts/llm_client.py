# scripts/llm_client.py
import os
import json
import httpx
from typing import List, Dict, Optional, Any

CHAT_BASE_URL = os.getenv("CHAT_BASE_URL", "http://127.0.0.1:30000/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "Qwen/Qwen3-0.6B")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "EMPTY")

class ChatClient:
    def __init__(self, base_url: str = CHAT_BASE_URL, model: str = CHAT_MODEL, api_key: str = OPENAI_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    async def chat(self, system: str, user: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

def _extract_json_array(text: str) -> Any:
    # 尽量从返回中提取首个 JSON 数组
    s = text.find("[")
    if s == -1:
        raise ValueError("No JSON array found")
    depth = 0
    for i in range(s, len(text)):
        c = text[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                snippet = text[s:i+1]
                return json.loads(snippet)
    raise ValueError("Unbalanced JSON array")

def to_ndjson_lines(items: List[Dict]) -> List[str]:
    return [json.dumps(it, ensure_ascii=False) for it in items]