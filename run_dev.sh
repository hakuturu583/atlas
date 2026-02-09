#!/bin/bash
# ATLAS - Development startup script
#
# FiftyOne + FastAPI (with WebSocket terminal)を起動

set -e

echo "🚀 Starting ATLAS..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# FiftyOneの停止（既存プロセス）
echo "🛑 Stopping existing FiftyOne processes..."
pkill -f "fiftyone_integration.py launch" || true
sleep 2

# FiftyOneをバックグラウンドで起動（ブラウザは開かない）
echo "📊 Starting FiftyOne..."
# 環境変数でブラウザの自動起動を無効化
export FIFTYONE_DEFAULT_APP_PORT=5151
nohup uv run python scripts/fiftyone_integration.py launch > logs/fiftyone.log 2>&1 &
FIFTYONE_PID=$!
echo "  FiftyOne PID: $FIFTYONE_PID"

# FiftyOneの起動を待つ（最大30秒）
echo "⏳ Waiting for FiftyOne to start..."
for i in {1..30}; do
    if curl -s http://localhost:5151 > /dev/null 2>&1; then
        echo "✓ FiftyOne is ready at http://localhost:5151"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  FiftyOne did not start in time. Check logs/fiftyone.log"
    fi
    sleep 1
done

# FastAPIを起動
echo "🌐 Starting FastAPI (http://localhost:8000)..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🎯 ATLAS is ready!"
echo "  📱 Web UI: http://localhost:8000"
echo "  📊 FiftyOne: http://localhost:5151"
echo "  📋 Logs: logs/fiftyone.log"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# FastAPIを起動（フォアグラウンド）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
