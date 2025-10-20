# app/engine/category_mapper.py
import json
import os
import time
import hashlib
from typing import Dict, List, Optional
import httpx
from app.config import CHAT_BASE_URL, CHAT_MODEL, OPENAI_API_KEY

class LLMCategoryMapper:
    """使用 LLM 动态生成商品类目的互补关系"""
    
    def __init__(
        self, 
        cache_file: str = "/data/xbx/KDD/app/data/category_cache.json",
        base_url: str = CHAT_BASE_URL,
        model: str = CHAT_MODEL,
        api_key: str = OPENAI_API_KEY,
        cache_ttl: int = 86400 * 7  # 7天缓存
    ):
        self.cache_file = cache_file
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.cache_ttl = cache_ttl
        
        # 加载缓存
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """从文件加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save cache: {e}")
    
    def _get_cache_key(self, anchor: Dict) -> str:
        """生成缓存键"""
        # 使用商品名称和类目生成唯一键
        key_str = f"{anchor.get('name', '')}|{anchor.get('category', '')}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """检查缓存是否过期"""
        if "timestamp" not in cache_entry:
            return False
        return time.time() - cache_entry["timestamp"] < self.cache_ttl
    
    async def _call_llm(self, anchor: Dict) -> List[str]:
        """调用 LLM 生成互补类目"""
        system_prompt = """你是一个电商商品关系专家，擅长分析商品之间的互补关系。
你的任务是根据给定的商品信息，推断出与该商品**互补**（而非相似）的其他商品类目。

注意：
1. 互补品是指用户购买A商品后，可能**一起搭配使用**的B商品
2. 不是相似品（例如：泳衣的互补品是防晒霜，而不是另一种泳衣）
3. 考虑使用场景、配套需求、功能互补等因素

输出要求：
- 返回类目名称列表（不要商品名）
- 使用简洁的类目词（如：防晒、沙滩、配件）
- 最多返回5个类目
- 必须严格遵守 JSON 数组格式"""

        user_prompt = f"""商品信息：
名称: {anchor.get('name', '未知')}
类目: {anchor.get('category', '未知')}
描述: {anchor.get('description', '无')}
标签: {', '.join(anchor.get('tags', []))}

请分析该商品的使用场景，推断出与其**互补**的商品类目。

输出格式（严格遵守）：
["类目1", "类目2", "类目3"]"""

        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,  # 低温度保证稳定性
            "max_tokens": 256
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                
                # 解析 JSON 数组
                categories = self._parse_llm_response(content)
                return categories
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            # 降级：返回自身类目
            return [anchor.get('category', 'Lifestyle')]
    
    def _parse_llm_response(self, content: str) -> List[str]:
        """解析 LLM 返回的类目列表"""
        try:
            # 尝试直接解析 JSON
            if content.strip().startswith("["):
                return json.loads(content.strip())
            
            # 查找 JSON 数组
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                json_str = content[start:end+1]
                return json.loads(json_str)
            
            # 降级：简单分割
            lines = [line.strip().strip('"-,') for line in content.split("\n") if line.strip()]
            return [line for line in lines if line and not line.startswith("[") and not line.startswith("]")][:5]
        except Exception as e:
            print(f"[WARN] Failed to parse LLM response: {e}")
            return []
    
    async def get_complement_categories(self, anchor: Dict, use_cache: bool = True) -> List[str]:
        """
        获取商品的互补类目列表
        
        Args:
            anchor: 锚点商品信息
            use_cache: 是否使用缓存
            
        Returns:
            互补类目列表
        """
        cache_key = self._get_cache_key(anchor)
        
        # 尝试从缓存读取
        if use_cache and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry):
                return cache_entry["categories"]
        
        # 调用 LLM 生成
        categories = await self._call_llm(anchor)
        
        # 确保包含自身类目
        anchor_cat = anchor.get('category', '')
        if anchor_cat and anchor_cat not in categories:
            categories.insert(0, anchor_cat)
        
        # 更新缓存
        self.cache[cache_key] = {
            "categories": categories,
            "timestamp": time.time(),
            "anchor_name": anchor.get('name', ''),
            "anchor_category": anchor_cat
        }
        self._save_cache()
        
        return categories
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        total = len(self.cache)
        valid = sum(1 for entry in self.cache.values() if self._is_cache_valid(entry))
        expired = total - valid
        
        return {
            "total_cached": total,
            "valid_cached": valid,
            "expired_cached": expired,
            "cache_file": self.cache_file
        }
    
    def clear_cache(self):
        """清空缓存"""
        self.cache = {}
        self._save_cache()


# 静态后备映射（当 LLM 不可用时使用）
FALLBACK_CATEGORY_COMPLEMENTS = {
    "游泳": ["游泳", "防晒", "沙滩", "配件", "居家"],
    "防晒": ["沙滩", "游泳", "护肤"],
    "沙滩": ["游泳", "防晒", "户外"],
    "clothing": ["clothing", "accessories", "shoes", "bags"],
    "Lifestyle": ["Lifestyle", "home", "accessories"],
    "Electronics": ["Electronics", "accessories", "cables"],
    "Sports": ["Sports", "accessories", "clothing"],
}