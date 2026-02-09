---
name: cleanup
description: This skill should be used when the user asks to "clean up scenarios", "delete all scenarios", "remove scenario files", "clear scenario data", "全削除", "シナリオクリーンアップ". Removes all scenario-related files including JSON, videos, RRD, embeddings, logs, and FiftyOne datasets.
---

# Cleanup Skill

**役割**: シナリオ関連のすべてのファイルとログを安全に削除する。

## トリガーワード

以下のキーワードが含まれる場合、このスキルを使用してください：
- "クリーンアップ"
- "cleanup"
- "削除"
- "シナリオ削除"
- "ログ削除"
- "全部削除"
- "リセット"

## 削除対象

### 1. シナリオファイル
- **抽象シナリオ**: `data/scenarios/abstract_*.json`
- **論理シナリオ**: `data/scenarios/logical_*.json`
- **パラメータ**: `data/scenarios/params_*.json`, `logical_*_parameters.json`
- **実行トレース**: `data/scenarios/execution_*.json`

### 2. Pythonスクリプト
- **シナリオスクリプト**: `scenarios/*.py`
- **注**: `examples/`以下は除外

### 3. 動画ファイル
- **MP4**: `data/videos/*.mp4`

### 4. RRDファイル
- **Rerunログ**: `data/rerun/*.rrd`

### 5. Embeddingファイル
- **JSON**: `data/embeddings/*.json`
- **NumPy**: `data/embeddings/*.npy`

### 6. ログファイル
- **すべてのログ**: `logs/*.log`

### 7. FiftyOneデータセット
- **デフォルト**: `carla-scenarios`

### 8. Sandboxワークスペース（オプション）
- **ワークスペース**: `sandbox/workspace/<uuid>/`

## 使用方法

### 基本的な使い方

#### ドライラン（確認のみ）

```bash
uv run python scripts/cleanup_all.py
```

削除対象のファイルを表示しますが、実際には削除しません。

#### 実際に削除

```bash
uv run python scripts/cleanup_all.py --force
```

すべてのファイルとFiftyOneデータセットを削除します。

### オプション

#### Sandboxワークスペースも削除

```bash
uv run python scripts/cleanup_all.py --force --include-sandbox
```

シナリオファイルに加えて、Sandboxのワークスペース（ビルド成果物、出力ファイル）も削除します。

#### FiftyOneデータセットを残す

```bash
uv run python scripts/cleanup_all.py --force --no-fiftyone
```

FiftyOneデータセットを削除せずに、ファイルのみを削除します。

#### カスタムデータセット名

```bash
uv run python scripts/cleanup_all.py --force --fiftyone-dataset my-dataset
```

デフォルト以外のFiftyOneデータセットを削除します。

## コマンド一覧

| コマンド | 説明 |
|---------|------|
| `cleanup_all.py` | ドライラン（確認のみ）|
| `cleanup_all.py --force` | すべて削除 |
| `cleanup_all.py --force --include-sandbox` | Sandbox含めてすべて削除 |
| `cleanup_all.py --force --no-fiftyone` | FiftyOne以外を削除 |

## 出力例

### ドライラン

```
============================================================
🔍 完全クリーンアップ（ドライラン）
============================================================

ファイルを検索中...

=== 削除対象ファイル ===

【scenarios】
  - data/scenarios/abstract_93c709df-06fb-42e0-80c0-154112752932.json (1.5KB)
  - data/scenarios/logical_8908f3a0-548b-4bc0-91d9-235afe5b69b1.json (3.1KB)
  小計: 4.6KB

【python】
  - scenarios/9eab1c6c-728b-4a3a-9588-5f64a1daad9c.py (11.6KB)
  小計: 11.6KB

【videos】
  - data/videos/9eab1c6c-728b-4a3a-9588-5f64a1daad9c_95615f23-382f-473f-93e9-136b746854af.mp4 (21.3MB)
  小計: 21.3MB

【embeddings】
  - data/embeddings/9eab1c6c-728b-4a3a-9588-5f64a1daad9c_95615f23-382f-473f-93e9-136b746854af.json (2.5KB)
  - data/embeddings/9eab1c6c-728b-4a3a-9588-5f64a1daad9c_95615f23-382f-473f-93e9-136b746854af.npy (1.0KB)
  小計: 3.5KB

【logs】
  - logs/fiftyone.log (15.2KB)
  小計: 15.2KB

【FiftyOne Dataset】
  - carla-scenarios
  （削除予定）

=== 合計: 8ファイル, 21.3MB ===

ℹ️  ドライランモード: ファイルは削除されません
   実際に削除するには --force オプションを使用してください

💡 実際に削除するには:
   uv run python scripts/cleanup_all.py --force
```

