# scenario-writerスキルの修正指針

## 目的

scenario-writerスキルを新しいデータモデル（`DATA_MODEL.md`）に準拠させる。

## 主要な変更点

### 変更前（旧実装）

1. **Phase 1**: 抽象シナリオを直接JSONファイルに書き出し
2. **Phase 2**: 論理シナリオを直接JSONファイルに書き出し（`initial_conditions`や`events`を含む）
3. **Phase 3**: パラメータファイルを独立したファイルとして作成（`{scenario_name}_{uuid}_params.json`）
4. **Phase 5**: 実行トレースを独自形式で記録

### 変更後（新実装）

1. **Phase 1**: `ScenarioManager.create_abstract_scenario()`を使用
2. **Phase 2**: `ScenarioManager.create_logical_scenario()`を使用（`parameter_space`のみ、分布情報）
3. **Phase 3**: `ScenarioManager.sample_parameters()`を使用（具体値をサンプリング）
4. **Phase 5**: `ScenarioManager.create_execution_trace()`を使用

---

## Phase 1: 抽象シナリオ生成

### 変更前

```python
abstract_scenario = {
    "uuid": str(uuid.uuid4()),
    "name": "...",
    # ... その他のフィールド
}

with open(f"data/scenarios/abstract_{uuid}.json", "w") as f:
    json.dump(abstract_scenario, f, indent=2)
```

### 変更後

```python
from scripts.scenario_manager import ScenarioManager

manager = ScenarioManager()

abstract_uuid = manager.create_abstract_scenario(
    name="交差点信号機遵守シナリオ",
    description="市街地の交差点で信号機に従って停止・発進する",
    original_prompt=user_prompt,  # ユーザーの元の要件
    environment={
        "location_type": "urban_intersection",
        "features": ["traffic_light", "road", "buildings"]
    },
    actors=[
        {
            "id": "ego_vehicle",
            "type": "vehicle",
            "role": "自動運転車両",
            "is_autonomous_stack": True
        },
        {
            "id": "traffic_light",
            "type": "traffic_signal",
            "role": "交差点の信号機"
        }
    ],
    scenario_type="traffic_light_compliance"
)

# abstract_uuidが返される
```

### 重要な変更点

- ✅ ScenarioManagerのAPIを使う
- ✅ UUIDは自動生成される
- ✅ ファイルパスは自動で決定される（`data/scenarios/abstract_{uuid}.json`）

---

## Phase 2: 論理シナリオ生成

### 変更前

```python
logical_scenario = {
    "uuid": str(uuid.uuid4()),
    "parent_abstract_uuid": abstract_uuid,
    "name": "...",
    "initial_conditions": {
        "ego_vehicle": {
            "location": "...",
            "speed": 50.0  # ← 具体値が入っていた
        }
    },
    "events": [...]
}

with open(f"data/scenarios/logical_{uuid}.json", "w") as f:
    json.dump(logical_scenario, f, indent=2)
```

### 変更後

```python
logical_uuid = manager.create_logical_scenario(
    parent_abstract_uuid=abstract_uuid,
    name="交差点信号機遵守論理シナリオ",
    description="パラメータ空間を定義した論理シナリオ",
    parameter_space={
        "ego_vehicle": {
            "initial_speed": {
                "type": "float",
                "unit": "km/h",
                "distribution": "uniform",  # ← 分布情報
                "min": 20.0,
                "max": 40.0,
                "description": "交差点接近時の速度"
            },
            "distance_to_light": {
                "type": "float",
                "unit": "m",
                "distribution": "uniform",
                "min": 30.0,
                "max": 70.0,
                "description": "信号機までの距離"
            }
        },
        "traffic_light": {
            "red_duration": {
                "type": "float",
                "unit": "s",
                "distribution": "uniform",
                "min": 3.0,
                "max": 7.0,
                "description": "赤信号の継続時間"
            }
        },
        "environment": {
            "weather": {
                "type": "string",
                "distribution": "choice",
                "choices": ["ClearNoon", "CloudyNoon", "WetNoon"],
                "description": "天候設定"
            }
        },
        "camera": {
            "offset_x": {
                "type": "float",
                "unit": "m",
                "distribution": "constant",
                "value": -6.0,
                "description": "車両後方のカメラ位置X"
            }
        }
    }
)

# logical_uuidが返される
```

### 重要な変更点

