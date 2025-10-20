#!/usr/bin/env python3
import os, sys, json, argparse, requests

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = os.environ.get("RECO_PORT", "")
ENV_TOP_K = int(os.environ.get("TOP_K", "5"))
ENV_SHOW_SCORE = os.environ.get("SHOW_SCORE", "1") == "1"

parser = argparse.ArgumentParser(description="Interactive recommender CLI")
parser.add_argument("--top", type=int, default=ENV_TOP_K, help="返回前N个（默认取环境变量TOP_K或5）")
parser.add_argument("--score", action="store_true", default=ENV_SHOW_SCORE, help="显示分数/概率")
args = parser.parse_args()

TOP_K = args.top
SHOW_SCORE = args.score

cands = [p for p in [PORT, "18081", "8081", "8080", "19000"] if p]

def find_port():
    for p in cands:
        try:
            r = requests.get(f"http://{HOST}:{p}/admin/stats", timeout=1)
            if r.ok: return p
        except Exception:
            pass
        try:
            r = requests.get(f"http://{HOST}:{p}", timeout=1)
            if r.ok: return p
        except Exception:
            pass
    return ""

PORT = find_port() or input("未能自动发现服务端口，请输入端口号：").strip()
print(f"连接到 http://{HOST}:{PORT}")

def print_items(data):
    items = data.get("items", [])[:TOP_K]
    for it in items:
        name = it.get("name","")
        if SHOW_SCORE:
            sc = it.get("score", None)
            # 这里的 score 是归一化相似度（0~1），你可以理解为“概率样的相关性”
            if sc is not None:
                print(f"{name} ({sc:.4f})")
            else:
                print(name)
        else:
            print(name)

print(f"""命令：
  :reload          重新加载 products.json 并重建索引
  :stats           查看内存中商品统计
  :top N           设置返回条数，例如 :top 7（当前 {TOP_K}）
  :score on|off    开关显示分数（当前 {"on" if SHOW_SCORE else "off"}）
  :port P          切换端口
  :quit            退出
直接输入商品名称获取推荐。
""")

sess = requests.Session()
while True:
    try:
        q = input("\n商品> ").strip()
    except EOFError:
        break
    if not q:
        continue
    if q in (":quit", ":exit"):
        break
    if q == ":reload":
        try:
            r = sess.post(f"http://{HOST}:{PORT}/admin/reload", timeout=10)
            print(r.text)
        except Exception as e:
            print("请求失败:", e)
        continue
    if q == ":stats":
        try:
            r = sess.get(f"http://{HOST}:{PORT}/admin/stats", timeout=10)
            print(r.text)
        except Exception as e:
            print("请求失败:", e)
        continue
    if q.startswith(":port "):
        PORT = q.split(" ", 1)[1].strip()
        print(f"切换到 http://{HOST}:{PORT}")
        continue
    if q.startswith(":top "):
        try:
            TOP_K = max(1, int(q.split(" ", 1)[1].strip()))
            print(f"已设置 TOP_K = {TOP_K}")
        except Exception:
            print("格式错误，用法示例：:top 7")
        continue
    if q.startswith(":score "):
        val = q.split(" ", 1)[1].strip().lower()
        if val in ("on", "1", "true", "yes"):
            SHOW_SCORE = True
            print("已开启分数显示")
        elif val in ("off", "0", "false", "no"):
            SHOW_SCORE = False
            print("已关闭分数显示")
        else:
            print("用法：:score on | :score off")
        continue

    payload = {"query": q, "top_k": TOP_K}
    try:
        r = sess.post(f"http://{HOST}:{PORT}/recommend", json=payload, timeout=60)
        if not r.ok:
            print("HTTP", r.status_code, r.text)
            continue
        data = r.json()
        print_items(data)
    except requests.exceptions.JSONDecodeError:
        print("非JSON响应：", r.text)
    except Exception as e:
        print("请求失败:", e)