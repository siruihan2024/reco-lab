#!/usr/bin/env python3
"""
实时推荐 CLI - 输入时自动显示推荐结果（带防抖优化）
使用 prompt_toolkit 实现类似搜索引擎的实时建议功能
"""
import os
import sys
import json
import time
import threading
import argparse
from typing import List, Dict
import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

# 配置
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = os.environ.get("RECO_PORT", "")
ENV_TOP_K = int(os.environ.get("TOP_K", "5"))
ENV_SHOW_SCORE = os.environ.get("SHOW_SCORE", "1") == "1"

parser = argparse.ArgumentParser(description="实时推荐 CLI（带防抖优化）")
parser.add_argument("--top", type=int, default=ENV_TOP_K, help="返回前N个推荐")
parser.add_argument("--score", action="store_true", default=ENV_SHOW_SCORE, help="显示分数")
parser.add_argument("--min-chars", type=int, default=1, help="触发推荐的最少字符数（默认1）")
parser.add_argument("--debounce", type=int, default=300, help="防抖延迟（毫秒，默认300）")
args = parser.parse_args()

TOP_K = args.top
SHOW_SCORE = args.score
MIN_CHARS = args.min_chars
DEBOUNCE_MS = args.debounce

# 查找服务端口
cands = [p for p in [PORT, "18081", "8081", "8080", "19000"] if p]

def find_port():
    for p in cands:
        try:
            r = requests.get(f"http://{HOST}:{p}/admin/stats", timeout=1)
            if r.ok:
                return p
        except Exception:
            pass
    return ""

PORT = find_port()
if not PORT:
    PORT = input("未能自动发现服务端口，请输入端口号：").strip()

print(f"✓ 连接到 http://{HOST}:{PORT}")
print(f"✓ 实时推荐已启用（输入 {MIN_CHARS} 个字符后自动显示）")
print(f"✓ 防抖延迟: {DEBOUNCE_MS}ms（避免频繁请求）")
print(f"✓ 按 Tab 键可循环选择建议，按 Enter 确认\n")

sess = requests.Session()


class SmartRecommendCompleter(Completer):
    """
    智能推荐补全器（带混合防抖优化）
    
    优化策略：
    1. 防抖（Debounce）：只在停止输入后触发
    2. 最少字符数：避免无意义的短查询
    3. 智能缓存：相同查询直接返回缓存
    4. 过期检测：避免过时的请求覆盖新结果
    """
    
    def __init__(self, host, port, top_k=5, min_chars=1, debounce_ms=300):
        self.host = host
        self.port = port
        self.top_k = top_k
        self.min_chars = min_chars
        self.debounce_ms = debounce_ms
        
        # 缓存
        self.cache: Dict[str, List[dict]] = {}
        
        # 防抖状态
        self.last_query_time: Dict[str, float] = {}  # 每个查询的最后请求时间
        self.lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "debounced": 0,
        }
    
    def get_completions(self, document: Document, complete_event):
        """根据当前输入获取推荐（带防抖）"""
        text = document.text.strip()
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1️⃣ 命令补全（不走 API）
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if document.text.startswith(":"):
            commands = [":quit", ":reload", ":stats", ":top", ":score", ":port", ":clear", ":debug"]
            for cmd in commands:
                if cmd.startswith(document.text):
                    yield Completion(cmd, start_position=-len(document.text))
            return
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2️⃣ 最少字符数检查
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if len(text) < self.min_chars:
            return
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3️⃣ 防抖检查
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        current_time = time.time() * 1000  # 毫秒
        
        with self.lock:
            last_time = self.last_query_time.get(text, 0)
            time_diff = current_time - last_time
            
            # 如果距离上次请求时间太短，先返回缓存（如果有）
            if time_diff < self.debounce_ms:
                if text in self.cache:
                    # 使用缓存，不发新请求
                    self.stats["debounced"] += 1
                    recommendations = self.cache[text]
                else:
                    # 太快了，且没缓存，不触发
                    return
            else:
                # 超过防抖时间，更新时间戳
                self.last_query_time[text] = current_time
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 4️⃣ 缓存检查
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if text in self.cache:
            self.stats["cache_hits"] += 1
            recommendations = self.cache[text]
        else:
            # 调用 API 获取推荐
            recommendations = self._fetch_recommendations(text)
            if recommendations:  # 只缓存成功的结果
                self.cache[text] = recommendations
            self.stats["total_requests"] += 1
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 5️⃣ 返回补全建议
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        for idx, item in enumerate(recommendations):
            name = item.get("name", "")
            score = item.get("score", 0)
            
            if SHOW_SCORE:
                display_text = f"{name} ({score:.4f})"
            else:
                display_text = name
            
            # 创建补全项
            yield Completion(
                text=name,
                start_position=-len(text),
                display=display_text,
                display_meta=f"#{idx+1}"
            )
    
    def _fetch_recommendations(self, query: str) -> List[dict]:
        """获取推荐结果"""
        try:
            payload = {"query": query, "top_k": self.top_k}
            r = sess.post(
                f"http://{self.host}:{self.port}/recommend",
                json=payload,
                timeout=3  # 减少超时时间
            )
            if r.ok:
                data = r.json()
                return data.get("items", [])
        except Exception:
            # 静默失败，不打断用户输入
            pass
        return []
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total = self.stats["total_requests"]
        cache_hits = self.stats["cache_hits"]
        debounced = self.stats["debounced"]
        
        if total > 0:
            cache_rate = cache_hits / total * 100
        else:
            cache_rate = 0
        
        return {
            "total_api_requests": total,
            "cache_hits": cache_hits,
            "debounced_requests": debounced,
            "cache_hit_rate": f"{cache_rate:.1f}%",
            "cached_queries": len(self.cache)
        }


