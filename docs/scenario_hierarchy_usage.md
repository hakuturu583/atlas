# シナリオ階層構造の使用方法

dataclassを使った型安全なシナリオ管理システムの使用例。

## 📦 モジュール構成

```
app/models/
├── scenario_hierarchy.py    # dataclass定義（型安全な構造）
├── scenario_builder.py       # ビルダーパターン（構築を簡単に）
└── scenario_serializer.py    # JSON変換（永続化）
```

## 🏗️ 階層構造

```
AbstractScenario (抽象シナリオ)
  - どんな場所でどんな物体が登場するか
  - OpenDRIVE/CARLA非依存
  ↓ 1:N
LogicalScenario (論理シナリオ)
  - パラメータ空間の定義と分布
  - サンプリング可能
  ↓ 1:N
ParameterSet (パラメータセット)
  - サンプリングされた具体値
  - CARLA設定を含む
  ↓ 1:1
ExecutionTrace (実行トレース)
  - 実行結果
  - .rrd/.mp4ファイルへのパス
```

## 📝 基本的な使い方

### 1. 抽象シナリオの作成

```python
from app.models.scenario_builder import (
    AbstractScenarioBuilder,
    ActorType,
    LocationType,
)

# ビルダーパターンで構築
abstract = (
    AbstractScenarioBuilder(
        name="交差点信号機シナリオ",
        description="市街地の交差点で信号機に従って停止・発進する",
        original_prompt="信号機が赤から青に変わったら車両が発進するシナリオ"
    )
    .with_environment(
        location_type=LocationType.INTERSECTION,
        features=["traffic_light", "road", "buildings"],
        weather="Clear",
        time_of_day="Noon"
    )
    .add_actor(
        actor_id="ego_vehicle",
        actor_type=ActorType.VEHICLE,
        role="自動運転車両",
        is_autonomous_stack=True
    )
    .add_maneuver(
        actor_id="ego_vehicle",
        action="信号機に従って停止・発進",
        duration="20s",
        conditions=["信号が赤の時は停止", "信号が青になったら発進"]
    )
    .with_scenario_type("traffic_light_compliance")
    .build()
)

print(f"Abstract UUID: {abstract.uuid}")
```

### 2. 論理シナリオの作成

```python
from app.models.scenario_builder import (
    LogicalScenarioBuilder,
    create_uniform_param,
    create_constant_param,
)

# パラメータ空間を定義
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
                unit="km/h",
                description="初期速度"
            ),
            "distance_to_light": create_uniform_param(
                "distance_to_light",
                min_val=30.0,
                max_val=70.0,
                unit="m",
                description="信号機までの距離"
            )
        }
    )
    .add_parameter_group(
        "traffic_light",
        {
            "red_duration": create_uniform_param(
                "red_duration",
                min_val=3.0,
                max_val=7.0,
                unit="s",
                description="赤信号の継続時間"
            )
        }
    )
    .add_parameter_group(
        "camera",
        {
            "offset_x": create_constant_param("offset_x", -6.0),
            "offset_z": create_constant_param("offset_z", 3.0),
            "pitch": create_constant_param("pitch", -20.0)
        }
    )
    .build()
)

print(f"Logical UUID: {logical.uuid}")
```

### 3. パラメータのサンプリング

```python
from app.models.scenario_builder import sample_parameter_set
from app.models.scenario_hierarchy import CarlaConfig

# パラメータをサンプリング（seed指定で再現性を担保）
param_set = sample_parameter_set(
    logical,
    carla_config=CarlaConfig(
        map="Town10HD_Opt",
        vehicle_type="vehicle.taxi.ford"
    ),
    seed=42
)

print(f"Parameter UUID: {param_set.uuid}")
print(f"Sampled values: {param_set.sampled_values}")

# 出力例:
# {
#   "ego_vehicle": {
#     "initial_speed": 32.5,
#     "distance_to_light": 45.3
#   },
#   "traffic_light": {
#     "red_duration": 5.2
#   },
#   "camera": {
#     "offset_x": -6.0,
#     "offset_z": 3.0,
#     "pitch": -20.0
#   }
# }
```

### 4. 複数回のサンプリング

```python
# 同じ論理シナリオから異なるパラメータセットを生成
param_set_1 = sample_parameter_set(logical, seed=1)
param_set_2 = sample_parameter_set(logical, seed=2)
param_set_3 = sample_parameter_set(logical, seed=3)

# それぞれ異なる値がサンプリングされる
```

