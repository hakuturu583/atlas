#!/bin/bash
# MCPサーバー起動スクリプト

cd "$(dirname "$0")"

# uvで実行
exec uv run python -m app.mcp.server
