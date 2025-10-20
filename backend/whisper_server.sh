#!/usr/bin/env bash
# 启动 Whisper ASR 服务

# 杀死占用端口的进程
lsof -ti:30004 | xargs kill -9 2>/dev/null

# 激活虚拟环境
source /data/xbx/kdd_env/bin/activate

# 设置环境变量
export WHISPER_MODEL=small
# 暂时使用 CPU（避免 cuDNN 问题）
export CUDA_VISIBLE_DEVICES=""  # 空字符串强制使用 CPU

# 启动服务
echo "🎤 Starting Whisper ASR Service (CPU mode)..."
nohup python -m uvicorn app.whisper_server:app \
    --host 0.0.0.0 \
    --port 30004 \
    --log-level info > whisper_server.log 2>&1 &

echo "✓ Whisper service started on port 30004"
echo "  Log: tail -f whisper_server.log"
echo "  Test: curl -X POST http://localhost:30004/health"