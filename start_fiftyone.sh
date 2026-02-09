#!/bin/bash
# FiftyOne GUIを起動するスクリプト

set -e

echo "📊 Starting FiftyOne GUI..."

# データセットの存在確認
DATASET_NAME="${1:-carla-scenarios}"
PORT="${2:-5151}"

echo "  Dataset: $DATASET_NAME"
echo "  Port: $PORT"

# 既存のFiftyOneプロセスを停止
echo "🛑 Stopping existing FiftyOne processes..."
pkill -f "fiftyone_integration.py launch" || true
sleep 1

# FiftyOneを起動
echo "🚀 Launching FiftyOne..."
uv run python scripts/fiftyone_integration.py launch \
    --dataset-name "$DATASET_NAME" \
    --port "$PORT"