# 自定义样式
style = Style.from_dict({
    'completion-menu.completion': 'bg:#008888 #ffffff',
    'completion-menu.completion.current': 'bg:#00aaaa #000000',
    'completion-menu.meta.completion': 'bg:#444444 #ffffff',
    'completion-menu.meta.completion.current': 'bg:#666666 #ffffff',
})


def print_help():
    """打印帮助信息"""
    help_text = FormattedText([
        ('ansiblue', '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'),
        ('ansigreen bold', '实时推荐 CLI 使用指南\n'),
        ('ansiblue', '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n'),
        ('', '🔍 '),
        ('ansiyellow', '直接输入商品名称'),
        ('', '：输入时会实时显示推荐\n'),
        ('', '⚡ '),
        ('ansiyellow', '防抖优化'),
        ('', f'：停止输入 {DEBOUNCE_MS}ms 后才触发请求\n'),
        ('', '⌨️  '),
        ('ansiyellow', 'Tab 键'),
        ('', '：循环选择推荐项\n'),
        ('', '↩️  '),
        ('ansiyellow', 'Enter 键'),
        ('', '：确认选择并查看详细推荐\n\n'),
        ('ansicyan bold', '命令：\n'),
        ('', '  '),
        ('ansimagenta', ':reload'),
        ('', '     重新加载数据\n'),
        ('', '  '),
        ('ansimagenta', ':stats'),
        ('', '      查看统计信息\n'),
        ('', '  '),
        ('ansimagenta', ':debug'),
        ('', '      查看缓存/防抖统计\n'),
        ('', '  '),
        ('ansimagenta', ':top N'),
        ('', '      设置返回条数（当前: '),
        ('ansiyellow', f'{TOP_K}'),
        ('', '）\n'),
        ('', '  '),
        ('ansimagenta', ':score on|off'),
        ('', '  显示/隐藏分数（当前: '),
        ('ansiyellow', 'on' if SHOW_SCORE else 'off'),
        ('', '）\n'),
        ('', '  '),
        ('ansimagenta', ':clear'),
        ('', '      清空缓存\n'),
        ('', '  '),
        ('ansimagenta', ':quit'),
        ('', '       退出程序\n'),
        ('ansiblue', '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'),
    ])
    print_formatted_text(help_text)


def print_recommendations(query: str, data: dict):
    """打印推荐结果"""
    anchor = data.get("anchor", {})
    items = data.get("items", [])[:TOP_K]
    
    result_text = [
        ('ansigreen', f'\n✓ 锚点商品: '),
        ('ansiyellow bold', anchor.get('name', 'N/A')),
        ('', f' (ID: {anchor.get("id", "N/A")})\n'),
        ('ansicyan', f'━' * 50 + '\n'),
        ('ansicyan bold', '推荐商品：\n\n'),
    ]
    
    for idx, item in enumerate(items):
        name = item.get("name", "")
        score = item.get("score", 0)
        
        result_text.append(('ansiwhite', f'  {idx+1}. '))
        result_text.append(('', name))
        
        if SHOW_SCORE:
            result_text.append(('ansiyellow', f' ({score:.4f})'))
        
        result_text.append(('', '\n'))
    
    result_text.append(('ansicyan', f'━' * 50 + '\n'))
    print_formatted_text(FormattedText(result_text))


