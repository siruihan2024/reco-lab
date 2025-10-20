# app/engine/recommendation.py
import json
import os
from typing import List, Dict
import numpy as np
from collections import Counter
import httpx
from app.config import TOP_K_CANDIDATES, TOP_K_RETURN
from app.models.embeddings import EmbeddingClient
from app.models.reranker import RerankerClient
from app.retrieval.vector_index import ProductIndex, _product_text
from app.engine.category_mapper import LLMCategoryMapper, FALLBACK_CATEGORY_COMPLEMENTS

class AssocRecommender:
    def __init__(self, products_path: str, use_llm_mapper: bool = True):
        self.products_path = products_path
        with open(products_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.products: List[Dict] = data["products"]
        self.embedder = EmbeddingClient()
        self.reranker = RerankerClient()
        self.index = ProductIndex(self.products)
        self._built = False
        
        # LLM 类目映射器
        self.use_llm_mapper = use_llm_mapper
        if use_llm_mapper:
            self.category_mapper = LLMCategoryMapper()
        else:
            self.category_mapper = None

    async def warmup(self):
        if not self._built:
            await self.index.build(self.embedder)
            self._built = True

    async def reload(self):
        # 重新读取 products.json 并重建索引
        with open(self.products_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.products = data.get("products", [])
        self.index = ProductIndex(self.products)
        await self.index.build(self.embedder)
        self._built = True
        return {"ok": True, "num_products": len(self.products)}

    def stats(self) -> Dict:
        cats = [p.get("category", "") for p in self.products]
        cnt = Counter(cats)
        top = cnt.most_common(10)
        
        stats = {
            "num_products": len(self.products),
            "top_categories": top,
        }
        
        # 添加类目映射器统计
        if self.category_mapper:
            stats["category_mapper"] = self.category_mapper.get_stats()
        
        return stats

    async def _embed(self, text: str) -> np.ndarray:
        vec = await self.embedder.embed([text])
        return np.array(vec[0], dtype=float)

    async def _understand_query(self, query: str) -> str:
        """
        🆕 使用 LLM 理解并规范化用户查询
        
        功能：
        1. 英文 → 中文翻译
        2. 口语化 → 标准商品名
        3. 模糊表达 → 精确类目
        
        Args:
            query: 用户原始查询
            
        Returns:
            规范化后的查询文本
        """
        # 如果未启用 LLM 映射器，直接返回原查询
        if not self.use_llm_mapper or not self.category_mapper:
            return query
        
        system_prompt = """你是一个专业的电商搜索理解助手，负责将用户的搜索查询转换为标准的商品相关词汇。

核心任务：
1. **语言转换**：如果是英文，翻译成中文
2. **规范表达**：将口语化、模糊的表达转换为标准的商品名称或类目
3. **保持简洁**：只输出转换后的关键词，不要解释或添加其他内容

示例：
- "clothes" → "服装"
- "pillow" → "枕头"
- "running shoes" → "跑鞋"
- "想买个泳衣" → "泳衣"
- "smart watch" → "智能手表"
- "coffee maker" → "咖啡机"
- "yoga mat" → "瑜伽垫"

输出要求：
- 仅输出转换后的中文词汇
- 不超过10个字
- 不要引号、标点或解释"""

        user_prompt = f'用户查询: {query}\n标准化输出:'
        
        try:
            url = f"{self.category_mapper.base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {self.category_mapper.api_key}"}
            payload = {
                "model": self.category_mapper.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,  # 低温度保证稳定性
                "max_tokens": 50
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                normalized = data["choices"][0]["message"]["content"].strip()
                
                # 验证结果的合理性
                if normalized and len(normalized) <= 50 and normalized != query:
                    print(f"[INFO] Query normalized: '{query}' → '{normalized}'")
                    return normalized
                else:
                    print(f"[INFO] Query unchanged: '{query}'")
                    return query
                    
        except Exception as e:
            print(f"[WARN] Query understanding failed: {e}, using original query")
            return query

    async def _candidate_filter(self, anchor: Dict) -> List[Dict]:
        """用类目先验扩展候选（支持 LLM 动态生成）"""
        anchor_cat = anchor.get("category") or ""
        
        # 尝试使用 LLM 映射器
        if self.use_llm_mapper and self.category_mapper:
            try:
                allowed_cats = await self.category_mapper.get_complement_categories(anchor)
            except Exception as e:
                print(f"[WARN] LLM mapper failed, using fallback: {e}")
                allowed_cats = FALLBACK_CATEGORY_COMPLEMENTS.get(anchor_cat, [])
        else:
            # 使用静态映射
            allowed_cats = FALLBACK_CATEGORY_COMPLEMENTS.get(anchor_cat, [])
        
        if not allowed_cats:
            # 无先验时，放开全部（后续由reranker过滤）
            return [p for p in self.products if p["id"] != anchor["id"]]
        
        return [p for p in self.products if p["id"] != anchor["id"] and (p.get("category") in allowed_cats)]

    async def recommend(self, query: str, top_k: int = TOP_K_RETURN, debug: bool = False) -> Dict:
        await self.warmup()

        # 🆕 0) 使用 LLM 理解并规范化查询
        normalized_query = await self._understand_query(query)

        # 1) 用向量检索找到锚点商品（使用规范化后的查询）
        q_emb = await self._embed(normalized_query)
        
        # 🔍 DEBUG: 查看 top 5 匹配
        if debug:
            top5_matches = self.index.top_k(q_emb, k=5)
            print(f"\n[DEBUG] Original query: '{query}'")
            print(f"[DEBUG] Normalized query: '{normalized_query}'")
            print(f"[DEBUG] Top 5 anchor candidates:")
            for idx, (i, sim) in enumerate(top5_matches):
                p = self.index.by_indices([i])[0]
                print(f"  {idx+1}. {p['name']} (sim={sim:.4f}, cat={p.get('category', 'N/A')})")
        
        anchor_idx_sim = self.index.top_k(q_emb, k=1)[0]
        anchor = self.index.by_indices([anchor_idx_sim[0]])[0]
        
        print(f"[INFO] Selected anchor: {anchor['name']} (cat={anchor.get('category', 'N/A')})")

        # 2) 构造候选集：先按先验过滤，再用向量近邻扩展
        # 2a) 先验候选（使用 LLM 增强）
        prior_candidates = await self._candidate_filter(anchor)
        
        # 2b) 向量近邻
        anchor_text = _product_text(anchor)
        anchor_emb = await self._embed(anchor_text)
        knn_idxs = [i for i, _ in self.index.top_k(anchor_emb, k=min(TOP_K_CANDIDATES, self.index.size()))]
        knn_candidates = self.index.by_indices(knn_idxs)

        # 合并去重
        cand_by_id = {}
        for p in prior_candidates + knn_candidates:
            if p["id"] != anchor["id"]:
                cand_by_id[p["id"]] = p
        candidates = list(cand_by_id.values())

        # 3) 用 Reranker 验证与打分（语义缺口由重排模型弥补）
        rerank_query = f"与{anchor['name']}一起购买/搭配的互补商品，相关性从高到低排序。"
        docs = [{
            "id": p["id"],
            "text": _product_text(p),
            "meta": {"name": p["name"], "category": p.get("category", "")}
        } for p in candidates]

        scored = await self.reranker.rerank(rerank_query, docs)

        # 4) 取Top-K并返回简要字段（名称与分数）
        top = scored[:top_k]
        results = [{
            "id": s["id"],
            "name": next((d["meta"]["name"] for d in scored if d["id"] == s["id"]), ""),
            "score": round(float(s["score"]), 4)
        } for s in top]
        # 补齐 name
        id2name = {p["id"]: p["name"] for p in candidates}
        for r in results:
            if not r["name"]:
                r["name"] = id2name.get(r["id"], r["id"])
        return {
            "anchor": {"id": anchor["id"], "name": anchor["name"]},
            "items": results
        }