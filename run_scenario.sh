#!/bin/bash
# シナリオ実行スクリプト（CARLA起動・終了機能付き）
#
# 使い方:
#   ./run_scenario.sh <logical-uuid> <parameter-uuid> [OPTIONS]
#
# オプション:
#   --start-carla     シナリオ実行前にCARLAを起動
#   --stop-carla      シナリオ実行後にCARLAを停止
#   --carla-path      CARLAのパス（デフォルト: 設定ファイルから読み込み）
#   --carla-map       CARLAマップ（デフォルト: Town10HD_Opt）
#   --carla-port      CARLAポート（デフォルト: 2000）
#
# 例:
#   ./run_scenario.sh <uuid> <uuid> --start-carla --stop-carla

set -e

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# デフォルト値
START_CARLA=false
STOP_CARLA=false
CARLA_PATH=""
CARLA_MAP="Town10HD_Opt"
CARLA_PORT=2000
CARLA_QUALITY="Low"
RENDER_OFFSCREEN=true

# 設定ファイルから読み込み
SETTINGS_FILE="data/carla_settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    CARLA_PATH=$(jq -r '.carla_path // ""' "$SETTINGS_FILE")
    CARLA_MAP=$(jq -r '.default_map // "Town10HD_Opt"' "$SETTINGS_FILE")
    CARLA_PORT=$(jq -r '.default_port // 2000' "$SETTINGS_FILE")
    CARLA_QUALITY=$(jq -r '.quality_level // "Low"' "$SETTINGS_FILE")
fi

# 引数チェック
if [ $# -lt 2 ]; then
    echo -e "${RED}Usage: $0 <logical-uuid> <parameter-uuid> [OPTIONS]${NC}"
    echo ""
    echo "Options:"
    echo "  --start-carla      シナリオ実行前にCARLAを起動"
    echo "  --stop-carla       シナリオ実行後にCARLAを停止"
    echo "  --carla-path PATH  CARLAのパス"
    echo "  --carla-map MAP    CARLAマップ (default: Town10HD_Opt)"
    echo "  --carla-port PORT  CARLAポート (default: 2000)"
    echo ""
    echo "Example:"
    echo "  $0 ad353814-59cf-4911-9666-ed1c60268717 23991fb4-809d-45c7-9846-09bc226dfa7c --start-carla --stop-carla"
    exit 1
fi

LOGICAL_UUID=$1
PARAMETER_UUID=$2
shift 2

# オプション解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --start-carla)
            START_CARLA=true
            shift
            ;;
        --stop-carla)
            STOP_CARLA=true
            shift
            ;;
        --carla-path)
            CARLA_PATH="$2"
            shift 2
            ;;
        --carla-map)
            CARLA_MAP="$2"
            shift 2
            ;;
        --carla-port)
            CARLA_PORT="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

SCRIPT_FILE="scenarios/${LOGICAL_UUID}.py"

if [ ! -f "$SCRIPT_FILE" ]; then
    echo -e "${RED}Error: シナリオファイルが見つかりません: $SCRIPT_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      シナリオ実行                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}論理UUID:${NC} $LOGICAL_UUID"
echo -e "${GREEN}パラメータUUID:${NC} $PARAMETER_UUID"
echo ""

# CARLAを起動
CARLA_PID=""
if [ "$START_CARLA" = true ]; then
    if [ -z "$CARLA_PATH" ]; then
        echo -e "${RED}Error: CARLAパスが設定されていません${NC}"
        echo "  設定ファイル ($SETTINGS_FILE) を確認するか、--carla-path オプションを使用してください"
        exit 1
    fi

    echo -e "${YELLOW}CARLA起動中...${NC}"
    echo "  パス: $CARLA_PATH"
    echo "  マップ: $CARLA_MAP"
    echo "  ポート: $CARLA_PORT"
    echo "  品質: $CARLA_QUALITY"

    # CARLAが既に起動しているかチェック
    if pgrep -f "CarlaUE5" > /dev/null; then
        echo -e "${YELLOW}Warning: CARLAは既に起動しています${NC}"
    else
        cd "$CARLA_PATH" || exit 1

        # 起動コマンドを構築
        CARLA_CMD="./CarlaUE5.sh"
        CARLA_ARGS="-quality-level=${CARLA_QUALITY} -carla-rpc-port=${CARLA_PORT}"

        if [ "$RENDER_OFFSCREEN" = true ]; then
            CARLA_ARGS="$CARLA_ARGS -RenderOffScreen"
        fi

        # バックグラウンドで起動
        nohup $CARLA_CMD $CARLA_ARGS > /dev/null 2>&1 &
        CARLA_PID=$!

        cd - > /dev/null

        echo -e "${GREEN}✓ CARLA起動中 (PID: $CARLA_PID)${NC}"

        # CARLAの起動を待つ（最大60秒）
        echo -e "${YELLOW}CARLAの準備を待っています...${NC}"
        for i in {1..60}; do
            if python3 -c "import carla; carla.Client('localhost', $CARLA_PORT, timeout=2.0).get_world()" 2>/dev/null; then
                echo -e "${GREEN}✓ CARLAの準備完了${NC}"
                break
            fi
            if [ $i -eq 60 ]; then
                echo -e "${RED}Error: CARLAが起動しませんでした${NC}"
                exit 1
            fi
            sleep 1
        done
        echo ""
    fi
fi

# シナリオを実行
echo -e "${YELLOW}シナリオ実行中...${NC}"
uv run python "$SCRIPT_FILE" \
    --logical-uuid "$LOGICAL_UUID" \
    --parameter-uuid "$PARAMETER_UUID"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ シナリオ実行完了${NC}"
    echo ""
    echo "出力ファイル:"
    echo "  動画: data/videos/${LOGICAL_UUID}_${PARAMETER_UUID}.mp4"
else
    echo ""
    echo -e "${RED}✗ シナリオ実行失敗 (Exit code: $EXIT_CODE)${NC}"
fi

# CARLAを停止
if [ "$STOP_CARLA" = true ]; then
    echo ""
    echo -e "${YELLOW}CARLA停止中...${NC}"

    # CARLAプロセスを検索
    CARLA_PIDS=$(pgrep -f "CarlaUE5" 2>/dev/null)

    if [ -n "$CARLA_PIDS" ]; then
        echo "  CARLAプロセス: $CARLA_PIDS"

        # 優しく終了
        for pid in $CARLA_PIDS; do
            kill -TERM $pid 2>/dev/null
        done

        # 終了を待つ（最大10秒）
        for i in {1..10}; do
            sleep 1
            if ! pgrep -f "CarlaUE5" > /dev/null; then
                break
            fi
        done

        # まだ動いている場合は強制終了
        CARLA_PIDS=$(pgrep -f "CarlaUE5" 2>/dev/null)
        if [ -n "$CARLA_PIDS" ]; then
            echo -e "${YELLOW}  強制終了中...${NC}"
            for pid in $CARLA_PIDS; do
                kill -9 $pid 2>/dev/null
            done
        fi

        echo -e "${GREEN}✓ CARLA停止完了${NC}"
    else
        echo -e "${GREEN}✓ CARLAは既に停止しています${NC}"
    fi
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      完了                              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"

exit $EXIT_CODE
