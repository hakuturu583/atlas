# シナリオ階層構造 - dataclassモデル

## 📦 概要

ATLASプロジェクトのシナリオ管理システムをdataclassで型安全に再実装しました。

### 主要な特徴

✅ **型安全**: dataclassによる厳密な型定義
✅ **階層構造**: Abstract → Logical → Parameters → Execution
✅ **分布サポート**: 一様分布、正規分布、固定値、選択肢
✅ **ビルダーパターン**: 直感的な構築API
✅ **JSON互換**: シリアライズ/デシリアライズ完備
✅ **IDEサポート**: 自動補完とエラー検出

## 📁 ファイル構成

```
app/models/
├── scenario_hierarchy.py     # 型定義（dataclass）
│   ├── Distribution          # 分布の型
│   ├── AbstractScenario     # 抽象シナリオ
│   ├── LogicalScenario      # 論理シナリオ
│   ├── ParameterSet         # パラメータセット
│   └── ExecutionTrace       # 実行トレース
│
├── scenario_builder.py        # ビルダーAPI
│   ├── AbstractScenarioBuilder
│   ├── LogicalScenarioBuilder
│   └── ヘルパー関数
│
└── scenario_serializer.py    # JSON変換
    ├── serialize_*()
    ├── deserialize_*()
    └── save/load functions

docs/
└── scenario_hierarchy_usage.md  # 詳細な使用方法

examples/
└── scenario_hierarchy_example.py  # 完全な動作例
```

## 🚀 クイックスタート

### 1. 抽象シナリオの作成

```python
from app.models.scenario_builder import (
    AbstractScenarioBuilder,
    ActorType,
    LocationType,
)

abstract = (
    AbstractScenarioBuilder(
        name="交差点信号機シナリオ",
        description="市街地の交差点で信号機に従って停止・発進する",
        original_prompt="信号機が赤から青に変わったら車両が発進するシナリオ"
    )
    .with_environment(
        location_type=LocationType.INTERSECTION,
        features=["traffic_light", "road"]
    )
    .add_actor(
        actor_id="ego_vehicle",
        actor_type=ActorType.VEHICLE,
        role="自動運転車両",
        is_autonomous_stack=True
    )
    .build()
)
```

### 2. 論理シナリオの作成

```python
from app.models.scenario_builder import (
    LogicalScenarioBuilder,
    create_uniform_param,
    create_constant_param,
)

logical = (
    LogicalScenarioBuilder(
        parent_abstract_uuid=abstract.uuid,
        name="交差点信号機シナリオ",
        description="パラメータ空間の定義"
    )
    .add_parameter_group(
        "ego_vehicle",
        {
            "initial_speed": create_uniform_param(
                "initial_speed",
                min_val=20.0,
                max_val=40.0,
                unit="km/h"
            ),
            "distance_to_light": create_uniform_param(
                "distance_to_light",
                min_val=30.0,
                max_val=70.0,
                unit="m"
            )
        }
    )
    .add_parameter_group(
        "camera",
        {
            "offset_x": create_constant_param("offset_x", -6.0),
            "offset_z": create_constant_param("offset_z", 3.0)
        }
    )
    .build()
)
```

### 3. パラメータのサンプリング

```python
from app.models.scenario_builder import sample_parameter_set
from app.models.scenario_hierarchy import CarlaConfig

param_set = sample_parameter_set(
    logical,
    carla_config=CarlaConfig(map="Town10HD_Opt"),
    seed=42  # 再現性
)

print(param_set.sampled_values)
# {
#   "ego_vehicle": {
#     "initial_speed": 32.5,
#     "distance_to_light": 45.3
#   },
#   "camera": {
#     "offset_x": -6.0,
#     "offset_z": 3.0
#   }
# }
```

### 4. ファイル保存

```python
from pathlib import Path
from app.models.scenario_serializer import (
    save_abstract_scenario,
    save_logical_scenario,
    save_parameter_set,
)

base_dir = Path("data/scenarios")

save_abstract_scenario(abstract, base_dir / f"abstract_{abstract.uuid}.json")
save_logical_scenario(logical, base_dir / f"logical_{logical.uuid}.json")
save_parameter_set(param_set, base_dir / f"params_{param_set.uuid}.json")
```

## 🎯 分布の種類

