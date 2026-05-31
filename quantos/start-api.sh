#!/bin/bash
# QuantOS API 启动脚本 - 自动替换环境变量
cd "$(dirname "$0")"

# 加载 .env 文件
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# 生成临时配置文件（替换环境变量）
cat app/api/etc/api.yaml | envsubst > /tmp/api.yaml

echo "Starting QuantOS API on port ${APP_PORT:-8888}..."
./bin/api -f /tmp/api.yaml
