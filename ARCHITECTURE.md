# ATLAS アーキテクチャ

## 概要

ATLASは、Claude CodeをバックエンドとしてMCPサーバー経由でUI状態を制御する先進的なアーキテクチャを採用しています。

## システム構成

```
┌─────────────────────────────────────────────────────┐
│                   ブラウザ UI                         │
├──────────────────────┬──────────────────────────────┤
│  左ペイン             │  右ペイン                     │
│  - rerun.io iframe   │  - Claude Code ターミナル     │
│  - シナリオ選択       │    (WebSocket接続)           │
│  - シナリオ分析       │                              │
└──────────┬───────────┴──────────────────┬───────────┘
           │ htmx / WebSocket              │ WebSocket
           ↓                               ↓
┌──────────────────────┐         ┌────────────────────┐
│  FastAPI Server      │         │                    │
│  ┌─────────────────┐ │         │  Claude Code       │
│  │ UI Endpoints    │ │◄────────┤  + MCP Server      │
│  │ API Endpoints   │ │   MCP   │    (stdio)         │
│  │ WebSocket       │ │         │                    │
│  │ MCP Bridge      │ │         │  Tools:            │
│  └─────────────────┘ │         │  - change_view     │
│                      │         │  - list_scenarios  │
│  ┌─────────────────┐ │         │  - get_scenario    │
│  │ Services        │ │         │  - create_scenario │
│  │ - UI State Mgr  │ │         │  - update_scenario │
│  │ - Scenario Mgr  │ │         │  - delete_scenario │
│  └─────────────────┘ │         │                    │
└──────────────────────┘         └────────────────────┘
```

## コンポーネント詳細

### 1. MCPサーバー (`app/mcp/server.py`)

Claude Codeから利用可能なツールを提供します。

**提供ツール:**
- `change_view`: UI画面を切り替え
- `get_current_view`: 現在のUI状態を取得
- `list_scenarios`: シナリオ一覧を取得
- `get_scenario`: シナリオ詳細を取得
- `create_scenario`: 新規シナリオ作成
- `update_scenario`: シナリオ更新
- `delete_scenario`: シナリオ削除

### 2. UI状態管理 (`app/services/ui_state_manager.py`)

アプリケーション全体のUI状態を管理し、購読者に変更を通知します。

**状態フィールド:**
- `current_view`: 現在表示中の画面
- `selected_scenario_id`: 選択中のシナリオID
- `rerun_file_path`: 表示中のrerunファイルパス
- `sidebar_expanded`: サイドバーの展開状態
- `terminal_visible`: ターミナルの表示状態

### 3. シナリオ管理 (`app/services/scenario_manager.py`)

CARLAシナリオのCRUD操作を管理します。

### 4. WebSocket通信

**ターミナル WebSocket (`/ws/terminal`):**
- Claude Codeターミナルとの双方向通信
- キー入力とコマンド出力をリアルタイムで送受信

**UI状態 WebSocket (`/ws/ui-state`):**
- UI状態の変更をリアルタイムで通知
- MCPサーバーからの状態変更を即座に反映

### 5. MCP Bridge (`app/routers/mcp_bridge.py`)

MCPサーバーとFastAPIを接続するブリッジ。

**エンドポイント:**
- `POST /mcp/change-view`: 画面遷移
- `GET /mcp/state`: 現在の状態取得
- `POST /mcp/update-state`: 状態の部分更新

## データフロー

### 画面遷移の例

1. Claude Codeでコマンド実行:
   ```
   use mcp tool: change_view(view="scenario_list")
   ```

2. MCPサーバーがFastAPIに通知:
   ```
   POST http://localhost:8000/mcp/change-view?view=scenario_list
   ```

3. UI State Managerが状態を更新し、購読者に通知

4. WebSocketでブラウザに通知:
   ```json
   {
     "current_view": "scenario_list",
     "selected_scenario_id": null,
     ...
   }
   ```

5. ブラウザが新しい画面をロード:
   ```javascript
   fetch('/views/scenario_list')
   ```

## ディレクトリ構造

```
atlas/
├── app/
│   ├── main.py                    # FastAPIメインアプリケーション
│   ├── mcp/                       # MCPサーバー
│   │   └── server.py
│   ├── models/                    # データモデル
│   │   ├── ui_state.py
│   │   └── scenario.py
│   ├── services/                  # ビジネスロジック
│   │   ├── ui_state_manager.py
│   │   └── scenario_manager.py
│   ├── routers/                   # APIルーター
│   │   ├── views.py              # 画面レンダリング
│   │   ├── api.py                # REST API
│   │   ├── websocket.py          # WebSocket通信
│   │   └── mcp_bridge.py         # MCP統合
│   ├── templates/                 # Jinja2テンプレート
│   │   ├── app.html              # 2ペインUI
│   │   └── views/                # 各画面のテンプレート
│   └── static/                    # 静的ファイル
├── .claude/
│   └── atlas-plugin/              # Claude Codeプラグイン
│       ├── plugin.json            # プラグイン設定
│       ├── commands/              # スラッシュコマンド
│       └── skills/                # スキル
├── data/                          # データストレージ
│   ├── scenarios/                 # シナリオファイル
│   └── rerun/                     # RRDファイル
├── run_mcp_server.sh              # MCPサーバー起動スクリプト
├── run_dev.sh                     # 開発サーバー起動
└── pyproject.toml                 # プロジェクト設定
```

## セキュリティ

- MCPサーバーはstdio経由でのみ通信（外部からのアクセス不可）
- FastAPIはローカルホスト上で動作
- WebSocketは同一オリジンポリシーで保護

## 拡張性

### 新しいビューの追加

1. `app/models/ui_state.py`の`ViewType`に追加
2. `app/templates/views/`に新しいテンプレート作成
3. `app/routers/views.py`にルート追加

### 新しいMCPツールの追加

1. `app/mcp/server.py`の`list_tools()`に追加
2. `call_tool()`にハンドラー実装
3. Claude Codeプラグインのスキル/コマンドを追加

## トラブルシューティング

### MCPサーバーが起動しない

```bash
# 手動でMCPサーバーをテスト
./run_mcp_server.sh
```

### WebSocket接続が失敗する

1. FastAPIサーバーが起動していることを確認
2. ブラウザのコンソールでエラーを確認
3. ポート8000が使用可能か確認

### UI状態が同期しない

1. WebSocket接続が確立されているか確認
2. ブラウザのNetworkタブでWebSocketメッセージを確認
3. FastAPIのログを確認
