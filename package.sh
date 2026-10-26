#!/bin/bash
set -euo pipefail

# ==========================================
# Forex OANDA Bot v6.8x — 打包脚本
# 输出: ../forex_oanda_v6.8x-YYYYMMDD-HHMMSS.zip
# ==========================================

NAME="forex_oanda_v6.8x"
VERSION=$(date +%Y%m%d-%H%M%S)
OUTPUT="../${NAME}-${VERSION}.zip"

# 回到项目根目录
cd "$(dirname "$0")"

echo "📦 正在打包 ..."
zip -r "$OUTPUT" . \
  -x "*.git*" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x ".venv/*" \
  -x "./config/.env" \
  -x "./data/*/datasets/*" \
  -x "./models/model_store/*/*" \
  -x "./reports/*" \
  -x "./nohup.out" \
  -x "*.zip"

echo "✅ 打包完成: $OUTPUT"
ls -lh "$OUTPUT"