### 実行モード

```
============================================================
🗑️  完全クリーンアップ（実行モード）
============================================================

ファイルを検索中...

=== 削除対象ファイル ===

【scenarios】
  - data/scenarios/abstract_93c709df-06fb-42e0-80c0-154112752932.json (1.5KB)
  小計: 1.5KB

...

✓ 削除: data/scenarios/abstract_93c709df-06fb-42e0-80c0-154112752932.json
✓ 削除: scenarios/9eab1c6c-728b-4a3a-9588-5f64a1daad9c.py
✓ 削除: data/videos/9eab1c6c-728b-4a3a-9588-5f64a1daad9c_95615f23-382f-473f-93e9-136b746854af.mp4
...

✓ 8ファイルを削除しました

【FiftyOne Dataset】
  - carla-scenarios
✓ FiftyOneデータセット削除: carla-scenarios
```

## Makefileターゲット

便利なMakeコマンドも用意されています：

```bash
# ドライラン
make cleanup-dry

# すべて削除
make cleanup

# Sandbox含めてすべて削除
make cleanup-full
```

## 安全機能

1. **ドライランがデフォルト**
   - `--force`なしでは何も削除されない
   - 削除前に必ず確認できる

2. **削除対象の表示**
   - すべてのファイルとサイズを表示
   - カテゴリごとに整理

3. **examples/除外**
   - サンプルスクリプトは削除されない

4. **FiftyOneオプション**
   - `--no-fiftyone`でデータセットを保護

## 使用例

### 例1: 削除前に確認

```bash
# 1. まずドライランで確認
uv run python scripts/cleanup_all.py

# 2. 問題なければ実行
uv run python scripts/cleanup_all.py --force
```

### 例2: Sandboxも含めて完全削除

```bash
# Sandboxのビルド成果物も削除
uv run python scripts/cleanup_all.py --force --include-sandbox
```

### 例3: FiftyOneデータセットのみ保持

```bash
# ファイルは削除するがFiftyOneは残す
uv run python scripts/cleanup_all.py --force --no-fiftyone
```

## Claude Codeでの使用

Claude Codeで以下のように指示すると、このスキルが自動的に起動します：

```
ユーザー: "シナリオを全部削除して"
ユーザー: "クリーンアップしてください"
ユーザー: "ログとシナリオをリセット"
```

Claude Codeは自動的に以下を実行します：
1. ドライランで削除対象を確認
2. ユーザーに確認
3. `--force`で実際に削除

## 注意事項

⚠️ **削除したファイルは復元できません**

- 重要なシナリオがある場合は、事前にバックアップを取ってください
- ドライランで必ず内容を確認してください
- `examples/`以下のファイルは削除されません

## 関連コマンド

- **個別削除**: `scripts/cleanup_scenarios.py` - 特定のシナリオのみ削除
- **Sandbox削除**: `cd sandbox && make shutdown-all` - Sandboxコンテナを停止
- **FiftyOne削除**: `uv run python scripts/fiftyone_integration.py clear` - FiftyOneのみ削除

## トラブルシューティング

### FiftyOneが削除できない

```bash
# FiftyOneが起動中の場合は停止
make fiftyone-stop

# 再度クリーンアップ
uv run python scripts/cleanup_all.py --force
```

### Sandboxワークスペースが削除できない

```bash
# Sandboxコンテナを停止
cd sandbox && make shutdown-all

# 再度クリーンアップ（Sandbox含む）
uv run python scripts/cleanup_all.py --force --include-sandbox
```

### 権限エラー

```bash
# ファイルの権限を確認
ls -la data/scenarios/
ls -la data/videos/

# 必要に応じて権限を変更
chmod -R u+w data/scenarios/ data/videos/
```
