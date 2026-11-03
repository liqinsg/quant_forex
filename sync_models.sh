#!/bin/bash
set -euo pipefail

DEV="/home/ubuntu/projects/forex_oanda_v7_dev"
PROD="/home/ubuntu/projects/forex_oanda_v7"

if [[ "$PWD" == "$DEV" ]]; then
    SRC="$DEV"
    DST="$PROD"
    echo ">>> dev → 运行版"
elif [[ "$PWD" == "$PROD" ]]; then
    SRC="$PROD"
    DST="$DEV"
    echo ">>> 运行版 → dev"
else
    echo "ERROR: cd to dev or v7 directory first"
    exit 1
fi

SRC_BASE="$SRC/models/model_store"
DST_BASE="$DST/models/model_store"

mkdir -p "$DST_BASE/practice" "$DST_BASE/live"

echo "Copying practice models..."
cp -f "$SRC_BASE/practice"/lgb_*.pkl "$DST_BASE/practice/"

echo "Copying live models..."
cp -f "$SRC_BASE/live"/lgb_*.pkl "$DST_BASE/live/"

echo "Sync complete."
echo "practice: $(ls "$DST_BASE/practice"/lgb_*.pkl 2>/dev/null | wc -l) files"
echo "live:      $(ls "$DST_BASE/live"/lgb_*.pkl 2>/dev/null | wc -l) files"