### 5. ファイルへの保存

```python
from pathlib import Path
from app.models.scenario_serializer import (
    save_abstract_scenario,
    save_logical_scenario,
    save_parameter_set,
)

base_dir = Path("data/scenarios")

# 各階層を個別に保存
save_abstract_scenario(abstract, base_dir / f"abstract_{abstract.uuid}.json")
save_logical_scenario(logical, base_dir / f"logical_{logical.uuid}.json")
save_parameter_set(param_set, base_dir / f"params_{param_set.uuid}.json")
```

### 6. ファイルからの読み込み

```python
from app.models.scenario_serializer import (
    load_abstract_scenario,
    load_logical_scenario,
    load_parameter_set,
)

# ファイルから復元
abstract_loaded = load_abstract_scenario(base_dir / f"abstract_{abstract.uuid}.json")
logical_loaded = load_logical_scenario(base_dir / f"logical_{logical.uuid}.json")
param_set_loaded = load_parameter_set(base_dir / f"params_{param_set.uuid}.json")

# 型安全に使用できる
assert abstract_loaded.uuid == abstract.uuid
assert logical_loaded.parent_abstract_uuid == abstract.uuid
```

## 🎯 分布の種類

### 固定値 (ConstantValue)

```python
from app.models.scenario_builder import create_constant_param

param = create_constant_param("offset_x", -6.0)
# 常に -6.0 を返す
```

### 一様分布 (UniformDistribution)

```python
from app.models.scenario_builder import create_uniform_param

param = create_uniform_param(
    "speed",
    min_val=20.0,
    max_val=40.0,
    unit="km/h"
)
# 20.0 〜 40.0 の範囲で一様にサンプリング
```

### 正規分布 (NormalDistribution)

```python
from app.models.scenario_builder import create_normal_param

param = create_normal_param(
    "reaction_time",
    mean=0.5,
    std=0.1,
    unit="s"
)
# 平均0.5、標準偏差0.1の正規分布
```

### 選択肢 (ChoiceDistribution)

```python
from app.models.scenario_builder import create_choice_param

param = create_choice_param(
    "weather",
    choices=["Clear", "Cloudy", "WetCloudy", "MidRain"]
)
# 選択肢からランダムに1つ選択
```

## 🔄 実行トレースの作成

```python
from pathlib import Path
from datetime import datetime
from app.models.scenario_hierarchy import ExecutionTrace, ExecutionStatus

execution = ExecutionTrace(
    uuid="exec-uuid",
    parent_parameter_uuid=param_set.uuid,
    parent_logical_uuid=logical.uuid,
    python_file=Path(f"scenarios/{logical.uuid}.py"),
    command=f"uv run python scenarios/{logical.uuid}.py",
    status=ExecutionStatus.SUCCESS,
    exit_code=0,
    started_at=datetime.utcnow(),
    completed_at=datetime.utcnow(),
    duration_seconds=15.3,
    rrd_file=Path(f"data/rerun/{logical.uuid}_{param_set.uuid}.rrd"),
    video_file=Path(f"data/videos/{logical.uuid}_{param_set.uuid}.mp4"),
    embedding_file=Path(f"data/embeddings/{logical.uuid}_{param_set.uuid}.json")
)
```

## 📊 完全な階層構造

```python
from app.models.scenario_hierarchy import ScenarioHierarchy

# すべてをまとめる
hierarchy = ScenarioHierarchy(
    abstract=abstract,
    logical=logical,
    parameter_set=param_set,
    execution=execution  # オプション
)

# 一度にすべて保存
from app.models.scenario_serializer import save_scenario_hierarchy

save_scenario_hierarchy(hierarchy, Path("data/scenarios"))
```

## 🔍 型チェック

dataclassを使うことで、IDEとmypyによる型チェックが効きます。

```python
# ✅ 型安全
abstract.actors[0].type  # ActorType
logical.parameter_space.groups["ego_vehicle"]  # ParameterGroup

# ❌ コンパイル時エラー
abstract.actors[0].invalid_field  # AttributeError (IDEで検出可能)
```

## 📚 参考

- `app/models/scenario_hierarchy.py` - 型定義
- `app/models/scenario_builder.py` - ビルダーパターン
- `app/models/scenario_serializer.py` - シリアライザ
- `examples/scenario_hierarchy_example.py` - 完全な使用例