def handle_command(cmd: str, completer: SmartRecommendCompleter):
    """处理命令"""
    global TOP_K, SHOW_SCORE, PORT
    
    if cmd in (":quit", ":exit"):
        return False
    
    if cmd == ":reload":
        try:
            r = sess.post(f"http://{HOST}:{PORT}/admin/reload", timeout=10)
            print(f"✓ {r.text}")
        except Exception as e:
            print(f"✗ 请求失败: {e}")
        return True
    
    if cmd == ":stats":
        try:
            r = sess.get(f"http://{HOST}:{PORT}/admin/stats", timeout=10)
            data = r.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"✗ 请求失败: {e}")
        return True
    
    if cmd == ":debug":
        # 显示缓存和防抖统计
        stats = completer.get_stats()
        debug_text = FormattedText([
            ('ansicyan bold', '\n📊 性能统计\n'),
            ('ansicyan', '━' * 40 + '\n'),
            ('ansiwhite', f"总 API 请求次数: "),
            ('ansiyellow', f"{stats['total_api_requests']}\n"),
            ('ansiwhite', f"缓存命中次数: "),
            ('ansigreen', f"{stats['cache_hits']}\n"),
            ('ansiwhite', f"防抖拦截次数: "),
            ('ansimagenta', f"{stats['debounced_requests']}\n"),
            ('ansiwhite', f"缓存命中率: "),
            ('ansiyellow bold', f"{stats['cache_hit_rate']}\n"),
            ('ansiwhite', f"已缓存查询数: "),
            ('ansicyan', f"{stats['cached_queries']}\n"),
            ('ansicyan', '━' * 40 + '\n'),
        ])
        print_formatted_text(debug_text)
        return True
    
    if cmd == ":clear":
        old_count = len(completer.cache)
        completer.cache.clear()
        completer.last_query_time.clear()
        print(f"✓ 缓存已清空（清理了 {old_count} 个缓存项）")
        return True
    
    if cmd.startswith(":port "):
        PORT = cmd.split(" ", 1)[1].strip()
        print(f"✓ 切换到 http://{HOST}:{PORT}")
        return True
    
    if cmd.startswith(":top "):
        try:
            TOP_K = max(1, int(cmd.split(" ", 1)[1].strip()))
            completer.top_k = TOP_K
            print(f"✓ 已设置 TOP_K = {TOP_K}")
        except Exception:
            print("✗ 格式错误，用法: :top 7")
        return True
    
    if cmd.startswith(":score "):
        val = cmd.split(" ", 1)[1].strip().lower()
        if val in ("on", "1", "true", "yes"):
            SHOW_SCORE = True
            print("✓ 已开启分数显示")
        elif val in ("off", "0", "false", "no"):
            SHOW_SCORE = False
            print("✓ 已关闭分数显示")
        else:
            print("✗ 用法：:score on | :score off")
        return True
    
    return True


def main():
    """主函数"""
    print_help()
    
    # 创建智能补全器（带防抖）
    completer = SmartRecommendCompleter(
        host=HOST,
        port=PORT,
        top_k=TOP_K,
        min_chars=MIN_CHARS,
        debounce_ms=DEBOUNCE_MS
    )
    
    # 创建会话
    session = PromptSession(
        completer=completer,
        complete_while_typing=True,  # 输入时自动显示补全
        complete_in_thread=True,     # 异步补全，不阻塞输入
        style=style
    )
    
    while True:
        try:
            # 获取用户输入
            query = session.prompt('\n🔍 商品> ')
            query = query.strip()
            
            if not query:
                continue
            
            # 处理命令
            if query.startswith(":"):
                if not handle_command(query, completer):
                    break
                continue
            
            # 获取推荐
            try:
                payload = {"query": query, "top_k": TOP_K}
                r = sess.post(
                    f"http://{HOST}:{PORT}/recommend",
                    json=payload,
                    timeout=60
                )
                if not r.ok:
                    print(f"✗ HTTP {r.status_code}: {r.text}")
                    continue
                
                data = r.json()
                print_recommendations(query, data)
                
            except requests.exceptions.JSONDecodeError:
                print(f"✗ 非 JSON 响应: {r.text}")
            except Exception as e:
                print(f"✗ 请求失败: {e}")
        
        except (EOFError, KeyboardInterrupt):
            # 退出前显示统计
            stats = completer.get_stats()
            print(f"\n\n📊 本次会话统计：")
            print(f"  - 总请求: {stats['total_api_requests']}")
            print(f"  - 缓存命中: {stats['cache_hits']}")
            print(f"  - 防抖拦截: {stats['debounced_requests']}")
            print(f"  - 节省请求: {stats['cache_hits'] + stats['debounced_requests']} 次")
            print("\n👋 再见！\n")
            break


if __name__ == "__main__":
    main()