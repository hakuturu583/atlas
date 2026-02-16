#!/bin/bash
# ========================================
# Docker Swarm Deployment Script
# Deploys ATLAS stack (CARLA [必須] + Scenario [オプション] + VLA [オプション])
# ========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STACK_NAME="${STACK_NAME:-atlas}"
REGISTRY_PORT="${REGISTRY_PORT:-5000}"

# デプロイオプション
DEPLOY_SCENARIO=false
DEPLOY_AD_STACK=false
BUILD_ALPAMAYO=false

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ========================================
# Step 1: Swarmの初期化確認
# ========================================
check_swarm() {
    log_info "Checking Docker Swarm status..."

    if docker info 2>/dev/null | grep -q "Swarm: active"; then
        log_success "Docker Swarm is already active"
        return 0
    else
        log_warn "Docker Swarm is not active"
        return 1
    fi
}

init_swarm() {
    log_info "Initializing Docker Swarm..."

    # Swarmマネージャーとして初期化
    docker swarm init --advertise-addr $(hostname -I | awk '{print $1}') || {
        log_error "Failed to initialize Docker Swarm"
        exit 1
    }

    log_success "Docker Swarm initialized successfully"
}

# ========================================
# Step 2: ローカルレジストリの起動
# ========================================
start_local_registry() {
    log_info "Starting local Docker registry on port ${REGISTRY_PORT}..."

    # 既存のレジストリをチェック
    if docker ps --filter "name=registry" --filter "status=running" | grep -q registry; then
        log_success "Local registry is already running"
        return 0
    fi

    # レジストリを起動
    docker run -d \
        --name registry \
        --restart=always \
        -p ${REGISTRY_PORT}:5000 \
        registry:2 || {
        log_error "Failed to start local registry"
        exit 1
    }

    # 起動を待つ
    sleep 3

    log_success "Local registry started on localhost:${REGISTRY_PORT}"
}

# ========================================
# Step 3: Dockerイメージのビルド
# ========================================
build_images() {
    log_info "Building Docker images..."

    cd "${PROJECT_ROOT}"

    # CARLA: 公式イメージを使用（ビルド不要）
    log_info "CARLA will use official image: carlasim/carla:0.9.15"

    # AD Stackが必要な場合のみビルド
    if [ "$DEPLOY_AD_STACK" = "true" ]; then
        # gRPCコード生成
        log_info "Generating gRPC code..."
        make generate-grpc || {
            log_error "Failed to generate gRPC code"
            exit 1
        }

        # VLA Dockerfilesを生成
        log_info "Generating VLA Dockerfiles..."
        uv run python scripts/generate_dockerfiles.py || {
            log_error "Failed to generate Dockerfiles"
            exit 1
        }

        # ベースイメージ
        log_info "Building atlas-vla-base..."
        docker build -t atlas-vla-base:latest -f docker/Dockerfile.base . || {
            log_error "Failed to build atlas-vla-base"
            exit 1
        }

        # ダミーVLA
        log_info "Building atlas-vla-dummy..."
        docker build -t atlas-vla-dummy:latest -f docker/Dockerfile.dummy . || {
            log_error "Failed to build atlas-vla-dummy"
            exit 1
        }

        # Alpamayo VLA（オプション）
        if [ "$BUILD_ALPAMAYO" = "true" ]; then
            log_info "Building atlas-vla-alpamayo..."
            docker build -t atlas-vla-alpamayo:latest -f docker/Dockerfile.alpamayo . || {
                log_error "Failed to build atlas-vla-alpamayo"
                exit 1
            }
        fi
    else
        log_info "Skipping AD Stack images (--with-ad-stack not specified)"
    fi

    # シナリオ実行コンテナが必要な場合のみビルド
    if [ "$DEPLOY_SCENARIO" = "true" ]; then
        log_info "Building atlas-scenario..."
        docker build -t atlas-scenario:latest -f docker/Dockerfile.scenario . || {
            log_error "Failed to build atlas-scenario"
            exit 1
        }
    else
        log_info "Skipping scenario image (--with-scenario not specified)"
    fi

    log_success "Required images built successfully"
}

# ========================================
# Step 4: イメージをローカルレジストリにプッシュ
# ========================================
push_images() {
    log_info "Pushing images to local registry..."

    # AD Stackイメージをプッシュ
    if [ "$DEPLOY_AD_STACK" = "true" ]; then
        log_info "Pushing atlas-vla-dummy..."
        docker tag atlas-vla-dummy:latest localhost:${REGISTRY_PORT}/atlas-vla-dummy:latest
        docker push localhost:${REGISTRY_PORT}/atlas-vla-dummy:latest || {
            log_error "Failed to push atlas-vla-dummy"
            exit 1
        }

        if [ "$BUILD_ALPAMAYO" = "true" ]; then
            log_info "Pushing atlas-vla-alpamayo..."
            docker tag atlas-vla-alpamayo:latest localhost:${REGISTRY_PORT}/atlas-vla-alpamayo:latest
            docker push localhost:${REGISTRY_PORT}/atlas-vla-alpamayo:latest || {
                log_error "Failed to push atlas-vla-alpamayo"
                exit 1
            }
        fi
    fi

    # シナリオイメージをプッシュ
    if [ "$DEPLOY_SCENARIO" = "true" ]; then
        log_info "Pushing atlas-scenario..."
        docker tag atlas-scenario:latest localhost:${REGISTRY_PORT}/atlas-scenario:latest
        docker push localhost:${REGISTRY_PORT}/atlas-scenario:latest || {
            log_error "Failed to push atlas-scenario"
            exit 1
        }
    fi

    log_success "Required images pushed to localhost:${REGISTRY_PORT}"
}

