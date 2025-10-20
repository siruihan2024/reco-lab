#!/usr/bin/env bash
export NCCL_IGNORE_DISABLED_P2P=1
export NCCL_SHM_DISABLE=1
export NCCL_P2P_DISABLE=1
# 查找并杀死占用 30001 的进程
lsof -ti:30001 | xargs kill -9

# 查找并杀死占用 30002 的进程
lsof -ti:30002 | xargs kill -9

# 查找并杀死占用 30003 的进程
lsof -ti:30003 | xargs kill -9

# 验证端口已释放
lsof -i:30001,30002,30003


CUDA_VISIBLE_DEVICES=6 python -m sglang.launch_server \
  --model /data/xbx/Qwen/Qwen3-Embedding-8B \
  --port 30001 \
  --context-length 8192 \
  --is-embedding \
  --mem-fraction-static 0.8 \
  --trust-remote-code &

CUDA_VISIBLE_DEVICES=7 python -m sglang.launch_server \
  --model /data/xbx/Qwen/Qwen3-Reranker-8B \
  --host 0.0.0.0 \
  --disable-radix-cache \
  --chunked-prefill-size -1 \
  --attention-backend triton \
  --is-embedding \
  --mem-fraction-static 0.8 \
  --port 30002 &



# CUDA_VISIBLE_DEVICES=4,5 python -m sglang.launch_server \
#   --model /data/xbx/Qwen/Qwen3-4B-Instruct-2507-FP8 \
#   --host 0.0.0.0 \
#   --port 30003 \
#   --context-length 32768 \
#   --tp 2  &

# CUDA_VISIBLE_DEVICES=4,5 python -m sglang.launch_server \
#   --model /data/xbx/Qwen/Qwen3-VL-4B-Instruct-FP8 \
#   --host 0.0.0.0 \
#   --port 30003 \
#   --mem-fraction-static 0.8 \
#   --tp 2  &

CUDA_VISIBLE_DEVICES=5 python -m sglang.launch_server \
  --model /data/xbx/Qwen/Qwen3-VL-4B-Instruct-FP8 \
  --host 0.0.0.0 \
  --port 30003 \
  --mem-fraction-static 0.8 &

# curl -s http://127.0.0.1:30003/v1/chat/completions \
#   -H "Content-Type: application/json" \
#   -d '{
#     "model": "qwen3-8b",
#     "messages": [
#       {"role": "user", "content": "帮我生成10个英文的淘宝产品"}
#     ],
#     "temperature": 0.7,
#     "max_tokens": 512
#   }'