- ✅ **分布情報のみを記録**（`distribution`, `min`, `max`, `mean`, `std`, `choices`, `value`）
- ✅ **具体値は入れない**（`speed: 50.0`のような値は削除）
- ✅ `initial_conditions`や`events`は削除（パラメータ空間定義に統一）
- ✅ 各パラメータに`type`, `unit`, `description`を追加

### パラメータ定義のパターン

#### 一様分布

```python
"initial_speed": {
    "type": "float",
    "unit": "km/h",
    "distribution": "uniform",
    "min": 20.0,
    "max": 40.0,
    "description": "交差点接近時の速度"
}
```

#### 正規分布

```python
"reaction_time": {
    "type": "float",
    "unit": "s",
    "distribution": "normal",
    "mean": 0.5,
    "std": 0.1,
    "description": "反応時間"
}
```

#### 選択肢

```python
"weather": {
    "type": "string",
    "distribution": "choice",
    "choices": ["ClearNoon", "CloudyNoon", "WetNoon"],
    "description": "天候設定"
}
```

#### 固定値

```python
"offset_x": {
    "type": "float",
    "unit": "m",
    "distribution": "constant",
    "value": -6.0,
    "description": "カメラのX座標オフセット"
}
```

---

## Phase 3: パラメータサンプリングとPython実装生成

### 変更前

```python
# パラメータを直接書き出し
params = {
    "scenario_uuid": str(uuid.uuid4()),
    "ego_vehicle": {
        "initial_speed": 45.0  # ← 直接具体値を入れていた
    },
    "output_video": f"data/videos/{scenario_name}_{uuid}.mp4"
}

with open(f"data/scenarios/{scenario_name}_{uuid}_params.json", "w") as f:
    json.dump(params, f, indent=2)

# Python実装を生成
python_code = generate_python_implementation(logical_scenario, params)
with open(f"scenarios/{logical_uuid}.py", "w") as f:
    f.write(python_code)
```

### 変更後

```python
# パラメータをサンプリング（具体値を生成）
param_uuid = manager.sample_parameters(
    logical_uuid=logical_uuid,
    carla_config={
        "host": "localhost",
        "port": 2000,
        "map": "Town10HD_Opt",
        "vehicle_type": "vehicle.tesla.model3"
    },
    seed=42  # 再現性のため（オプション）
)

# サンプリングされたパラメータを取得
params = manager.get_parameters(logical_uuid, param_uuid)

# params["sampled_values"] に具体値が入っている
# 例: params["sampled_values"]["ego_vehicle"]["initial_speed"] = 35.2

# Python実装を生成（論理シナリオとサンプリングされたパラメータから）
python_code = generate_python_implementation(logical_uuid, param_uuid, params)

# Python実装を保存
python_file = f"scenarios/{logical_uuid}.py"
with open(python_file, "w") as f:
    f.write(python_code)
```

### 重要な変更点

- ✅ `manager.sample_parameters()`で具体値をサンプリング
- ✅ パラメータファイルは`logical_{uuid}_parameters.json`形式で自動保存される
- ✅ 1つの論理シナリオから複数のパラメータセットを生成可能
- ✅ Python実装では`param_uuid`を使ってパラメータを取得

### Python実装での変更点

#### 旧実装

```python
# コマンドライン引数でパラメータファイルを受け取る
parser.add_argument('--params', required=True)
args = parser.parse_args()

with open(args.params) as f:
    params = json.load(f)

# パラメータを直接使用
speed = params['ego_vehicle']['initial_speed']
```

#### 新実装

```python
# コマンドライン引数で論理UUIDとパラメータUUIDを受け取る
parser.add_argument('--logical-uuid', required=True)
parser.add_argument('--param-uuid', required=True)
args = parser.parse_args()

# ScenarioManagerからパラメータを取得
from scripts.scenario_manager import ScenarioManager
manager = ScenarioManager()
params = manager.get_parameters(args.logical_uuid, args.param_uuid)

# sampled_valuesから値を取得
speed = params['sampled_values']['ego_vehicle']['initial_speed']
carla_config = params['carla_config']
output_files = params['output']
```

---

## Phase 4: 実行

### 変更前

```bash
uv run python scenarios/{logical_uuid}.py --params data/scenarios/{scenario_name}_{uuid}_params.json
```

### 変更後

```bash
uv run python scenarios/{logical_uuid}.py --logical-uuid {logical_uuid} --param-uuid {param_uuid}
```

または、パラメータファイルを直接渡す場合：

