#!/bin/bash
# ========================================
# Docker Swarm Teardown Script
# Removes ATLAS stack and cleans up resources
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
# Step 1: スタックの削除
# ========================================
remove_stack() {
    log_info "Removing ATLAS stack '${STACK_NAME}'..."

    if docker stack ls | grep -q ${STACK_NAME}; then
        docker stack rm ${STACK_NAME} || {
            log_error "Failed to remove stack"
            exit 1
        }

        # サービスが完全に削除されるまで待つ
        log_info "Waiting for services to be removed..."
        timeout=60
        elapsed=0
        while docker stack ps ${STACK_NAME} 2>/dev/null | grep -q ${STACK_NAME}; do
            sleep 2
            elapsed=$((elapsed + 2))
            if [ $elapsed -ge $timeout ]; then
                log_warn "Timed out waiting for services to be removed"
                break
            fi
        done

        log_success "Stack removed"
    else
        log_warn "Stack '${STACK_NAME}' not found"
    fi
}

# ========================================
# Step 2: ネットワークの削除
# ========================================
remove_networks() {
    log_info "Removing networks..."

    # atlas-networkの削除
    if docker network ls | grep -q "${STACK_NAME}_atlas-network"; then
        docker network rm ${STACK_NAME}_atlas-network 2>/dev/null || {
            log_warn "Could not remove network (may still be in use)"
        }
    fi

    log_success "Networks cleaned up"
}

# ========================================
# Step 3: ボリュームの削除（オプション）
# ========================================
remove_volumes() {
    if [ "$REMOVE_VOLUMES" = "true" ]; then
        log_info "Removing volumes..."

        for volume in huggingface-cache scenario-logs scenario-videos scenario-rerun; do
            volume_name="${STACK_NAME}_${volume}"
            if docker volume ls | grep -q ${volume_name}; then
                docker volume rm ${volume_name} 2>/dev/null || {
                    log_warn "Could not remove volume ${volume_name}"
                }
            fi
        done

        log_success "Volumes removed"
    else
        log_info "Skipping volume removal (use --remove-volumes to delete)"
    fi
}

# ========================================
# Step 4: ローカルレジストリの停止（オプション）
# ========================================
stop_registry() {
    if [ "$STOP_REGISTRY" = "true" ]; then
        log_info "Stopping local Docker registry..."

        if docker ps --filter "name=registry" | grep -q registry; then
            docker stop registry || {
                log_warn "Failed to stop registry"
            }
            docker rm registry || {
                log_warn "Failed to remove registry"
            }
            log_success "Registry stopped and removed"
        else
            log_warn "Registry not running"
        fi
    else
        log_info "Keeping local registry running (use --stop-registry to stop)"
    fi
}

# ========================================
# Step 5: イメージの削除（オプション）
# ========================================
remove_images() {
    if [ "$REMOVE_IMAGES" = "true" ]; then
        log_info "Removing Docker images..."

        for image in atlas-vla-base atlas-vla-dummy atlas-vla-alpamayo atlas-scenario; do
            if docker images | grep -q ${image}; then
                docker rmi ${image}:latest 2>/dev/null || {
                    log_warn "Could not remove image ${image}:latest"
                }
            fi

            # ローカルレジストリのイメージも削除
            registry_image="localhost:${REGISTRY_PORT}/${image}:latest"
            if docker images | grep -q "${registry_image}"; then
                docker rmi ${registry_image} 2>/dev/null || {
                    log_warn "Could not remove image ${registry_image}"
                }
            fi
        done

        log_success "Images removed"
    else
        log_info "Keeping Docker images (use --remove-images to delete)"
    fi
}

# ========================================
# Step 6: Swarmの解除（オプション）
# ========================================
leave_swarm() {
    if [ "$LEAVE_SWARM" = "true" ]; then
        log_warn "Leaving Docker Swarm..."
        log_warn "This will remove all stacks and services!"

        read -p "Are you sure? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker swarm leave --force || {
                log_error "Failed to leave swarm"
                exit 1
            }
            log_success "Left Docker Swarm"
        else
            log_info "Cancelled swarm leave"
        fi
    else
        log_info "Keeping Docker Swarm active (use --leave-swarm to deactivate)"
    fi
}

# ========================================
# メイン処理
# ========================================
main() {
    echo "========================================"
    echo "  ATLAS Docker Swarm Teardown"
    echo "========================================"
    echo ""

    # 引数パース
    while [[ $# -gt 0 ]]; do
        case $1 in
            --stack-name)
                STACK_NAME="$2"
                shift 2
                ;;
            --remove-volumes)
                REMOVE_VOLUMES=true
                shift
                ;;
            --stop-registry)
                STOP_REGISTRY=true
                shift
                ;;
            --remove-images)
                REMOVE_IMAGES=true
                shift
                ;;
            --leave-swarm)
                LEAVE_SWARM=true
                shift
                ;;
            --full-cleanup)
                REMOVE_VOLUMES=true
                STOP_REGISTRY=true
                REMOVE_IMAGES=true
                LEAVE_SWARM=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --stack-name NAME    Stack name to remove (default: atlas)"
                echo "  --remove-volumes     Remove all volumes (data will be lost)"
                echo "  --stop-registry      Stop and remove local registry"
                echo "  --remove-images      Remove all Docker images"
                echo "  --leave-swarm        Leave Docker Swarm (removes all stacks)"
                echo "  --full-cleanup       Perform complete cleanup (all of the above)"
                echo "  --help               Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Step 1: スタック削除
    remove_stack

    # Step 2: ネットワーク削除
    remove_networks

    # Step 3: ボリューム削除
    remove_volumes

    # Step 4: レジストリ停止
    stop_registry

    # Step 5: イメージ削除
    remove_images

    # Step 6: Swarm解除
    leave_swarm

    echo ""
    echo "========================================"
    log_success "Teardown completed successfully!"
    echo "========================================"
    echo ""
}

main "$@"
