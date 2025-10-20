# app/config.py
import os

# OpenAI-compatible endpoints served by sglang
CHAT_BASE_URL = os.getenv("CHAT_BASE_URL", "http://127.0.0.1:30003/v1")
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://127.0.0.1:30001/v1")
RERANK_BASE_URL = os.getenv("RERANK_BASE_URL", "http://127.0.0.1:30002/v1")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "EMPTY")

# Model names on your sglang servers
CHAT_MODEL = os.getenv("CHAT_MODEL", "Qwen/Qwen3-VL-4B-Instruct-FP8")  # ✅ 改为 VL 模型
EMBED_MODEL = os.getenv("EMBED_MODEL", "Qwen/Qwen3-Embedding-8B")
RERANK_MODEL = os.getenv("RERANK_MODEL", "Qwen/Qwen3-Reranker-8B")

# App
TOP_K_CANDIDATES = int(os.getenv("TOP_K_CANDIDATES", "20"))
TOP_K_RETURN = int(os.getenv("TOP_K_RETURN", "8"))

# LLM Category Mapper
USE_LLM_CATEGORY_MAPPER = os.getenv("USE_LLM_CATEGORY_MAPPER", "true").lower() == "true"
CATEGORY_CACHE_TTL = int(os.getenv("CATEGORY_CACHE_TTL", str(86400 * 7)))

# Vision Model (VL)
VL_API_URL = os.getenv("VL_API_URL", "http://127.0.0.1:30003/v1")
VL_MODEL = os.getenv("VL_MODEL", "Qwen/Qwen3-VL-4B-Instruct-FP8")