```bash
uv run python scenarios/{logical_uuid}.py --params data/scenarios/logical_{logical_uuid}_parameters.json --param-uuid {param_uuid}
```

---

## Phase 5: 実行トレース記録

### 変更前

```python
# 独自形式で実行トレースを記録
execution_trace = {
    "execution_uuid": str(uuid.uuid4()),
    "scenario_uuid": logical_uuid,
    # ...
}

with open(f"data/scenarios/execution_{uuid}.json", "w") as f:
    json.dump(execution_trace, f, indent=2)
```

### 変更後

```python
# ScenarioManagerで実行トレースを記録
trace_file = manager.create_execution_trace(
    logical_uuid=logical_uuid,
    parameter_uuid=param_uuid,
    python_file=python_file,
    command=f"uv run python {python_file} --logical-uuid {logical_uuid} --param-uuid {param_uuid}",
    exit_code=result.returncode,
    status="success" if result.returncode == 0 else "failed"
)

# trace_fileパスが返される
# 例: data/scenarios/execution_{logical_uuid}_{param_uuid}.json
```

### 重要な変更点

- ✅ 完全なトレーサビリティ（抽象→論理→パラメータ→実行）
- ✅ 標準化されたファイル命名規則
- ✅ 親子関係の自動記録

---

## 実装チェックリスト

### Phase 1: 抽象シナリオ生成

- [ ] `ScenarioManager.create_abstract_scenario()`を使用
- [ ] `environment`, `actors`, `scenario_type`を正しく渡す
- [ ] `original_prompt`にユーザーの元の要件を記録

### Phase 2: 論理シナリオ生成

- [ ] `ScenarioManager.create_logical_scenario()`を使用
- [ ] `parameter_space`に**分布情報のみ**を記録
- [ ] 各パラメータに`type`, `unit`, `distribution`, `description`を含める
- [ ] `distribution`に応じて適切なフィールドを設定（`min/max`, `mean/std`, `choices`, `value`）
- [ ] **具体値を入れない**（`speed: 50.0`のような値は削除）

### Phase 3: パラメータサンプリング

- [ ] `ScenarioManager.sample_parameters()`を使用
- [ ] `carla_config`を渡す（`host`, `port`, `map`, `vehicle_type`）
- [ ] オプションで`seed`を渡す（再現性確保）
- [ ] `manager.get_parameters()`で具体値を取得

### Phase 4: Python実装生成

- [ ] コマンドライン引数を`--logical-uuid`, `--param-uuid`に変更
- [ ] `manager.get_parameters()`でパラメータを取得
- [ ] `params['sampled_values']`から具体値を使用
- [ ] `params['carla_config']`でCARLA設定を取得
- [ ] `params['output']`で出力ファイルパスを取得

### Phase 5: 実行トレース記録

- [ ] `ScenarioManager.create_execution_trace()`を使用
- [ ] `logical_uuid`, `parameter_uuid`を渡す
- [ ] `python_file`, `command`, `exit_code`, `status`を記録

---

## 移行手順

1. **scripts/scenario_manager.pyを確認**
   - 最新版を使用していることを確認
   - `seed`フィールドが記録されることを確認

2. **scenario-writerスキルを修正**
   - Phase 1, 2, 3, 5をScenarioManagerのAPIに置き換え
   - parameter_spaceの構造を修正（分布情報のみ）

3. **Python実装テンプレートを修正**
   - コマンドライン引数を変更
   - ScenarioManagerからパラメータを取得するコードに変更

4. **既存のシナリオファイルを移行（オプション）**
   - 旧形式のファイルを新形式に変換
   - または、新しいシナリオ生成時に新形式を使用

5. **テスト**
   - シンプルなシナリオで動作確認
   - トレーサビリティを確認（抽象→論理→パラメータ→実行）

---

## まとめ

### 新しいデータモデルの利点

1. **完全なトレーサビリティ**
   - 要件 → 抽象 → 論理 → パラメータ → 実行の追跡が可能

2. **再現性の確保**
   - `seed`による再現可能なサンプリング
   - 分布情報の明確な記録

3. **複数パラメータセットの管理**
   - 1つの論理シナリオから複数のパラメータセットを生成
   - 各パラメータセットが独立して管理される

4. **標準化されたファイル構造**
   - UUID-based命名規則
   - ファイル名から関係性がわかる

5. **明確な責任分離**
   - 論理シナリオ: 分布情報のみ
   - パラメータファイル: 具体値のみ
