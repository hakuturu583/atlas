## シナリオ管理ツール

### 概要

`scenario_manager.py`は、CARLAシナリオのトレーサビリティを管理するためのPythonスクリプトです。

### 階層構造

```
抽象シナリオ (abstract_uuid)
  ↓
論理シナリオ (logical_uuid, parent: abstract_uuid)
  ↓
パラメータ (parameter_uuid, logical: logical_uuid)
  ↓
実行トレース (execution_uuid, logical: logical_uuid, param: parameter_uuid)
```

### ファイル構造

```
data/scenarios/
  ├── abstract_{uuid}.json          # 抽象シナリオ
  ├── logical_{uuid}.json            # 論理シナリオ（parent_abstract_uuid記録）
  ├── params_{uuid}.json             # パラメータ（logical_uuid記録）
  └── execution_{logical}_{param}.json  # 実行トレース

scenarios/
  └── {logical_uuid}.py              # Python実装

data/rerun/
  └── {logical_uuid}_{parameter_uuid}.rrd  # Rerunログ

data/videos/
  └── {logical_uuid}_{parameter_uuid}.mp4  # 動画
```

### 使用方法

#### 1. シナリオの作成

```python
from scripts.scenario_manager import ScenarioManager

manager = ScenarioManager()

# 抽象シナリオを作成
abstract_uuid = manager.create_abstract_scenario(
    name="highway_follow",
    description="高速道路で前方車両を追従するシナリオ",
    original_prompt="高速道路で前方車両を追従するシナリオ",
    actors=[...],
    maneuvers=[...]
)

# 論理シナリオを作成
logical_uuid = manager.create_logical_scenario(
    parent_abstract_uuid=abstract_uuid,
    name="highway_follow",
    description="高速道路追従の論理シナリオ",
    map_requirements={...},
    initial_conditions={...},
    events=[...]
)

# パラメータを作成（同じ論理シナリオで複数作成可能）
param_uuid_1 = manager.create_parameters(
    logical_uuid=logical_uuid,
    carla_config={"host": "localhost", "port": 2000, "map": "Town04"},
    vehicles={...},
    scenario={...}
)

param_uuid_2 = manager.create_parameters(
    logical_uuid=logical_uuid,
    carla_config={"host": "localhost", "port": 2000, "map": "Town05"},
    vehicles={...},  # 異なるパラメータ
    scenario={...}
)
```

#### 2. シナリオの実行

```bash
# パラメータ1で実行
uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{param_uuid_1}.json

# パラメータ2で実行
uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{param_uuid_2}.json
```

#### 3. 実行トレースの記録

```python
# シナリオ実行後、トレースを記録
manager.create_execution_trace(
    logical_uuid=logical_uuid,
    parameter_uuid=param_uuid_1,
    python_file=f"scenarios/{logical_uuid}.py",
    command=f"uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{param_uuid_1}.json",
    exit_code=0,
    status="success"
)
```

#### 4. シナリオの一覧表示

```bash
# 抽象シナリオ一覧
python scripts/scenario_manager.py list-abstract

# 論理シナリオ一覧
python scripts/scenario_manager.py list-logical

# 特定の抽象シナリオから派生した論理シナリオ
python scripts/scenario_manager.py list-logical {abstract_uuid}

# パラメータ一覧
python scripts/scenario_manager.py list-params

# 特定の論理シナリオのパラメータ
python scripts/scenario_manager.py list-params {logical_uuid}
```

### 使用例の実行

```bash
# 完全な例を実行（抽象→論理→パラメータ×2を作成）
uv run python scripts/example_create_scenario.py
```

### トレーサビリティの分析

```bash
# 全体の階層構造を表示
uv run python scripts/analyze_scenarios.py

# 特定の論理シナリオの系譜を追跡
uv run python scripts/analyze_scenarios.py {logical_uuid}
```

### ファイル名の意味

- **抽象シナリオ**: `abstract_{uuid}.json`
  - ユーザーの元の要件を構造化したもの

- **論理シナリオ**: `logical_{uuid}.json`
  - OpenDRIVE非依存の中間表現
  - `parent_abstract_uuid`で親を記録

- **パラメータ**: `params_{uuid}.json`
  - 具体的な実行パラメータ（マップ、座標、速度等）
  - `logical_uuid`で論理シナリオを記録

- **実行トレース**: `execution_{logical_uuid}_{parameter_uuid}.json`
  - 実行結果のメタデータ
  - 全てのUUIDを記録

- **出力ファイル**: `{logical_uuid}_{parameter_uuid}.{rrd,mp4}`
  - どの論理シナリオをどのパラメータで実行したかが一目瞭然

### 利点

1. **トレーサビリティ**: 全てのシナリオがUUIDで一意に識別され、親子関係が明確
2. **再現性**: パラメータファイルにより、同じ実行を再現可能
3. **バリエーション**: 1つの論理シナリオから複数のパラメータセットを作成可能
4. **自動化**: UUID生成やJSON管理がスクリプトで自動化
5. **分析**: analyze_scenarios.pyで関係を可視化

### 注意事項

- UUIDは自動生成されるため、手動で編集しないこと
- ファイルを直接削除する場合は、関連ファイルも削除すること（孤立を防ぐため）
- パラメータUUIDと実行UUIDは同じ値を使用
