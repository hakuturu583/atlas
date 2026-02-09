# ATLAS クイックスタート

## 🚀 5分で始めるATLAS

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. システムテスト

```bash
uv run python test_system.py
```

成功すれば以下のような出力が表示されます：

```
✅ すべてのテストが成功しました！
```

### 3. FastAPIサーバーの起動

別のターミナルで：

```bash
./run_dev.sh
```

サーバーが起動したら、ブラウザで http://localhost:8000 を開きます。

### 4. UIの確認

ブラウザで以下が表示されます：

- **左ペイン**: ホーム画面、ナビゲーションボタン
- **右ペイン**: Claude Codeターミナル（WebSocket接続）

ナビゲーションボタンで画面を切り替えてみてください：
- ホーム
- シナリオ一覧
- 分析
- Rerun

### 5. Claude CodeプラグインでMCPツールを試す

Claude Codeで以下のコマンドを実行：

```python
# 画面をシナリオ一覧に切り替え
change_view(view="scenario_list")

# シナリオ一覧を取得
list_scenarios()

# シナリオ詳細を取得
get_scenario(scenario_id="test_scenario_001")

# 現在のUI状態を確認
get_current_view()
```

ブラウザの画面がリアルタイムで切り替わることを確認してください！

## 🎯 MCPツールの使い方

### change_view

UI画面を切り替えます。

```python
change_view(
    view="scenario_list",           # 必須: home, scenario_list, scenario_analysis, rerun_viewer
    scenario_id="scenario_001",     # オプション: シナリオID
    rerun_file="/path/to/file.rrd"  # オプション: RRDファイルパス
)
```

### list_scenarios

すべてのシナリオを一覧表示します。

```python
list_scenarios()
```

### get_scenario

特定のシナリオの詳細を取得します。

```python
get_scenario(scenario_id="test_scenario_001")
```

### create_scenario

新しいシナリオを作成します。

```python
create_scenario(
    id="my_scenario",
    name="My Test Scenario",
    description="テストシナリオ",
    carla_config={"map": "Town03"},
    vehicles=[],
    pedestrians=[],
    weather={}
)
```

### update_scenario

既存のシナリオを更新します。

```python
update_scenario(
    scenario_id="test_scenario_001",
    description="更新された説明"
)
```

### delete_scenario

シナリオを削除します。

```python
delete_scenario(scenario_id="test_scenario_001")
```

## 🔧 トラブルシューティング

### ポート8000が使用中

```bash
# 使用中のプロセスを確認
lsof -i :8000

# プロセスを終了
kill -9 <PID>
```

### WebSocket接続エラー

1. FastAPIサーバーが起動しているか確認
2. ブラウザのコンソールでエラーメッセージを確認
3. サーバーを再起動

```bash
# Ctrl+C でサーバーを停止
./run_dev.sh  # 再起動
```

### MCPサーバーが動作しない

```bash
# 手動でMCPサーバーをテスト
./run_mcp_server.sh

# エラーメッセージを確認
```

### シナリオが表示されない

```bash
# データディレクトリを確認
ls -la data/scenarios/

# サンプルシナリオがあるか確認
cat data/scenarios/test_scenario_001.json
```

## 📚 次に読むべきドキュメント

- [ARCHITECTURE.md](./ARCHITECTURE.md) - システムアーキテクチャの詳細
- [README.md](./README.md) - プロジェクト概要
- `.claude/atlas-plugin/` - プラグインのコマンドとスキル

## 💡 ヒント

### デバッグモード

FastAPIのログを詳細に表示：

```bash
FASTAPI_LOG_LEVEL=debug ./run_dev.sh
```

### WebSocket通信の確認

ブラウザの開発者ツール → Networkタブ → WS でWebSocketメッセージを確認できます。

### MCPツールの一覧

Claude Codeで以下のコマンドを実行：

```python
# 利用可能なツールを確認
list_tools()
```

## 🎉 完了！

これでATLASの基本的な使い方がわかりました。

次は実際にシナリオを作成して、CARLAシミュレーションと連携してみましょう！
