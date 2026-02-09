# FiftyOne統合ガイド

## 概要

FiftyOne は強力なコンピュータビジョンデータセット管理ツールです。ATLASではCARLAシナリオの実行結果（動画、メタデータ）をFiftyOneで可視化・分析できます。

## セットアップ

FiftyOneは既にインストール済みです。

```bash
# FiftyOneのバージョン確認
uv run python -c "import fiftyone as fo; print(fo.__version__)"
```

## 基本的な使い方

### 1. シナリオをFiftyOneに追加

CARLAシナリオを実行した後、その結果をFiftyOneデータセットに追加します。

```bash
# シナリオを追加
uv run python scripts/fiftyone_integration.py add \
    --logical-uuid 9eab1c6c-728b-4a3a-9588-5f64a1daad9c \
    --parameter-uuid <parameter-uuid>

# 出力例:
# ✓ 既存のデータセットをロード: carla-scenarios
# ✓ シナリオをデータセットに追加: 9eab1c6c-728b-4a3a-9588-5f64a1daad9c_<uuid>.mp4
# ✓ データセット保存完了
```

### 2. FiftyOne GUIを起動

ローカルでFiftyOne GUIを起動し、ブラウザでデータセットを可視化します。

```bash
# GUIを起動（デフォルト: http://localhost:5151）
uv run python scripts/fiftyone_integration.py launch

# カスタムポートで起動
uv run python scripts/fiftyone_integration.py launch --port 8080
```

ブラウザが自動的に開き、FiftyOne GUIが表示されます。

### 3. データセット一覧を確認

```bash
uv run python scripts/fiftyone_integration.py list

# 出力例:
# === FiftyOneデータセット一覧 ===
#
#   carla-scenarios:
#     サンプル数: 5
#     フィールド: ['id', 'filepath', 'logical_uuid', 'parameter_uuid', ...]
```

### 4. データセットをクリア

```bash
# データセット削除
uv run python scripts/fiftyone_integration.py clear --dataset-name carla-scenarios
```

## 完全なワークフロー例

### シナリオ実行 → FiftyOne可視化

```bash
# 1. シナリオのパラメータUUIDを確認
uv run python scripts/scenario_manager.py list-params 9eab1c6c-728b-4a3a-9588-5f64a1daad9c

# 出力例:
# === パラメータ一覧（論理シナリオ: 9eab1c6c-728b-4a3a-9588-5f64a1daad9c）===
#   UUID: abc123-def456-...
#   ...

# 2. シナリオを実行
uv run python scenarios/9eab1c6c-728b-4a3a-9588-5f64a1daad9c.py \
    --logical-uuid 9eab1c6c-728b-4a3a-9588-5f64a1daad9c \
    --parameter-uuid abc123-def456-...

# 3. FiftyOneに追加
uv run python scripts/fiftyone_integration.py add \
    --logical-uuid 9eab1c6c-728b-4a3a-9588-5f64a1daad9c \
    --parameter-uuid abc123-def456-...

# 4. FiftyOne GUIを起動
uv run python scripts/fiftyone_integration.py launch
```

## FiftyOne GUI の機能

### サンプルの閲覧

- **Grid View**: 動画のサムネイル一覧を表示
- **Sample View**: 個別の動画を再生

### フィルタリング

```python
# 例: 初期速度が30km/h以上のシナリオ
dataset.filter_field("initial_speed", F("initial_speed") >= 30.0)
```

### メタデータ表示

各動画サンプルには以下のメタデータが含まれます:

- `logical_uuid`: 論理シナリオUUID
- `parameter_uuid`: パラメータUUID
- `initial_speed`: 初期速度 (km/h)
- `distance_to_light`: 信号機までの距離 (m)
- `duration`: シナリオ実行時間 (秒)
- `carla_map`: CARLAマップ名
- `vehicle_type`: 車両タイプ

### ソート

- 初期速度順
- シナリオ実行時間順
- CARLAマップ別

### タグ付け

