#!/bin/bash

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    ATLAS System Shutdown Manager      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# オプション解析
SHUTDOWN_SANDBOX=true
SHUTDOWN_FLASK=true
SHUTDOWN_FIFTYONE=true
SHUTDOWN_CARLA=true
CLEAN_DOCKER=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --sandbox-only)
            SHUTDOWN_FLASK=false
            SHUTDOWN_MCP=false
            shift
            ;;
        --flask-only)
            SHUTDOWN_SANDBOX=false
            SHUTDOWN_FIFTYONE=false
            shift
            ;;
        --fiftyone-only)
            SHUTDOWN_SANDBOX=false
            SHUTDOWN_FLASK=false
            SHUTDOWN_CARLA=false
            shift
            ;;
        --carla-only)
            SHUTDOWN_SANDBOX=false
            SHUTDOWN_FLASK=false
            SHUTDOWN_MCP=false
            shift
            ;;
        --no-carla)
            SHUTDOWN_CARLA=false
            shift
            ;;
        --clean-docker)
            CLEAN_DOCKER=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./shutdown.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --sandbox-only   Sandboxコンテナのみシャットダウン"
            echo "  --flask-only     Flaskアプリケーションのみシャットダウン"
            echo "  --mcp-only       MCPサーバーのみシャットダウン"
            echo "  --carla-only     CARLAサーバーのみシャットダウン"
            echo "  --no-carla       CARLAはシャットダウンしない"
            echo "  --clean-docker   Dockerイメージも削除"
            echo "  -f, --force      確認なしで実行"
            echo "  -h, --help       このヘルプを表示"
            echo ""
            echo "Examples:"
            echo "  ./shutdown.sh                   # すべてシャットダウン"
            echo "  ./shutdown.sh --flask-only      # Flaskアプリのみ停止"
            echo "  ./shutdown.sh --no-carla        # CARLAは残して他を停止"
            echo "  ./shutdown.sh --carla-only      # CARLAのみ停止"
            echo "  ./shutdown.sh --clean-docker    # Docker完全クリーンアップ"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# 確認プロンプト（forceフラグがない場合）
if [ "$FORCE" = false ]; then
    echo -e "${YELLOW}This will shutdown:${NC}"
    [ "$SHUTDOWN_FLASK" = true ] && echo "  ✓ Flask application (port 8000)"
    [ "$SHUTDOWN_MCP" = true ] && echo "  ✓ MCP server"
    [ "$SHUTDOWN_CARLA" = true ] && echo "  ✓ CARLA server"
    [ "$SHUTDOWN_SANDBOX" = true ] && echo "  ✓ Sandbox Docker containers"
    [ "$CLEAN_DOCKER" = true ] && echo "  ✓ Docker images"
    echo ""
    read -p "Continue? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Shutdown cancelled${NC}"
        exit 0
    fi
fi

echo ""

# Flask アプリケーションのシャットダウン
if [ "$SHUTDOWN_FLASK" = true ]; then
    echo -e "${CYAN}[1/3] Shutting down Flask application...${NC}"

    # ポート8000で動作しているプロセスを検索
    FLASK_PID=$(lsof -ti:8000 2>/dev/null)

    if [ -n "$FLASK_PID" ]; then
        echo -e "${YELLOW}  Found Flask process (PID: $FLASK_PID)${NC}"
        kill $FLASK_PID 2>/dev/null

        # プロセスが終了するまで待つ
        sleep 2

        # まだ動いている場合は強制終了
        if kill -0 $FLASK_PID 2>/dev/null; then
            echo -e "${YELLOW}  Forcing shutdown...${NC}"
            kill -9 $FLASK_PID 2>/dev/null
        fi

        echo -e "${GREEN}  ✓ Flask application stopped${NC}"
    else
        echo -e "${GREEN}  ✓ Flask application not running${NC}"
    fi
    echo ""
fi

# FiftyOne のシャットダウン
if [ "$SHUTDOWN_FIFTYONE" = true ]; then
    echo -e "${CYAN}[2/3] Shutting down FiftyOne...${NC}"

    # FiftyOneプロセスを検索
    FIFTYONE_PIDS=$(pgrep -f "fiftyone_integration.py launch" 2>/dev/null)

    if [ -n "$FIFTYONE_PIDS" ]; then
        echo -e "${YELLOW}  Found FiftyOne processes: $FIFTYONE_PIDS${NC}"
        for pid in $FIFTYONE_PIDS; do
            kill $pid 2>/dev/null
        done

        sleep 1

        # まだ動いているプロセスを強制終了
        FIFTYONE_PIDS=$(pgrep -f "fiftyone_integration.py launch" 2>/dev/null)
        if [ -n "$FIFTYONE_PIDS" ]; then
            echo -e "${YELLOW}  Forcing shutdown...${NC}"
            for pid in $FIFTYONE_PIDS; do
                kill -9 $pid 2>/dev/null
            done
        fi

        echo -e "${GREEN}  ✓ FiftyOne stopped${NC}"
    else
        echo -e "${GREEN}  ✓ FiftyOne not running${NC}"
    fi
    echo ""
