#!/bin/bash
# ========================================
# Docker Swarm Deployment Script
# Deploys ATLAS stack (CARLA + Scenario + VLA)
# ========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STACK_NAME="${STACK_NAME:-atlas}"
REGISTRY_PORT="${REGISTRY_PORT:-5000}"

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
    else
        log_info "Skipping atlas-vla-alpamayo (set BUILD_ALPAMAYO=true to build)"
    fi

    # シナリオ実行コンテナ
    log_info "Building atlas-scenario..."
    docker build -t atlas-scenario:latest -f docker/Dockerfile.scenario . || {
        log_error "Failed to build atlas-scenario"
        exit 1
    }

    log_success "All images built successfully"
}

# ========================================
# Step 4: イメージをローカルレジストリにプッシュ
# ========================================
push_images() {
    log_info "Pushing images to local registry..."

    # タグ付け＆プッシュ
    for image in atlas-vla-dummy atlas-scenario; do
        log_info "Pushing ${image}..."
        docker tag ${image}:latest localhost:${REGISTRY_PORT}/${image}:latest
        docker push localhost:${REGISTRY_PORT}/${image}:latest || {
            log_error "Failed to push ${image}"
            exit 1
        }
    done

    if [ "$BUILD_ALPAMAYO" = "true" ]; then
        log_info "Pushing atlas-vla-alpamayo..."
        docker tag atlas-vla-alpamayo:latest localhost:${REGISTRY_PORT}/atlas-vla-alpamayo:latest
        docker push localhost:${REGISTRY_PORT}/atlas-vla-alpamayo:latest || {
            log_error "Failed to push atlas-vla-alpamayo"
            exit 1
        }
    fi

    log_success "All images pushed to localhost:${REGISTRY_PORT}"
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

    # スタックをデプロイ
    docker stack deploy -c docker-compose.stack.yml ${STACK_NAME} || {
        log_error "Failed to deploy stack"
        exit 1
    }

    log_success "ATLAS stack deployed as '${STACK_NAME}'"
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
            --with-alpamayo)
                BUILD_ALPAMAYO=true
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
                echo "Options:"
                echo "  --with-alpamayo       Build and deploy Alpamayo VLA service"
                echo "  --stack-name NAME     Stack name (default: atlas)"
                echo "  --registry-port PORT  Local registry port (default: 5000)"
                echo "  --help                Show this help message"
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
