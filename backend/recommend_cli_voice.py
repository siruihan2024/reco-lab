#!/usr/bin/env python3
"""
支持语音输入的推荐 CLI（文件上传模式）
无需录音依赖，直接上传音频文件
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
WHISPER_PORT = "30004"

parser = argparse.ArgumentParser(
    description="语音推荐 CLI - 文件上传模式",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
示例:
  %(prog)s audio.wav
  %(prog)s /path/to/audio.m4a --lang en
  %(prog)s voice.mp3 --top 10
  %(prog)s recording.ogg --debug
    """
)
parser.add_argument("file", type=str, help="音频文件路径 (支持 wav, mp3, m4a, ogg, flac 等)")
parser.add_argument("--top", type=int, default=5, help="返回推荐数量（默认5）")
parser.add_argument("--lang", type=str, default="auto", help="语言 (zh/en/auto，默认auto)")
parser.add_argument("--debug", action="store_true", help="显示详细调试信息")
parser.add_argument("--text-only", action="store_true", help="只进行转写，不推荐")
args = parser.parse_args()


def check_file(filepath):
    """检查文件是否存在且有效"""
    path = Path(filepath)
    if not path.exists():
        print(f"✗ 错误: 文件不存在: {filepath}")
        sys.exit(1)
    
    # 支持的音频格式
    supported = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aac', '.wma', '.opus']
    if path.suffix.lower() not in supported:
        print(f"⚠️  警告: 文件格式 {path.suffix} 可能不支持")
        print(f"   支持的格式: {', '.join(supported)}")
    
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"📁 文件: {path.name}")
    print(f"   大小: {size_mb:.2f} MB")
    print(f"   格式: {path.suffix}")
    
    return filepath


def transcribe_audio(audio_file):
    """调用 Whisper 转写"""
    print(f"\n⏳ 转写中...")
    try:
        with open(audio_file, 'rb') as f:
            files = {'file': (Path(audio_file).name, f, 'audio/*')}
            data = {'language': args.lang if args.lang != 'auto' else None}
            
            resp = requests.post(
                f"http://{HOST}:{WHISPER_PORT}/v1/audio/transcriptions",
                files=files,
                data=data,
                timeout=60
            )
            resp.raise_for_status()
            result = resp.json()
            
            if args.debug:
                print(f"\n[DEBUG] Whisper Response:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            
            return result
    except requests.exceptions.ConnectionError:
        print(f"✗ 连接失败: Whisper 服务未启动 (端口 {WHISPER_PORT})")
        print(f"   请先运行: bash whisper_server.sh")
        return None
    except requests.exceptions.Timeout:
        print(f"✗ 转写超时: 音频文件可能太长")
        return None
    except Exception as e:
        print(f"✗ 转写失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return None


def recommend_by_text(query, top_k=5):
    """文本推荐"""
    print(f"\n⏳ 推荐中...")
    try:
        resp = requests.post(
            f"http://{HOST}:{PORT}/recommend",
            json={"query": query, "top_k": top_k},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        print(f"✗ 连接失败: 推荐服务未启动 (端口 {PORT})")
        print(f"   请先运行: bash run.sh")
        return None
    except Exception as e:
        print(f"✗ 推荐失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return None


def recommend_by_voice(audio_file, top_k=5):
    """语音推荐（一步到位）"""
    print(f"\n⏳ 处理中...")
    try:
        with open(audio_file, 'rb') as f:
            files = {'audio': (Path(audio_file).name, f, 'audio/*')}
            data = {'top_k': top_k, 'language': args.lang if args.lang != 'auto' else 'zh'}
            
            resp = requests.post(
                f"http://{HOST}:{PORT}/recommend/voice",
                files=files,
                data=data,
                timeout=90
            )
            resp.raise_for_status()
            result = resp.json()
            
            if args.debug:
                print(f"\n[DEBUG] Recommend Response:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            
            return result
    except requests.exceptions.ConnectionError:
        print(f"✗ 连接失败: 推荐服务未启动 (端口 {PORT})")
        return None
    except Exception as e:
        print(f"✗ 语音推荐失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return None


def print_transcription(result):
    """打印转写结果"""
    if not result:
        return
    
    text = result.get('text', '')
    language = result.get('language', 'N/A')
    duration = result.get('duration', 0)
    
    print(f"\n" + "=" * 60)
    print(f"📝 转写结果")
    print(f"=" * 60)
    print(f"\n{text}")
    print(f"\n语言: {language}")
    print(f"时长: {duration:.2f} 秒")
    print(f"=" * 60)


def print_recommendations(data):
    """打印推荐结果"""
    if not data:
        return
    
    print(f"\n" + "=" * 60)
    print(f"🎯 推荐结果")
    print(f"=" * 60)
    
    # 转写文本
    if "transcription" in data:
        print(f"\n📝 识别文本: '{data['transcription']}'")
        if data.get('language'):
            print(f"   语言: {data['language']}")
        if data.get('duration'):
            print(f"   时长: {data['duration']:.2f} 秒")
    
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
    print("🎤 语音推荐 CLI（文件上传模式）")
    print("=" * 60)
    
    # 检查文件
    audio_file = check_file(args.file)
    
    # 只转写模式
    if args.text_only:
        result = transcribe_audio(audio_file)
        print_transcription(result)
        return
    
    # 完整推荐模式（一步到位）
    result = recommend_by_voice(audio_file, top_k=args.top)
    
    if result:
        print_recommendations(result)
    else:
        # 降级：分步执行
        print("\n⚠️  一步式推荐失败，尝试分步执行...")
        
        # 1. 转写
        asr_result = transcribe_audio(audio_file)
        if not asr_result:
            print("\n✗ 转写失败，无法继续")
            sys.exit(1)
        
        text = asr_result.get('text', '')
        if not text:
            print("\n✗ 转写结果为空")
            sys.exit(1)
        
        print(f"\n✓ 识别文本: '{text}'")
        
        # 2. 推荐
        reco_result = recommend_by_text(text, top_k=args.top)
        if reco_result:
            # 补充转写信息
            reco_result['transcription'] = text
            reco_result['language'] = asr_result.get('language')
            reco_result['duration'] = asr_result.get('duration')
            print_recommendations(reco_result)
        else:
            print("\n✗ 推荐失败")
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 已取消")
        sys.exit(0)