fi

# CARLA サーバーのシャットダウン
if [ "$SHUTDOWN_CARLA" = true ]; then
    echo -e "${CYAN}[3/4] Shutting down CARLA server...${NC}"

    # CARLAプロセスを検索（CarlaUE4またはCarlaUnreal）
    CARLA_PIDS=$(pgrep -f "Carla.*\.sh|CarlaUE4" 2>/dev/null)

    if [ -n "$CARLA_PIDS" ]; then
        echo -e "${YELLOW}  Found CARLA processes: $CARLA_PIDS${NC}"

        # まず優しく終了させる
        for pid in $CARLA_PIDS; do
            kill -TERM $pid 2>/dev/null
        done

        # 終了を待つ（最大10秒）
        echo -e "${YELLOW}  Waiting for CARLA to shutdown gracefully...${NC}"
        for i in {1..10}; do
            sleep 1
            CARLA_PIDS=$(pgrep -f "Carla.*\.sh|CarlaUE4" 2>/dev/null)
            if [ -z "$CARLA_PIDS" ]; then
                break
            fi
            echo -ne "  ."
        done
        echo ""

        # まだ動いているプロセスを強制終了
        CARLA_PIDS=$(pgrep -f "Carla.*\.sh|CarlaUE4" 2>/dev/null)
        if [ -n "$CARLA_PIDS" ]; then
            echo -e "${YELLOW}  Forcing CARLA shutdown...${NC}"
            for pid in $CARLA_PIDS; do
                kill -9 $pid 2>/dev/null
            done
            # プロセスグループ全体を終了
            for pid in $CARLA_PIDS; do
                pkill -9 -P $pid 2>/dev/null
            done
        fi

        echo -e "${GREEN}  ✓ CARLA server stopped${NC}"
    else
        echo -e "${GREEN}  ✓ CARLA server not running${NC}"
    fi
    echo ""
fi

# Sandbox Docker コンテナのシャットダウン
if [ "$SHUTDOWN_SANDBOX" = true ]; then
    echo -e "${CYAN}[4/4] Shutting down Sandbox containers...${NC}"

    if [ -d "sandbox" ]; then
        cd sandbox

        # Dockerコンテナが動いているか確認
        CONTAINERS=$(docker-compose ps -q 2>/dev/null)

        if [ -n "$CONTAINERS" ]; then
            echo -e "${YELLOW}  Stopping sandbox containers...${NC}"

            if [ "$CLEAN_DOCKER" = true ]; then
                docker-compose down --rmi all -v 2>/dev/null
                echo -e "${GREEN}  ✓ Sandbox containers, volumes and images removed${NC}"
            else
                docker-compose down 2>/dev/null
                echo -e "${GREEN}  ✓ Sandbox containers stopped${NC}"
            fi
        else
            echo -e "${GREEN}  ✓ Sandbox containers not running${NC}"
        fi

        cd ..
    else
        echo -e "${YELLOW}  Sandbox directory not found, skipping...${NC}"
    fi
    echo ""
fi

# システム状態の確認
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         System Status Check            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# ポート8000の確認
PORT_8000=$(lsof -ti:8000 2>/dev/null)
if [ -n "$PORT_8000" ]; then
    echo -e "${RED}✗ Port 8000 still in use (PID: $PORT_8000)${NC}"
else
    echo -e "${GREEN}✓ Port 8000 is free${NC}"
fi

# FiftyOneの確認
FIFTYONE_CHECK=$(pgrep -f "fiftyone_integration.py launch" 2>/dev/null)
if [ -n "$FIFTYONE_CHECK" ]; then
    echo -e "${RED}✗ FiftyOne still running (PID: $FIFTYONE_CHECK)${NC}"
else
    echo -e "${GREEN}✓ FiftyOne stopped${NC}"
fi

# CARLAサーバーの確認
CARLA_CHECK=$(pgrep -f "Carla.*\.sh|CarlaUE4" 2>/dev/null)
if [ -n "$CARLA_CHECK" ]; then
    echo -e "${RED}✗ CARLA server still running (PID: $CARLA_CHECK)${NC}"
else
    echo -e "${GREEN}✓ CARLA server stopped${NC}"
fi

# Dockerコンテナの確認
if [ -d "sandbox" ]; then
    cd sandbox
    DOCKER_CHECK=$(docker-compose ps -q 2>/dev/null)
    cd ..

    if [ -n "$DOCKER_CHECK" ]; then
        echo -e "${RED}✗ Sandbox containers still running${NC}"
    else
        echo -e "${GREEN}✓ Sandbox containers stopped${NC}"
    fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Shutdown completed successfully    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# 追加のクリーンアップヒント
if [ "$CLEAN_DOCKER" = false ]; then
    echo -e "${BLUE}Tip: To completely clean Docker resources:${NC}"
    echo "  ./shutdown.sh --clean-docker"
fi
