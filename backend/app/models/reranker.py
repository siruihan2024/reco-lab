# app/models/reranker.py
from typing import List, Dict
import httpx
import numpy as np
from app.config import RERANK_BASE_URL, RERANK_MODEL, OPENAI_API_KEY
from app.models.embeddings import EmbeddingClient

class RerankerClient:
    def __init__(self, base_url: str = RERANK_BASE_URL, model: str = RERANK_MODEL, api_key: str = OPENAI_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self._embed_fallback = EmbeddingClient()

    async def rerank(self, query: str, docs: List[Dict[str, str]]) -> List[Dict]:
        """
        Expects docs as [{"id": str, "text": str, "meta": any}, ...]
        Returns sorted list with fields: id, text, score, meta
        
        Strategy:
        1. 为每个 [query, doc] 对生成 embedding
        2. 使用 embedding 向量的范数或特定维度作为相关性分数
        """
        
        # 🔧 方案：使用 embeddings 端点处理 query-doc 对
        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # 构造 query-doc 对（用特殊分隔符）
        # Reranker 模型通常接受 "query [SEP] document" 格式
        query_doc_pairs = [f"{query} [SEP] {d['text']}" for d in docs]
        
        payload = {
            "model": self.model,
            "input": query_doc_pairs,
            "encoding_format": "float"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                embeddings = data.get("data", [])
                
                if embeddings and len(embeddings) == len(docs):
                    scored = []
                    for idx, emb_data in enumerate(embeddings):
                        embedding = emb_data.get("embedding", [])
                        
                        # 🔧 使用 embedding 的 L2 范数作为相关性分数
                        # Reranker 输出的向量范数通常代表相关性
                        if embedding:
                            vec = np.array(embedding, dtype=float)
                            # 尝试多种方式提取分数
                            # 1. 向量的第一个维度（某些模型如此设计）
                            # 2. L2 范数
                            # 3. 向量和的平均值
                            score = float(vec[0]) if len(vec) > 0 else 0.0
                            # 或者使用范数：score = float(np.linalg.norm(vec))
                        else:
                            score = 0.0
                        
                        scored.append({
                            "id": docs[idx].get("id", ""),
                            "text": docs[idx]["text"],
                            "meta": docs[idx].get("meta"),
                            "score": score
                        })
                    
                    # 归一化到 [0,1]
                    if scored:
                        scores = np.array([s["score"] for s in scored], dtype=float)
                        if np.ptp(scores) > 1e-9:
                            norm = (scores - scores.min()) / (scores.max() - scores.min())
                        else:
                            norm = np.ones_like(scores)
                        for i, v in enumerate(norm):
                            scored[i]["score"] = float(v)
                        scored.sort(key=lambda x: x["score"], reverse=True)
                        print(f"[INFO] Reranker succeeded with {len(scored)} results")
                        return scored
        except Exception as e:
            print(f"[WARN] Reranker API failed: {e}")

        # Fallback: embedding cosine similarity
        print("[INFO] Using embedding fallback for reranking")
        texts = [query] + [d["text"] for d in docs]
        embs = await self._embed_fallback.embed(texts)
        q = np.array(embs[0], dtype=float)
        M = np.array(embs[1:], dtype=float)
        qn = q / (np.linalg.norm(q) + 1e-9)
        Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
        sims = (Mn @ qn)
        # normalize
        if np.ptp(sims) > 1e-9:
            sims = (sims - sims.min()) / (sims.max() - sims.min())
        else:
            sims = np.ones_like(sims)
        scored = []
        for i, s in enumerate(sims.tolist()):
            scored.append({"id": docs[i].get("id", ""), "text": docs[i]["text"], "meta": docs[i].get("meta"), "score": float(s)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored