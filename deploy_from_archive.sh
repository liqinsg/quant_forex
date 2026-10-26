#!/bin/bash
set -euo pipefail

# ==========================================
# Forex Bot — 从压缩包一键部署
# 用法: ./deploy_from_archive.sh 压缩包名.zip
# ==========================================

ZIP_FILE="${1:-}"
if [[ -z "$ZIP_FILE" || ! -f "$ZIP_FILE" ]]; then
    echo "用法: $0 forex_oanda_v6.8x-XXXXXXXX-XXXXXX.zip"
    exit 1
fi

echo "🚀 部署: $ZIP_FILE"

# 解压（自动去掉外层目录）
unzip -q "$ZIP_FILE" -d temp_extract
mv temp_extract/* .
rm -rf temp_extract

# 赋权限
chmod +x deploy.sh package.sh

# 初始化
./deploy.sh init

echo ""
echo "✅ 部署完成！"
echo "下一步："
echo "  1. cp .env.example .env"
echo "  2. nano .env 填入 OANDA 凭证"
echo "  3. ./deploy.sh train"
echo "  4. ./deploy.sh daemon"