FiftyOne GUIでサンプルに任意のタグを追加できます:

- 成功/失敗
- バグ発見
- 検証済み
- など

## Python APIの使用例

### データセットをプログラムから操作

```python
import fiftyone as fo

# データセットをロード
dataset = fo.load_dataset("carla-scenarios")

# サンプル数を取得
print(f"サンプル数: {len(dataset)}")

# メタデータでフィルタリング
# 例: Town10HD_Optマップのシナリオのみ
town10_samples = dataset.match(fo.ViewField("carla_map") == "Town10HD_Opt")
print(f"Town10HD_Opt サンプル数: {len(town10_samples)}")

# 初期速度が30km/h以上のシナリオ
high_speed_samples = dataset.match(fo.ViewField("initial_speed") >= 30.0)
print(f"高速サンプル数: {len(high_speed_samples)}")

# セッションを起動
session = fo.launch_app(dataset)
session.wait()
```

### 統計情報を取得

```python
import fiftyone as fo
import pandas as pd

dataset = fo.load_dataset("carla-scenarios")

# メタデータをDataFrameに変換
data = []
for sample in dataset:
    data.append({
        "logical_uuid": sample["logical_uuid"],
        "parameter_uuid": sample["parameter_uuid"],
        "initial_speed": sample.get("initial_speed", 0.0),
        "distance_to_light": sample.get("distance_to_light", 0.0),
        "carla_map": sample.get("carla_map", "unknown")
    })

df = pd.DataFrame(data)

# 統計情報を表示
print(df.describe())
print(df.groupby("carla_map").count())
```

## トラブルシューティング

### ポートが既に使用されている

```bash
# カスタムポートで起動
uv run python scripts/fiftyone_integration.py launch --port 8888
```

### データベースの場所

FiftyOneのデータベースはデフォルトで `~/.fiftyone/` に保存されます。

```bash
# データベースの場所を確認
uv run python -c "import fiftyone.config as foc; print(foc.database_dir)"
```

### データセットのバックアップ

```bash
# データセットをエクスポート
uv run python -c "
import fiftyone as fo
dataset = fo.load_dataset('carla-scenarios')
dataset.export(
    export_dir='data/fiftyone_backup',
    dataset_type=fo.types.FiftyOneDataset
)
"
```

### データセットのインポート

```bash
# データセットをインポート
uv run python -c "
import fiftyone as fo
dataset = fo.Dataset.from_dir(
    dataset_dir='data/fiftyone_backup',
    dataset_type=fo.types.FiftyOneDataset,
    name='carla-scenarios-restored'
)
"
```

## 高度な使用例

### 複数のデータセットを作成

```bash
# マップ別にデータセットを作成
uv run python scripts/fiftyone_integration.py add \
    --logical-uuid <uuid> \
    --parameter-uuid <uuid> \
    --dataset-name carla-town10

uv run python scripts/fiftyone_integration.py add \
    --logical-uuid <uuid> \
    --parameter-uuid <uuid> \
    --dataset-name carla-town04
```

### カスタムメタデータを追加

`fiftyone_integration.py` の `add_scenario()` メソッドに `metadata` パラメータを追加して、任意のメタデータを付与できます。

```python
from scripts.fiftyone_integration import CarlaFiftyOneManager

manager = CarlaFiftyOneManager()
dataset = manager.load_or_create_dataset()

manager.add_scenario(
    dataset=dataset,
    logical_uuid="...",
    parameter_uuid="...",
    mp4_file=Path("data/videos/....mp4"),
    metadata={
        "weather": "cloudy",
        "time_of_day": "noon",
        "traffic_density": "medium",
        "test_result": "pass"
    }
)

dataset.save()
```

## 参考リンク

- [FiftyOne Documentation](https://docs.voxel51.com/)
- [FiftyOne Tutorials](https://docs.voxel51.com/tutorials/index.html)
- [FiftyOne Python API](https://docs.voxel51.com/api/fiftyone.html)