# ========================================
# Step 5: スタックのデプロイ
# ========================================
deploy_stack() {
    log_info "Deploying ATLAS stack..."

    cd "${PROJECT_ROOT}"

    # GPUノードにラベル付け（ローカル環境の場合）
    log_info "Labeling GPU nodes..."
    docker node update --label-add gpu=true $(docker node ls -q) || true

    # Composeファイルのリストを構築
    COMPOSE_FILES="-c docker-compose.stack.yml"

    if [ "$DEPLOY_SCENARIO" = "true" ]; then
        log_info "Including scenario service..."
        COMPOSE_FILES="${COMPOSE_FILES} -c docker-compose.stack.scenario.yml"
    fi

    if [ "$DEPLOY_AD_STACK" = "true" ]; then
        log_info "Including AD Stack service..."
        COMPOSE_FILES="${COMPOSE_FILES} -c docker-compose.stack.adstack.yml"
    fi

    # スタックをデプロイ
    log_info "Deploying with: docker stack deploy ${COMPOSE_FILES} ${STACK_NAME}"
    docker stack deploy ${COMPOSE_FILES} ${STACK_NAME} || {
        log_error "Failed to deploy stack"
        exit 1
    }

    log_success "ATLAS stack deployed as '${STACK_NAME}'"
    log_info "Services deployed:"
    log_info "  - CARLA (必須)"
    [ "$DEPLOY_SCENARIO" = "true" ] && log_info "  - Scenario execution"
    [ "$DEPLOY_AD_STACK" = "true" ] && log_info "  - AD Stack (VLA)"
}

# ========================================
# Step 6: サービス状態の確認
# ========================================
check_services() {
    log_info "Checking service status..."

    echo ""
    docker stack services ${STACK_NAME}

    echo ""
    log_info "Waiting for services to become ready (this may take a few minutes)..."

    # 各サービスの起動を待つ
    for service in $(docker stack services ${STACK_NAME} --format "{{.Name}}"); do
        log_info "Waiting for ${service}..."
        timeout=300
        elapsed=0
        while [ $elapsed -lt $timeout ]; do
            replicas=$(docker service ls --filter "name=${service}" --format "{{.Replicas}}")
            if echo "$replicas" | grep -q "1/1"; then
                log_success "${service} is ready"
                break
            fi
            sleep 5
            elapsed=$((elapsed + 5))
        done

        if [ $elapsed -ge $timeout ]; then
            log_warn "${service} did not become ready within ${timeout}s"
        fi
    done

    echo ""
    log_success "Stack deployment completed"
}

# ========================================
# メイン処理
# ========================================
main() {
    echo "========================================"
    echo "  ATLAS Docker Swarm Deployment"
    echo "========================================"
    echo ""

    # 引数パース
    while [[ $# -gt 0 ]]; do
        case $1 in
            --with-scenario|-s)
                DEPLOY_SCENARIO=true
                shift
                ;;
            --with-ad-stack|-a)
                DEPLOY_AD_STACK=true
                shift
                ;;
            --with-alpamayo)
                BUILD_ALPAMAYO=true
                DEPLOY_AD_STACK=true  # Alpamayoを含める場合はAD Stackも有効化
                shift
                ;;
            --stack-name)
                STACK_NAME="$2"
                shift 2
                ;;
            --registry-port)
                REGISTRY_PORT="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "ATLAS Docker Swarm Deployment"
                echo "  CARLAは常にデプロイされます（必須）"
                echo "  その他のサービスはオプションです"
                echo ""
                echo "Options:"
                echo "  -s, --with-scenario       シナリオ実行コンテナをデプロイ"
                echo "  -a, --with-ad-stack       AD Stack (VLA dummy) をデプロイ"
                echo "  --with-alpamayo           Alpamayo VLAをデプロイ (--with-ad-stackも有効化)"
                echo "  --stack-name NAME         Stack name (default: atlas)"
                echo "  --registry-port PORT      Local registry port (default: 5000)"
                echo "  --help                    Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                        # CARLAのみ"
                echo "  $0 -s                     # CARLA + Scenario"
                echo "  $0 -a                     # CARLA + AD Stack (dummy)"
                echo "  $0 -s -a                  # CARLA + Scenario + AD Stack"
                echo "  $0 --with-alpamayo        # CARLA + AD Stack (Alpamayo)"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Step 1: Swarmの初期化
    if ! check_swarm; then
        init_swarm
    fi

    # Step 2: ローカルレジストリ起動
    start_local_registry

    # Step 3: イメージビルド
    build_images

    # Step 4: イメージプッシュ
    push_images

    # Step 5: スタックデプロイ
    deploy_stack

    # Step 6: サービス状態確認
    check_services

    echo ""
    echo "========================================"
    log_success "Deployment completed successfully!"
    echo "========================================"
    echo ""
    echo "Next steps:"
    echo "  - View services:   docker stack services ${STACK_NAME}"
    echo "  - View logs:       docker service logs -f ${STACK_NAME}_scenario"
    echo "  - Remove stack:    bash scripts/teardown_swarm.sh"
    echo ""
}

main "$@"
