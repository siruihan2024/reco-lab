# app/retrieval/vector_index.py
import json
from typing import List, Dict, Tuple
import numpy as np
from app.models.embeddings import EmbeddingClient

def _product_text(p: Dict) -> str:
    syn = " ".join(p.get("synonyms", []) or [])
    return f"{p['name']} | {p.get('category','')} | {syn} | {p.get('description','')}"

class ProductIndex:
    def __init__(self, products: List[Dict]):
        self.products = products
        self.embeddings = None  # np.ndarray [N, D]
        self._id2idx = {p["id"]: i for i, p in enumerate(products)}

    async def build(self, embedder: EmbeddingClient):
        texts = [_product_text(p) for p in self.products]
        vecs = await embedder.embed(texts)
        self.embeddings = np.array(vecs, dtype=float)

    def top_k(self, text_emb: np.ndarray, k: int = 10) -> List[Tuple[int, float]]:
        assert self.embeddings is not None, "Index not built"
        M = self.embeddings
        qn = text_emb / (np.linalg.norm(text_emb) + 1e-9)
        Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
        sims = (Mn @ qn)
        idxs = np.argpartition(-sims, kth=min(k, len(sims)-1))[:k]
        pairs = [(int(i), float(sims[i])) for i in idxs]
        pairs.sort(key=lambda x: x[1], reverse=True)
        return pairs

    def by_indices(self, idxs: List[int]) -> List[Dict]:
        return [self.products[i] for i in idxs]

    def size(self) -> int:
        return len(self.products)