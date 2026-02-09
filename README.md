# ATLAS

**A**nalytic **T**ransparent **L**Anguage-driven Scenario generator for CARLA

CARLAのシナリオ生成・管理ツール

## 🚀 特徴

- **Claude Code統合**: MCPサーバー経由でClaude CodeからUI制御
- **2ペインUI**: 左側にアプリUI、右側にClaude Codeターミナル
- **リアルタイム同期**: WebSocketによる即座のUI状態更新
- **htmx + FastAPI**: モダンなハイパーメディア駆動アーキテクチャ
- **Python完結**: フロントエンド・バックエンドをPythonで統一
- **uv管理**: 高速な依存関係管理とパッケージインストール
- **rerun.io統合**: 3D可視化ビューア内蔵

## 📋 必要要件

- Python 3.10以上
- [uv](https://github.com/astral-sh/uv) - Python パッケージマネージャー

## 🔧 セットアップ

### uvのインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 依存関係のインストール

```bash
uv sync
```

## 🏃 起動方法

### 1. FastAPIサーバーの起動

#### 通常起動

```bash
./run.sh
```

#### 開発モード（自動リロード有効）

```bash
./run_dev.sh
```

アプリケーションは http://localhost:8000 で起動します。

### 2. Claude Codeプラグインの有効化

Claude Codeで `.claude/atlas-plugin` を認識させます。

```bash
# Claude Codeを起動
claude-code

# プラグインが自動的に読み込まれます
```

### 3. MCPサーバーの動作確認

Claude Code内でMCPツールを使用してUIを制御できます：

```
# 画面をシナリオ一覧に切り替え
change_view(view="scenario_list")

# rerunビューアを表示
change_view(view="rerun_viewer")

# 現在の画面状態を確認
get_current_view()
```

## 🛑 シャットダウン

### すべてのシステムを停止

```bash
# 基本シャットダウン（Flask + MCP + Sandbox）
./shutdown.sh

# または Makeを使用
make shutdown
```

### 個別コンポーネントの停止

```bash
# Flaskアプリケーションのみ
./shutdown.sh --flask-only

# Sandboxコンテナのみ
./shutdown.sh --sandbox-only

# MCPサーバーのみ
./shutdown.sh --mcp-only
```

### 完全クリーンアップ

```bash
# Dockerイメージも含めてすべて削除
./shutdown.sh --clean-docker -f

# または Makeを使用
make shutdown-all
```

### システム状態の確認

```bash
make status
```

## 💡 使用例

### Claude CodeからUI操作

```
> change_view(view="scenario_list")
画面を scenario_list に切り替えました。

> list_scenarios()
シナリオリスト (3件):
- scenario_001: 市街地走行テスト
- scenario_002: 高速道路合流
- scenario_003: 交差点右折

> get_scenario(scenario_id="scenario_001")
シナリオ詳細: {...}
```

### スラッシュコマンド

```bash
# 画面切り替え
/view scenario_list

# シナリオ管理
/scenario-manager
```

## 🎯 Claude Code スキル

ATLASプロジェクトには10個の専用スキルが用意されています。

### 主要スキル

| スキル名 | トリガーワード | 機能 |
|---------|---------------|------|
| **scenario-writer** | "シナリオ生成", "create scenario" | 自然言語からPythonシナリオを自動生成（PEGASUS統合） |
| **scenario-manager** | "シナリオ一覧", "list scenarios" | シナリオのCRUD操作 |
| **pegasus-analyzer** | "pegasus", "シナリオ分析" | PEGASUS 6 Layer分析 |
| **carla-launcher** | "start CARLA", "carla起動" | CARLAシミュレーター管理 |
| **cleanup** | "cleanup", "削除" | シナリオファイル一括削除 |

その他のスキル: `carla-python-scenario`, `scenario-breakdown`, `rerun-carla-sdk`, `fiftyone-integration`, `test-simple`

**詳細**: `.claude/CLAUDE.md` の「スキル」セクションを参照してください。

## 🐳 Sandbox管理

### 自動起動（推奨）⭐

**完全自動でSandboxを起動し、成功を保証します**

```bash
# 最もシンプル（すべて自動）
uv run python scripts/auto_launch_sandbox.py

# または Makeコマンド
make sandbox-auto
```

**自動起動の特徴:**
- ✅ UUIDを自動生成
- ✅ CARLA接続確認
- ✅ ワークスペース自動作成
- ✅ コンテナ起動待機
- ✅ 起動成功を検証

### PythonからSandboxを起動

PythonスクリプトからUUIDを生成してSandboxを起動できます。

#### 方法1: 自動起動スクリプト（推奨）

```bash
# すべて自動
uv run python scripts/auto_launch_sandbox.py

# UUID指定
uv run python scripts/auto_launch_sandbox.py --uuid my-scenario-001

# 詳細ログ表示
uv run python scripts/auto_launch_sandbox.py --verbose
```

#### 方法2: CLIツールで起動

```bash
# 新しいSandboxを起動（UUID自動生成）
uv run python scripts/launch_sandbox.py launch

# 既存のSandboxを再起動
uv run python scripts/launch_sandbox.py launch --uuid 550e8400-e29b-41d4-a716-446655440000

# Sandbox一覧を表示
uv run python scripts/launch_sandbox.py list

# Sandbox状態を確認
uv run python scripts/launch_sandbox.py status --uuid 550e8400-e29b-41d4-a716-446655440000

# Sandboxを停止
uv run python scripts/launch_sandbox.py stop --uuid 550e8400-e29b-41d4-a716-446655440000
```

#### Makeコマンドで起動

```bash
# 新しいSandboxを起動
make sandbox-launch

# 既存のSandboxを起動
make sandbox-launch UUID=550e8400-e29b-41d4-a716-446655440000

# Sandbox一覧を表示
make sandbox-list

# Sandbox状態を確認
make sandbox-status UUID=550e8400-e29b-41d4-a716-446655440000

# Sandboxを停止
make sandbox-stop UUID=550e8400-e29b-41d4-a716-446655440000

# すべてのSandboxを停止
make sandbox-stop-all
```

#### Pythonコードから使用

**推奨: SandboxLauncher（起動を保証）**

```python
from app.services import sandbox_launcher

# シンプルな起動
result = sandbox_launcher.launch_and_wait()

if result.success:
    print(f"✅ Success! UUID: {result.uuid}")
    print(f"   Container: {result.container_name}")
    print(f"   Workspace: {result.workspace_path}")
else:
    print(f"❌ Failed: {result.error_message}")
```

**低レベルAPI: SandboxManager**

```python
from app.services import sandbox_manager

# 新しいSandboxを起動
uuid, result = sandbox_manager.launch_sandbox()
print(f"Launched sandbox: {uuid}")

# Sandbox一覧を取得
sandboxes = sandbox_manager.list_sandboxes()
for sb in sandboxes:
    print(f"{sb.uuid}: {sb.status}")

# Sandboxを停止
result = sandbox_manager.stop_sandbox(uuid)
```

詳細は [scripts/README.md](scripts/README.md) を参照してください。

## 📁 プロジェクト構造

```
atlas/
├── app/
│   ├── main.py                    # FastAPIメインアプリケーション
│   ├── mcp/                       # MCPサーバー
│   │   └── server.py              # MCP server実装
│   ├── models/                    # データモデル
│   │   ├── ui_state.py            # UI状態モデル
│   │   └── scenario.py            # シナリオモデル
│   ├── services/                  # ビジネスロジック
│   │   ├── ui_state_manager.py    # UI状態管理
│   │   └── scenario_manager.py    # シナリオ管理
│   ├── routers/                   # APIルーター
│   │   ├── views.py               # 画面レンダリング
│   │   ├── api.py                 # REST API
│   │   ├── websocket.py           # WebSocket通信
│   │   └── mcp_bridge.py          # MCP統合ブリッジ
│   ├── templates/                 # Jinja2テンプレート
│   │   ├── app.html               # 2ペインメインUI
│   │   └── views/                 # 各画面テンプレート
│   │       ├── home.html
│   │       ├── scenario_list.html
│   │       ├── scenario_analysis.html
│   │       └── rerun_viewer.html
│   └── static/                    # 静的ファイル
│       ├── css/
│       └── js/
├── .claude/
│   └── atlas-plugin/              # Claude Codeプラグイン
│       ├── plugin.json            # プラグイン設定
│       ├── commands/              # スラッシュコマンド
│       └── skills/                # スキル
├── data/                          # データストレージ
│   ├── scenarios/                 # シナリオファイル
│   └── rerun/                     # RRDファイル
├── sandbox/                       # Dockerサンドボックス環境
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── src/                       # C++シナリオコード
│   ├── output/                    # .rrdファイル出力
│   └── build/                     # ビルド成果物
├── pyproject.toml                 # プロジェクト設定
├── Makefile                       # ビルド・実行タスク
├── run_mcp_server.sh              # MCPサーバー起動スクリプト
├── run.sh                         # FastAPI起動スクリプト
├── run_dev.sh                     # 開発用起動スクリプト
├── shutdown.sh                    # システムシャットダウンスクリプト
├── ARCHITECTURE.md                # アーキテクチャドキュメント
└── README.md
```

詳細なアーキテクチャについては、[ARCHITECTURE.md](./ARCHITECTURE.md) を参照してください。

## 🛠️ 技術スタック

### バックエンド
- **FastAPI**: 高速なWebフレームワーク
- **MCP Server**: Model Context Protocol実装
- **WebSocket**: リアルタイム通信
- **Pydantic**: データバリデーション

### フロントエンド
- **htmx**: ハイパーメディア駆動UI
- **Tailwind CSS**: ユーティリティファーストCSS
- **xterm.js**: ターミナルエミュレーター
- **Jinja2**: テンプレートエンジン

### 統合
- **Claude Code**: AI支援開発環境
- **rerun.io**: 3D可視化ツール
- **WebSocket**: 双方向通信

### その他
- **uv**: 高速パッケージマネージャー
- **CARLA**: 自動運転シミュレーター（連携予定）

## 📝 実装済み機能

- ✅ 2ペインUI（左：アプリ、右：Claude Codeターミナル）
- ✅ MCPサーバー経由のUI制御
- ✅ WebSocketによるリアルタイム状態同期
- ✅ シナリオ管理（CRUD操作）
- ✅ rerun.io統合（.rrdファイル可視化）
- ✅ Claude Codeプラグイン
- ✅ htmxによる動的UI更新

## 📝 次のステップ

- [ ] シナリオエディタの高度化（ドラッグ&ドロップ）
- [ ] CARLAシミュレーション実行連携
- [ ] リアルタイム分析ダッシュボード
- [ ] データベース統合（SQLModel + PostgreSQL）
- [ ] ユーザー認証・権限管理
- [ ] CI/CD パイプライン

## 📄 ライセンス

TBD
