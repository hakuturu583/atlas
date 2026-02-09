#!/bin/bash
# FiftyOne API Helper Script
#
# Claude CodeからFiftyOne UIを操作するためのヘルパースクリプト

API_BASE="http://localhost:8000/api/fiftyone"

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# データセットの統計情報を取得
get_stats() {
    echo -e "${YELLOW}データセット統計情報を取得中...${NC}"
    curl -s "${API_BASE}/stats" | jq '.'
}

# サンプル一覧を取得
list_samples() {
    local limit=${1:-10}
    echo -e "${YELLOW}サンプル一覧を取得中 (limit: ${limit})...${NC}"
    curl -s "${API_BASE}/samples?limit=${limit}" | jq '.'
}

# ヘルプ
show_help() {
    cat << EOF
FiftyOne API Helper

使い方:
  ./fiftyone_api.sh <command> [args]

コマンド:
  stats           データセット統計情報を取得
  list [limit]    サンプル一覧を取得 (デフォルト: 10件)
  help            このヘルプを表示

例:
  ./fiftyone_api.sh stats
  ./fiftyone_api.sh list 5

EOF
}

# メイン処理
case "$1" in
    stats)
        get_stats
        ;;
    list)
        list_samples "$2"
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
