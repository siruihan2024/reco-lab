#!/usr/bin/env python3
"""
支持图片输入的推荐 CLI
上传图片 → VL 识别 → 商品推荐
"""
import os
import sys
import json
import argparse
import requests
from pathlib import Path

# 配置
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = os.environ.get("RECO_PORT", "8081")

parser = argparse.ArgumentParser(
    description="图片推荐 CLI",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
示例:
  %(prog)s product.jpg
  %(prog)s /path/to/photo.png --top 10
  %(prog)s image.webp --prompt "识别图片中的所有商品"
  %(prog)s photo.jpg --debug
    """
)
parser.add_argument("file", type=str, help="图片文件路径 (jpg, png, webp, etc.)")
parser.add_argument("--top", type=int, default=5, help="返回推荐数量（默认5）")
parser.add_argument("--prompt", type=str, help="自定义图片理解提示词")
parser.add_argument("--debug", action="store_true", help="显示详细调试信息")
args = parser.parse_args()


def check_file(filepath):
    """检查文件是否存在且有效"""
    path = Path(filepath)
    if not path.exists():
        print(f"✗ 错误: 文件不存在: {filepath}")
        sys.exit(1)
    
    # 支持的图片格式
    supported = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']
    if path.suffix.lower() not in supported:
        print(f"⚠️  警告: 文件格式 {path.suffix} 可能不支持")
        print(f"   支持的格式: {', '.join(supported)}")
    
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 10:
        print(f"⚠️  警告: 文件过大 ({size_mb:.2f} MB)，建议压缩后再上传")
    
    print(f"📷 图片: {path.name}")
    print(f"   大小: {size_mb:.2f} MB")
    print(f"   格式: {path.suffix}")
    
    return filepath


def recommend_by_image(image_file, top_k=5, custom_prompt=None):
    """图片推荐"""
    print(f"\n⏳ 处理中...")
    try:
        with open(image_file, 'rb') as f:
            files = {'image': (Path(image_file).name, f, 'image/*')}
            data = {'top_k': top_k}
            if custom_prompt:
                data['custom_prompt'] = custom_prompt
            
            resp = requests.post(
                f"http://{HOST}:{PORT}/recommend/image",
                files=files,
                data=data,
                timeout=90
            )
            resp.raise_for_status()
            result = resp.json()
            
            if args.debug:
                print(f"\n[DEBUG] Response:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            
            return result
    except requests.exceptions.ConnectionError:
        print(f"✗ 连接失败: 推荐服务未启动 (端口 {PORT})")
        print(f"   请先运行: bash run.sh")
        return None
    except Exception as e:
        print(f"✗ 图片推荐失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return None


def print_results(data):
    """打印推荐结果"""
    if not data:
        return
    
    print(f"\n" + "=" * 60)
    print(f"🖼️  图片推荐结果")
    print(f"=" * 60)
    
    # 图片理解
    understanding = data.get("understanding", "")
    query = data.get("query", "")
    
    print(f"\n💡 图片理解: {understanding}")
    if query != understanding:
        print(f"🔍 查询关键词: {query}")
    
    # 锚点商品
    anchor = data.get("anchor", {})
    print(f"\n✓ 锚点商品: {anchor.get('name', 'N/A')}")
    print(f"   ID: {anchor.get('id', 'N/A')}")
    
    # 推荐列表
    items = data.get("items", [])
    print(f"\n🎯 推荐商品 ({len(items)} 个):\n")
    for idx, item in enumerate(items, 1):
        score = item.get('score', 0)
        name = item.get('name', 'N/A')
        print(f"  {idx}. {name} ({score:.4f})")
    
    print(f"\n" + "=" * 60)


def main():
    """主函数"""
    print("=" * 60)
    print("🖼️  图片推荐 CLI")
    print("=" * 60)
    
    # 检查文件
    image_file = check_file(args.file)
    
    # 推荐
    result = recommend_by_image(image_file, top_k=args.top, custom_prompt=args.prompt)
    
    if result:
        print_results(result)
    else:
        print("\n✗ 推荐失败")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 已取消")
        sys.exit(0)