| 分布 | クラス | 使用例 |
|------|--------|--------|
| **固定値** | `ConstantValue` | カメラのオフセット |
| **一様分布** | `UniformDistribution` | 初期速度、距離 |
| **正規分布** | `NormalDistribution` | 反応時間 |
| **選択肢** | `ChoiceDistribution` | 天候、車両タイプ |

## 📊 階層構造

```
AbstractScenario
  uuid: "93c709df-..."
  name: "交差点信号機シナリオ"
  actors: [Actor, Actor]
  maneuvers: [Maneuver, Maneuver]
  ↓
LogicalScenario
  uuid: "8908f3a0-..."
  parent_abstract_uuid: "93c709df-..."
  parameter_space: ParameterSpace
    ↓
ParameterSet (seed=42)
  uuid: "1b002c69-..."
  parent_logical_uuid: "8908f3a0-..."
  sampled_values: {...}
    ↓
ParameterSet (seed=43)
  uuid: "5d18c05e-..."
  parent_logical_uuid: "8908f3a0-..."
  sampled_values: {...}
    ↓
ExecutionTrace
  uuid: "exec-uuid"
  parent_parameter_uuid: "1b002c69-..."
  status: SUCCESS
  rrd_file: "data/rerun/*.rrd"
  video_file: "data/videos/*.mp4"
```

## 🔧 型安全性

### ✅ IDEでの自動補完

```python
abstract.actors[0].type  # ActorType（列挙型）
abstract.actors[0].invalid  # ← エラー（存在しないフィールド）
```

### ✅ mypyでの型チェック

```bash
mypy app/models/scenario_hierarchy.py
# → Success: no issues found
```

### ✅ 実行時の型検証

```python
from dataclasses import asdict

# dataclass → dict
data = asdict(abstract)

# dict → dataclass（型チェック付き）
from app.models.scenario_serializer import deserialize_abstract_scenario
abstract_restored = deserialize_abstract_scenario(data)
```

## 🧪 テストとバリデーション

### 使用例の実行

```bash
uv run python examples/scenario_hierarchy_example.py
```

### 期待される出力

```
============================================================
シナリオ階層構造の使用例
============================================================

[1/5] 抽象シナリオを作成中...
  ✓ 抽象シナリオ作成完了
    UUID: 93c709df-06fb-42e0-80c0-154112752932
    アクター数: 2
    マニューバー数: 2

[2/5] 論理シナリオを作成中...
  ✓ 論理シナリオ作成完了
    パラメータグループ数: 5

[3/5] パラメータをサンプリング中...
  ✓ パラメータセット 1 作成完了
  ✓ パラメータセット 2 作成完了
  ✓ パラメータセット 3 作成完了

[4/5] ファイルに保存中...
  ✓ 抽象シナリオ保存
  ✓ 論理シナリオ保存
  ✓ パラメータセット保存 (×3)

[5/5] ファイルから読み込み中...
  ✓ すべて正常に読み込み完了

============================================================
✓ すべての処理が正常に完了しました
============================================================
```

## 📚 詳細ドキュメント

- **使用方法**: [`docs/scenario_hierarchy_usage.md`](./scenario_hierarchy_usage.md)
- **API リファレンス**: `app/models/scenario_hierarchy.py` のdocstring
- **動作例**: `examples/scenario_hierarchy_example.py`

## 🔄 既存コードからの移行

### 旧: Pydantic BaseModel

```python
from pydantic import BaseModel

class Scenario(BaseModel):
    name: str
    actors: list
```

### 新: dataclass

```python
from dataclasses import dataclass
from typing import List

@dataclass
class Scenario:
    name: str
    actors: List[Actor]
```

### 互換性

- **JSON変換**: `scenario_serializer.py` で完全サポート
- **既存ファイル**: デシリアライザで読み込み可能
- **段階的移行**: 旧コードと共存可能

## ✨ 利点

1. **型安全性**: コンパイル時エラー検出
2. **可読性**: 明確な構造定義
3. **保守性**: IDEの支援
4. **パフォーマンス**: Pydanticより高速
5. **標準ライブラリ**: 外部依存なし

## 🎓 学習リソース

- [Python dataclasses ドキュメント](https://docs.python.org/3/library/dataclasses.html)
- [ATLASシナリオ階層構造](./scenario_hierarchy_usage.md)
- [使用例](../examples/scenario_hierarchy_example.py)
