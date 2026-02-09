---
name: fiftyone-integration
description: This skill should be used when the user asks to "register to FiftyOne", "create FiftyOne dataset", "compute video embeddings", "add to FiftyOne", "FiftyOneに登録", "embedding計算". Automates FiftyOne dataset registration and video embedding computation for CARLA scenarios.
---

# FiftyOne Integration Skill

**役割**: CARLAシナリオの実行結果（動画、メタデータ）をFiftyOneデータセットに登録し、NVIDIA NIM Cosmos Embed1を使った動画embeddingのバッチ計算を自動化する。

## トリガーワード

以下のキーワードが含まれる場合、このスキルを使用してください：
- "fiftyone"
- "データセット登録"
- "embedding計算"
- "バッチ処理"
- "動画分析"
- "シナリオ可視化"

## 主要機能

### 1. **バッチ登録（embedding計算あり）**

すべての動画を一度に処理し、embeddingも計算します。

**コマンド**:
```bash
uv run python scripts/fiftyone_integration.py batch-add --all-videos
```

**処理フロー**:
1. `data/videos/`内のすべての`.mp4`ファイルを検出
2. NVIDIA NIM Cosmos Embed1コンテナを起動
3. 各動画からembeddingを計算（/v1/embeddings API）
4. 結果を`data/embeddings/`に保存（JSON + NumPy）
5. FiftyOneデータセットに登録
6. NIMコンテナをシャットダウン（VRAM解放）

**オプション**:
- `--no-embeddings`: embeddingを計算せず、メタデータのみ登録（高速）
- `--nim-port 8001`: NIMコンテナのポート番号を指定
- `--dataset-name carla-scenarios`: データセット名を指定

### 2. **個別シナリオの登録**

特定のシナリオのみを登録します。

**コマンド**:
```bash
uv run python scripts/fiftyone_integration.py batch-add \
  --logical-uuid <論理シナリオUUID> \
  --parameter-uuid <パラメータUUID>
```

### 3. **従来の登録（embedding計算なし）**

embeddingを計算せず、メタデータと動画のみを登録します。

**コマンド**:
```bash
uv run python scripts/fiftyone_integration.py add \
  --logical-uuid <論理シナリオUUID> \
  --parameter-uuid <パラメータUUID>
```

### 4. **FiftyOne GUIの起動**

登録済みデータセットをブラウザで可視化・分析します。

**コマンド**:
```bash
uv run python scripts/fiftyone_integration.py launch --dataset-name carla-scenarios
```

GUIは `http://localhost:5151` で起動します。

### 5. **データセット一覧**

すべてのFiftyOneデータセットを表示します。

**コマンド**:
```bash
uv run python scripts/fiftyone_integration.py list
```

### 6. **データセット削除**

指定したデータセットを削除します。

**コマンド**:
```bash
uv run python scripts/fiftyone_integration.py clear --dataset-name carla-scenarios
```

## FiftyOneデータセットのフィールド

登録されるデータには以下のフィールドが含まれます：

| フィールド | 説明 | 型 |
|-----------|------|-----|
| `filepath` | 動画ファイルのパス | str |
| `logical_uuid` | 論理シナリオUUID | str |
| `parameter_uuid` | パラメータUUID | str |
| `initial_speed` | 初期速度（km/h） | float |
| `distance_to_light` | 信号機までの距離（m） | float |
| `duration` | シナリオ実行時間（秒） | float |
| `carla_map` | CARLAマップ名 | str |
| `vehicle_type` | 車両タイプ | str |
| `embedding` | 動画埋め込みベクトル | List[float] |
| `embedding_dim` | ベクトル次元数 | int |

## Embeddingファイルの保存場所

- **JSON形式**: `data/embeddings/{logical_uuid}_{parameter_uuid}.json`
- **NumPy形式**: `data/embeddings/{logical_uuid}_{parameter_uuid}.npy`

JSON形式には以下が含まれます：
```json
{
  "data": [
    {
      "embedding": [0.123, -0.456, ...],
      "index": 0,
      "object": "embedding"
    }
  ],
  "model": "nvidia/cosmos-embed1",
  "object": "list",
  "usage": {
    "prompt_tokens": 0,
    "total_tokens": 0
  }
}
```

