# scripts/gen_products.py
import os
import re
import json
import argparse
import asyncio
from datetime import datetime
from typing import List, Dict, Set
from llm_client import ChatClient, _extract_json_array, to_ndjson_lines
from prompts import build_generation_prompt
from prompts_En import build_generation_prompt as build_generation_prompt_En

DATA_DIR = os.getenv("DATA_DIR", "/data/xbx/KDD/app/data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

def slugify_name(name: str) -> str:
    s = re.sub(r"\s+", "", name)
    s = re.sub(r"[^\w\u4e00-\u9fff-]", "", s)
    return s[:24]

def load_existing_names(products_path: str) -> Set[str]:
    names: Set[str] = set()
    if os.path.exists(products_path):
        try:
            with open(products_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for p in data.get("products", []):
                    if p.get("name"):
                        names.add(p["name"])
        except Exception:
            pass
    # 也从 NDJSON 原始库去重
    for fname in os.listdir(RAW_DIR):
        if not fname.endswith(".ndjson"):
            continue
        with open(os.path.join(RAW_DIR, fname), "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get("name"):
                        names.add(obj["name"])
                except Exception:
                    continue
    return names

def assign_ids(items: List[Dict], prefix: str, start_index: int) -> None:
    i = start_index
    for it in items:
        it["id"] = f"{prefix}{i:05d}"
        i += 1

async def gen_for_category(category: str, batch: int, client: ChatClient, lang: str = "zh") -> List[Dict]:
    """Generate products for a category in specified language."""
    if lang == "en":
        import prompts_En as prompts
        sys_prompt = "You are a rigorous e-commerce product planning assistant, skilled at structured output."
    else:
        import prompts
        sys_prompt = "你是一个严谨的电商商品策划助理，擅长结构化输出。"
    if lang == "en":
        build_generation_prompt = build_generation_prompt_En
    else:
        build_generation_prompt = build_generation_prompt
    # print(build_generation_prompt)
    user_prompt = build_generation_prompt(category, batch)
    text = await client.chat(system=sys_prompt, user=user_prompt, temperature=0.6, max_tokens=2048)
    items = _extract_json_array(text)
    # 只保留所需字段，防 prompt 漂移
    cleaned = []
    for x in items:
        cleaned.append({
            "id": "",
            "name": x.get("name", "").strip(),
            "synonyms": list(filter(None, (x.get("synonyms") or []))),
            "category": category,
            "description": x.get("description", "").strip(),
            "tags": list(filter(None, (x.get("tags") or []))),
            "price": x.get("price", None),
            "attributes": x.get("attributes", {}) or {},
        })
    # 基础清洗：去空名
    cleaned = [c for c in cleaned if c["name"]]
    return cleaned

async def main(categories: List[str], per_category: int, batch_size: int, id_prefix: str, lang: str = "zh"):
    products_path = os.path.join(DATA_DIR, "products.json")
    existing_names = load_existing_names(products_path)

    client = ChatClient()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = os.path.join(RAW_DIR, f"products_{lang}_{ts}.ndjson")


    next_id_index = 1
    if os.path.exists(products_path):
        try:
            with open(products_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ids = [p["id"] for p in data.get("products", []) if isinstance(p.get("id"), str) and p["id"].startswith(id_prefix)]
            if ids:
                nums = [int(x[len(id_prefix):]) for x in ids if x[len(id_prefix):].isdigit()]
                if nums:
                    next_id_index = max(nums) + 1
        except Exception:
            pass

    written = 0
    with open(raw_file, "a", encoding="utf-8") as out:
        for cat in categories:
            remaining = per_category
            while remaining > 0:
                batch = min(batch_size, remaining)
                try:
                    items = await gen_for_category(cat, batch, client, lang)  # Pass lang parameter
                except Exception as e:
                    print(f"[WARN] Generation failed for {cat}: {e}")
                    continue
                # 去重（按 name）
                uniq = []
                for it in items:
                    if it["name"] in existing_names:
                        continue
                    existing_names.add(it["name"])
                    uniq.append(it)
                # 分配 id
                assign_ids(uniq, id_prefix, next_id_index)
                next_id_index += len(uniq)
                # 写 NDJSON
                lines = to_ndjson_lines(uniq)
                for ln in lines:
                    out.write(ln + "\n")
                written += len(uniq)
                print(f"[OK] {cat} +{len(uniq)} (batch={batch}), total_written={written}")
                remaining -= batch

    print(f"Done. NDJSON written to: {raw_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--categories", type=str, required=True, help="Comma-separated: e.g., Lifestyle,Food,Clothing")
    parser.add_argument("--per-category", type=int, default=50, help="Target number of new items per category")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of items to request from LLM each time")
    parser.add_argument("--id-prefix", type=str, default="tb", help="ID prefix, e.g., tb")
    parser.add_argument("--lang", type=str, default="en", choices=["zh", "en"], help="Language: zh (Chinese) or en (English)")
    args = parser.parse_args()

    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    asyncio.run(main(cats, args.per_category, args.batch_size, args.id_prefix, args.lang))