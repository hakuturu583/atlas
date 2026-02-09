# Claude Code → FiftyOne API Integration

Claude Code（右側）からFiftyOne UI（左側）を操作するためのAPI統合ドキュメント

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                Claude Code (右ペイン)                        │
│  ユーザープロンプト → curl/httpx → FastAPI                   │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP Request
                             ▼
┌─────────────────────────────────────────────────────────────┐
│             FastAPI (localhost:8000)                         │
│  /api/fiftyone/* エンドポイント                               │
│  ↓                                                           │
│  FiftyOneManager (Python API)                               │
└────────────────────────────┬────────────────────────────────┘
                             │ FiftyOne Python API
                             ▼
┌─────────────────────────────────────────────────────────────┐
│          FiftyOne (localhost:5151 - 左ペイン)                │
│  データセットが自動的に更新される                              │
└─────────────────────────────────────────────────────────────┘
```

## 利用可能なAPI

### 1. データセット統計情報

```bash
GET /api/fiftyone/stats
```

**レスポンス例**:
```json
{
  "success": true,
  "stats": {
    "name": "carla-scenarios",
    "sample_count": 4,
    "fields": ["id", "filepath", "tags", "logical_uuid", ...],
    "tags": [],
    "map_distribution": {
      "Town10HD_Opt": 4
    }
  }
}
```

### 2. サンプル一覧

```bash
GET /api/fiftyone/samples?limit=10
```

**レスポンス例**:
```json
{
  "success": true,
  "samples": [
    {
      "id": "...",
      "filepath": "data/videos/....mp4",
      "logical_uuid": "9eab1c6c-...",
      "parameter_uuid": "95615f23-...",
      "carla_map": "Town10HD_Opt",
      "initial_speed": 32.9,
      "tags": []
    }
  ],
  "count": 4
}
```

## Claude Codeからの使い方

### 方法1: curlコマンド

```bash
# 統計情報を取得
curl http://localhost:8000/api/fiftyone/stats | jq

# サンプル一覧を取得
curl http://localhost:8000/api/fiftyone/samples?limit=5 | jq
```

### 方法2: ヘルパースクリプト

```bash
# 統計情報
./scripts/api_helpers/fiftyone_api.sh stats

# サンプル一覧
./scripts/api_helpers/fiftyone_api.sh list 5
```

### 方法3: Python (httpx)

```python
import httpx

# 統計情報を取得
response = httpx.get("http://localhost:8000/api/fiftyone/stats")
stats = response.json()
print(f"サンプル数: {stats['stats']['sample_count']}")

# サンプル一覧を取得
response = httpx.get("http://localhost:8000/api/fiftyone/samples", params={"limit": 10})
samples = response.json()
for sample in samples["samples"]:
    print(f"- {sample['filepath']}: {sample['carla_map']}")
```

## 使用例

### 例1: データセット情報を確認

```bash
# Claude Codeターミナルで実行
curl http://localhost:8000/api/fiftyone/stats | jq '.stats.sample_count'
# → 4

# 出力: データセットには4つのサンプルがあります
```

### 例2: 特定のマップのサンプル数を確認

```bash
curl http://localhost:8000/api/fiftyone/stats | \
  jq '.stats.map_distribution["Town10HD_Opt"]'
# → 4
```

### 例3: 最新5件のサンプルを表示

```bash
./scripts/api_helpers/fiftyone_api.sh list 5
```

## 今後追加予定の機能

以下の機能を追加することで、より高度なUI制御が可能になります：

### フィルタリング API

```bash
POST /api/fiftyone/filter
Content-Type: application/json

{
  "filters": {
    "carla_map": "Town10HD_Opt",
    "initial_speed__gte": 30
  }
}
```

### ソート API

```bash
POST /api/fiftyone/sort
Content-Type: application/json

{
  "field": "initial_speed",
  "reverse": true
}
```

### タグ追加 API

```bash
POST /api/fiftyone/tag
Content-Type: application/json

{
  "sample_ids": ["sample_id_1", "sample_id_2"],
  "tags": ["reviewed", "high-speed"]
}
```

## トラブルシューティング

### APIが応答しない

```bash
# FastAPIが起動しているか確認
curl http://localhost:8000/health

# FiftyOneが起動しているか確認
curl http://localhost:5151
```

### データセットが見つからない

```bash
# データセットを確認
uv run python scripts/fiftyone_integration.py list
```

データセットが空の場合は、シナリオを追加してください：

```bash
uv run python scripts/fiftyone_integration.py add \
  --logical-uuid <uuid> \
  --parameter-uuid <uuid>
```

## 参考資料

- [FiftyOne Python API](https://docs.voxel51.com/api/fiftyone.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [httpx Documentation](https://www.python-httpx.org/)
