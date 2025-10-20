#!/usr/bin/env bash
set -euo pipefail

export EMBED_BASE_URL="http://127.0.0.1:30001/v1"
export RERANK_BASE_URL="http://127.0.0.1:30002/v1"
export CHAT_BASE_URL="http://127.0.0.1:30003/v1"
export OPENAI_API_KEY="EMPTY"
export PRODUCTS_PATH="/data/xbx/KDD/app/data/products.json"

# 允许外部传 PORT 指定端口，否则按候选列表自动找空闲端口
CANDIDATES=("${PORT:-8081}" 8080 18081 18082 19000)
PORT=""

for p in "${CANDIDATES[@]}"; do
  if ! ss -ltn | awk '{print $4}' | grep -q ":$p$"; then
    PORT="$p"
    break
  fi
done

if [ -z "${PORT}" ]; then
  # 兜底：系统随机分配高位端口
  PORT=$(python - <<'PY'
import socket
s=socket.socket()
s.bind(('',0))
print(s.getsockname()[1])
s.close()
PY
)
fi

echo "Starting server on 0.0.0.0:${PORT}"
uvicorn app.server:app --host 0.0.0.0 --port "${PORT}"

