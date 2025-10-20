# scripts/merge_dataset.py
import os
import json
from glob import glob
from typing import Dict

DATA_DIR = os.getenv("DATA_DIR", "/data/xbx/KDD/app/data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
OUT_PATH = os.path.join(DATA_DIR, "products.json")

def load_existing() -> Dict[str, Dict]:
    if not os.path.exists(OUT_PATH):
        return {}
    with open(OUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {p["name"]: p for p in data.get("products", []) if p.get("name")}

def main():
    by_name = load_existing()
    for path in sorted(glob(os.path.join(RAW_DIR, "*.ndjson"))):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                name = obj.get("name")
                if not name:
                    continue
                if name not in by_name:
                    by_name[name] = obj

    products = list(by_name.values())
    
    # 🔧 重新分配唯一ID
    for i, p in enumerate(products, start=1):
        p["id"] = f"prod{i:05d}"
    
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"products": products}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(products)} products to {OUT_PATH}")

if __name__ == "__main__":
    main()