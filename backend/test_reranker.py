#!/usr/bin/env python3
"""测试 Reranker API 格式"""
import requests
import json
import numpy as np

RERANK_URL = "http://127.0.0.1:30002/v1"

# 测试数据
query = "泳衣"
documents = [
    {"text": "防晒霜，SPF50+", "id": "doc1"},
    {"text": "沙滩巾，纯棉材质", "id": "doc2"},
    {"text": "羽绒服，冬季保暖", "id": "doc3"},
]

print("=" * 60)
print("测试 Reranker - 使用 Embeddings 端点")
print("=" * 60)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 方案：使用 embeddings 处理 query-doc 对
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n[测试] 使用 /embeddings 处理 query-doc 对")
try:
    # 构造 query-doc 对
    query_doc_pairs = [f"{query} [SEP] {d['text']}" for d in documents]
    
    payload = {
        "model": "Qwen/Qwen3-Reranker-8B",
        "input": query_doc_pairs,
        "encoding_format": "float"
    }
    print(f"Request: POST {RERANK_URL}/embeddings")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    r = requests.post(f"{RERANK_URL}/embeddings", json=payload, timeout=10)
    print(f"\nStatus: {r.status_code}")
    
    if r.ok:
        data = r.json()
        print(f"✅ 成功！")
        
        embeddings = data.get("data", [])
        print(f"\n📊 获得 {len(embeddings)} 个 embedding")
        
        # 提取分数（使用第一个维度或范数）
        scores = []
        for idx, emb_data in enumerate(embeddings):
            embedding = emb_data.get("embedding", [])
            vec = np.array(embedding[:10], dtype=float)  # 只显示前10维
            
            # 使用第一个维度作为分数
            score = float(embedding[0]) if embedding else 0.0
            scores.append(score)
            
            print(f"\nDoc {idx+1}: {documents[idx]['text']}")
            print(f"  Embedding (前10维): {vec}")
            print(f"  Score (第1维): {score:.6f}")
        
        # 归一化并排序
        scores_arr = np.array(scores)
        if np.ptp(scores_arr) > 1e-9:
            norm_scores = (scores_arr - scores_arr.min()) / (scores_arr.max() - scores_arr.min())
        else:
            norm_scores = np.ones_like(scores_arr)
        
        # 排序
        sorted_indices = np.argsort(-norm_scores)
        
        print(f"\n🏆 重排序结果（按相关性）：")
        for rank, idx in enumerate(sorted_indices):
            print(f"  #{rank+1}: {documents[idx]['text']} (归一化分数: {norm_scores[idx]:.4f})")
    else:
        print(f"❌ 失败")
        print(f"Response: {r.text}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)