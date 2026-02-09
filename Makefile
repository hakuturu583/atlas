.PHONY: help run dev shutdown clean install test carla-launch carla-stop carla-status carla-config fiftyone fiftyone-batch fiftyone-list fiftyone-stop cleanup-dry cleanup cleanup-full

# デフォルトターゲット
.DEFAULT_GOAL := help

# シナリオUUID（コマンドライン引数で指定）
UUID ?=

help: ## このヘルプメッセージを表示
	@echo "ATLAS - Analytic Transparent LAnguage-driven Scenario generator"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make dev       # 開発モードで起動"
	@echo "  make shutdown  # すべて停止"

install: ## 依存関係をインストール
	@echo "📦 Installing dependencies..."
	uv sync

run: install ## 本番モードで起動
	@echo "🚀 Starting ATLAS..."
	@./run.sh

dev: install ## 開発モードで起動（auto-reload）
	@echo "🔧 Starting ATLAS (Development Mode)..."
	@./run_dev.sh

shutdown: ## すべてをシャットダウン
	@./shutdown.sh

shutdown-flask: ## Flaskアプリのみシャットダウン
	@./shutdown.sh --flask-only

fiftyone: install ## FiftyOne GUIを起動
	@echo "📊 Starting FiftyOne GUI..."
	@./start_fiftyone.sh

fiftyone-batch: install ## すべての動画をembedding付きでFiftyOneに登録
	@echo "📦 Batch adding scenarios to FiftyOne with embeddings..."
	@uv run python scripts/fiftyone_integration.py batch-add --all-videos

fiftyone-batch-fast: install ## すべての動画をFiftyOneに登録（embeddingなし）
	@echo "📦 Batch adding scenarios to FiftyOne (no embeddings)..."
	@uv run python scripts/fiftyone_integration.py batch-add --all-videos --no-embeddings

fiftyone-list: install ## FiftyOneデータセット一覧を表示
	@uv run python scripts/fiftyone_integration.py list

fiftyone-stop: ## FiftyOneを停止
	@echo "🛑 Stopping FiftyOne..."
	@pkill -f "fiftyone_integration.py launch" || echo "  FiftyOne is not running"

shutdown-carla: ## CARLAのみシャットダウン
	@./shutdown.sh --carla-only

shutdown-all: ## 完全シャットダウン（Docker完全削除）
	@./shutdown.sh --clean-docker -f

clean: ## ビルド成果物をクリア
	@echo "🧹 Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .venv 2>/dev/null || true
	@cd sandbox && make clean 2>/dev/null || true
	@echo "✓ Cleaned"

cleanup-dry: install ## シナリオ関連ファイルを確認（ドライラン）
	@echo "🔍 シナリオクリーンアップ（ドライラン）..."
	@uv run python scripts/cleanup_all.py

cleanup: install ## シナリオ関連ファイルをすべて削除
	@echo "🗑️  シナリオクリーンアップ（実行）..."
	@uv run python scripts/cleanup_all.py --force

cleanup-full: install ## シナリオ関連ファイルとSandboxをすべて削除
	@echo "🗑️  完全クリーンアップ（実行）..."
	@uv run python scripts/cleanup_all.py --force --include-sandbox

test: install ## テストを実行
	@echo "🧪 Running tests..."
	@uv run pytest

carla-launch: install ## CARLAを起動 (PORT=<port> MAP=<map>で指定可能)
	@echo "🚗 Launching CARLA..."
	@if [ -n "$(PORT)" ] && [ -n "$(MAP)" ]; then \
		uv run python scripts/carla_launcher.py launch --port $(PORT) --map $(MAP); \
	elif [ -n "$(PORT)" ]; then \
		uv run python scripts/carla_launcher.py launch --port $(PORT); \
	elif [ -n "$(MAP)" ]; then \
		uv run python scripts/carla_launcher.py launch --map $(MAP); \
	else \
		uv run python scripts/carla_launcher.py launch; \
	fi

carla-stop: install ## CARLAを停止
	@echo "🛑 Stopping CARLA..."
	@uv run python scripts/carla_launcher.py stop

carla-status: install ## CARLA状態を確認
	@uv run python scripts/carla_launcher.py status

carla-config: install ## CARLA設定を更新 (PATH=<path> PORT=<port> MAP=<map>等)
	@echo "⚙️  Updating CARLA settings..."
	@CMD="uv run python scripts/carla_launcher.py config"; \
	[ -n "$(PATH)" ] && CMD="$$CMD --carla-path $(PATH)"; \
	[ -n "$(EXEC)" ] && CMD="$$CMD --executable $(EXEC)"; \
	[ -n "$(PORT)" ] && CMD="$$CMD --port $(PORT)"; \
	[ -n "$(MAP)" ] && CMD="$$CMD --map $(MAP)"; \
	[ -n "$(QUALITY)" ] && CMD="$$CMD --quality $(QUALITY)"; \
	[ -n "$(ARGS)" ] && CMD="$$CMD --additional-args \"$(ARGS)\""; \
	[ -n "$(TIMEOUT)" ] && CMD="$$CMD --timeout $(TIMEOUT)"; \
	eval $$CMD

status: ## システム状態を確認
	@echo "=== ATLAS System Status ==="
	@echo ""
	@echo "Flask Application (port 8000):"
	@lsof -ti:8000 >/dev/null 2>&1 && echo "  ✓ Running (PID: $$(lsof -ti:8000))" || echo "  ✗ Not running"
	@echo ""
	@echo "CARLA Server:"
	@uv run python scripts/carla_launcher.py status 2>/dev/null | grep -q "Running" && echo "  ✓ Running" || echo "  ✗ Not running"

batch-execute: install ## 複数の論理シナリオをバッチ実行 (UUIDS=<uuid1,uuid2,...>)
	@if [ -z "$(UUIDS)" ]; then \
		echo "Error: UUIDS is required. Usage: make batch-execute UUIDS=<uuid1,uuid2>"; \
		exit 1; \
	fi
	@uv run python scripts/batch_execute_scenarios.py --logical-uuids $(UUIDS)

batch-execute-dry: install ## バッチ実行のドライラン (UUIDS=<uuid1,uuid2,...>)
	@if [ -z "$(UUIDS)" ]; then \
		echo "Error: UUIDS is required. Usage: make batch-execute-dry UUIDS=<uuid1,uuid2>"; \
		exit 1; \
	fi
	@uv run python scripts/batch_execute_scenarios.py --logical-uuids $(UUIDS) --dry-run

batch-execute-high-risk: install ## 高リスクシナリオのみバッチ実行 (UUIDS=<uuid1,uuid2,...>)
	@if [ -z "$(UUIDS)" ]; then \
		echo "Error: UUIDS is required. Usage: make batch-execute-high-risk UUIDS=<uuid1,uuid2>"; \
		exit 1; \
	fi
	@uv run python scripts/batch_execute_scenarios.py --logical-uuids $(UUIDS) --min-criticality 4