## 使用例

### 例1: すべてのシナリオをembedding付きで登録

```bash
uv run python scripts/fiftyone_integration.py batch-add --all-videos
```

### 例2: embeddingなしで高速登録

```bash
uv run python scripts/fiftyone_integration.py batch-add --all-videos --no-embeddings
```

### 例3: 特定のシナリオのみ登録

```bash
uv run python scripts/fiftyone_integration.py batch-add \
  --logical-uuid 9eab1c6c-728b-4a3a-9588-5f64a1daad9c \
  --parameter-uuid 95615f23-382f-473f-93e9-136b746854af
```

### 例4: 登録後にGUIで確認

```bash
# データセットに登録
uv run python scripts/fiftyone_integration.py batch-add --all-videos

# GUIを起動
uv run python scripts/fiftyone_integration.py launch

# ブラウザで http://localhost:5151 を開く
```

## ワークフロー統合

### シナリオ実行→FiftyOne登録の完全フロー

1. **シナリオ生成・実行**
   ```bash
   # scenario-writerスキルを使ってシナリオを生成
   # → data/videos/{logical_uuid}_{parameter_uuid}.mp4 が生成される
   ```

2. **FiftyOneに登録（embedding計算）**
   ```bash
   uv run python scripts/fiftyone_integration.py batch-add --all-videos
   ```

3. **可視化・分析**
   ```bash
   uv run python scripts/fiftyone_integration.py launch
   ```

## NVIDIA NIM Cosmos Embed1について

### 必要なリソース

- **GPU**: NVIDIA GPU（VRAM 8GB以上推奨）
- **Dockerイメージ**: `nvcr.io/nim/nvidia/cosmos-embed1:1.0.0`
- **ポート**: デフォルト 8001（`--nim-port`で変更可能）

### VRAMの管理

- NIMコンテナはバッチ処理の開始時に起動
- すべての動画処理が完了すると自動的にシャットダウン
- **VRAM解放**: コンテナ停止時にGPUメモリが解放される

### Embedding次元数

| モデル | 解像度 | 出力次元 |
|--------|--------|---------|
| Cosmos-Embed1-224p | 224x224 | 256 |
| Cosmos-Embed1-336p | 336x336 | 768 |
| Cosmos-Embed1-448p | 448x448 | 768 |

デフォルトでは `nvidia/cosmos-embed1` が使用されます。

## トラブルシューティング

### NIMコンテナが起動しない

```bash
# Dockerイメージを手動でpull
docker pull nvcr.io/nim/nvidia/cosmos-embed1:1.0.0

# GPUが認識されているか確認
nvidia-smi
```

### VRAMが不足する

```bash
# embeddingなしで登録（VRAMを使用しない）
uv run python scripts/fiftyone_integration.py batch-add --all-videos --no-embeddings
```

### 既存のNIMコンテナが残っている

```bash
# 手動でコンテナを停止
docker ps | grep cosmos-embed1
docker stop <container_id>
```

### FiftyOne GUIが起動しない

```bash
# ポートが使用されているか確認
lsof -i:5151

# 別のポートで起動
uv run python scripts/fiftyone_integration.py launch --port 5152
```

## 重要な注意事項

1. **バッチ処理は時間がかかる**
   - 動画1本あたり数十秒〜数分
   - 複数動画がある場合は合計時間を考慮

2. **NIMコンテナは自動的にシャットダウンされる**
   - 処理完了後にVRAMが解放される
   - 手動で停止する必要はない

3. **Embeddingは再計算しない**
   - 既にFiftyOneに登録済みのシナリオは再登録されない
   - 強制的に再登録する場合は、先にデータセットをクリア

4. **動画ファイルの命名規則**
   - `{logical_uuid}_{parameter_uuid}.mp4` の形式であること
   - UUIDは標準形式（xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx）

## 関連スキル

- **scenario-writer**: シナリオ生成・実行
- **scenario-manager**: シナリオ管理

## 参考リンク

- [FiftyOne Documentation](https://docs.voxel51.com/)
- [NVIDIA NIM Cosmos Embed1](https://docs.nvidia.com/nim/cosmos-embed1/)
- [CARLA Documentation](https://carla.readthedocs.io/)
