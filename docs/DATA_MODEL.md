# ATLASデータモデル仕様

## 概要

ATLASのシナリオ管理は、PEGASUS 6 Layerに基づいた階層構造を採用しています。

```
自然言語シナリオ (Natural Language)
  ↓ PEGASUS 6 Layer分析
PEGASUS分析結果 (PEGASUS Analysis)
  ↓ 構造化
抽象シナリオ (Abstract)
  ↓ パラメータ空間抽出 (1:N)
論理シナリオ (Logical)
  ↓ サンプリング (1:N)
パラメータセット (Parameters)
  ↓ 実行 (1:1)
実行トレース (Execution)
```

---

## 0. 自然言語シナリオ (Natural Language Scenario)

**ファイル名**: `data/scenarios/natural_{uuid}.json`

**目的**: ユーザーの元の要件を非構造化テキストとして記録。PEGASUS分析の入力となる。

```json
{
  "uuid": "natural-uuid",
  "prompt": "市街地交差点で死角から車両が突然飛び出してくる危険なシナリオ",
  "created_at": "2026-02-09T09:00:00Z",
  "user_metadata": {
    "source": "user_input",
    "context": "危険シナリオのテスト"
  }
}
```

---

## 0.5. PEGASUS分析結果 (PEGASUS Analysis)

**ファイル名**: `data/scenarios/pegasus_{natural_uuid}.json`

**目的**: PEGASUS 6 Layerに基づいた構造化分析。自然言語シナリオから抽象シナリオへの橋渡し。

```json
{
  "uuid": "pegasus-uuid",
  "natural_scenario_uuid": "natural-uuid",
  "created_at": "2026-02-09T09:01:00Z",
  "analysis": {
    "layer_1_road": {
      "description": "市街地T字路/十字路交差点",
      "expected_values": {
        "road_type": ["urban_intersection", "T_junction", "crossroad"],
        "lane_count": [2, 3],
        "intersection_width": {"min": 6.0, "max": 10.0, "unit": "m"}
      },
      "carla_mapping": {
        "map": "Town10HD_Opt",
        "road_features": ["intersection", "multi_lane"]
      }
    },
    "layer_2_infrastructure": {
      "description": "信号機なし、一時停止標識あり",
      "expected_values": {
        "traffic_signals": false,
        "stop_signs": true,
        "road_markings": ["stop_line", "crosswalk"]
      },
      "carla_mapping": {
        "use_traffic_lights": false,
        "stop_sign_locations": ["side_road_entry"]
      }
    },
    "layer_3_temporary": {
      "description": "建物・駐車車両による視界遮蔽",
      "expected_values": {
        "occlusion_type": ["building", "parked_vehicle"],
        "occlusion_distance": {"min": 10.0, "max": 20.0, "unit": "m"}
      },
      "carla_mapping": {
        "static_obstacles": ["building_corner"],
        "parked_vehicles": true
      }
    },
    "layer_4_objects": {
      "description": "2台の車両（自車と飛び出し車両）",
      "expected_values": {
        "ego_vehicle": {
          "type": "vehicle",
          "initial_speed": {"min": 40.0, "max": 50.0, "unit": "km/h"},
          "maneuver": "straight_driving"
        },
        "oncoming_vehicle": {
          "type": "vehicle",
          "initial_state": "stopped",
          "maneuver": "sudden_entry",
          "acceleration": {"min": 3.0, "max": 5.0, "unit": "m/s²"}
        }
      },
      "carla_mapping": {
        "ego_vehicle": {"vehicle_type": "vehicle.taxi.ford", "is_autonomous_stack": true},
        "oncoming_vehicle": {"vehicle_type": "vehicle.audi.a2", "is_autonomous_stack": false}
      }
    },
    "layer_5_environment": {
      "description": "晴天、昼間、乾燥路面",
      "expected_values": {
        "weather": ["ClearNoon", "CloudyNoon"],
        "time_of_day": "noon",
        "road_condition": "dry"
      },
      "carla_mapping": {
        "weather_preset": "ClearNoon",
        "sun_altitude_angle": 70.0
      }
    },
    "layer_6_digital": {
      "description": "センサーベース認識（カメラ、LiDAR）",
      "expected_values": {
        "sensors": ["camera", "lidar"],
        "perception_range": {"min": 50.0, "max": 100.0, "unit": "m"}
      },
      "carla_mapping": {
        "camera": {"fov": 90, "image_size_x": 1280, "image_size_y": 720},
        "lidar": {"channels": 64, "range": 100.0}
      }
    }
  },
  "criticality": {
    "level": "high",
    "factors": ["occlusion", "sudden_maneuver", "collision_risk"],
    "ttc_threshold": 1.5
  }
}
```

### PEGASUS Layer詳細

各Layerには以下のフィールドが含まれます：

- **`description`**: 自然言語での説明
- **`expected_values`**: 期待される値の範囲や選択肢（パラメータ空間のヒント）
- **`carla_mapping`**: CARLAでの実装方法

---

## 1. 抽象シナリオ (Abstract Scenario)

**ファイル名**: `data/scenarios/abstract_{uuid}.json`

**目的**: シナリオの概念的な記述。PEGASUS分析結果を統合し、どんな場所で、どんなアクターが、何をするかを構造化。

```json
{
  "uuid": "abstract-uuid",
  "natural_scenario_uuid": "natural-uuid",
  "pegasus_analysis_uuid": "pegasus-uuid",
  "name": "交差点死角飛び出しシナリオ",
  "description": "市街地交差点で死角から車両が突然飛び出してくる危険なシナリオ",
  "created_at": "2026-02-09T10:00:00Z",
  "original_prompt": "市街地交差点で死角から車両が突然飛び出してくる危険なシナリオ",
  "pegasus_layers": {
    "layer_1_road": "市街地T字路/十字路交差点",
    "layer_2_infrastructure": "信号機なし、一時停止標識あり",
    "layer_3_temporary": "建物・駐車車両による視界遮蔽",
    "layer_4_objects": "2台の車両（自車と飛び出し車両）",
    "layer_5_environment": "晴天、昼間、乾燥路面",
    "layer_6_digital": "センサーベース認識（カメラ、LiDAR）"
  },
  "environment": {
    "location_type": "urban_intersection",
    "weather": "clear",
    "time_of_day": "noon",
    "road_condition": "dry",
    "features": ["occlusion", "buildings", "parked_vehicles"]
  },
  "actors": [
    {
      "id": "ego_vehicle",
      "type": "vehicle",
      "role": "自動運転予定車両",
      "is_autonomous_stack": true,
      "description": "交差点に直進で接近する主体車両"
    },
    {
      "id": "oncoming_vehicle",
      "type": "vehicle",
      "role": "飛び出し車両",
      "is_autonomous_stack": false,
      "description": "死角から突然交差点に進入する車両"
    }
  ],
  "scenario_type": "intersection_occlusion_hazard",
  "criticality": "high"
}
```

### 重要なフィールド

- **`natural_scenario_uuid`**: 元の自然言語シナリオへの参照（トレーサビリティ）
- **`pegasus_analysis_uuid`**: PEGASUS分析結果への参照
- **`pegasus_layers`**: 各Layerの要約（簡単な参照用）
- **`original_prompt`**: ユーザーの元の要件（検索用）

---

## 2. 論理シナリオ (Logical Scenario)

**ファイル名**: `data/scenarios/logical_{uuid}.json`

**目的**: パラメータ空間の定義。PEGASUS分析の`expected_values`から導出。各パラメータの分布、範囲、単位を記述。

**重要**: **分布情報のみを記録し、具体値は含まない**（トレーサビリティ確保）

**PEGASUS Layerからのパラメータマッピング**:
- **Layer 1 (Road)**: マップ選択、スポーン位置の基準
- **Layer 4 (Objects)**: 車両の初期速度、加速度、トリガー条件
- **Layer 5 (Environment)**: 天候、時間帯、路面状態
- **カメラ/センサー**: Layer 6から導出

```json
{
  "uuid": "logical-uuid",
  "parent_abstract_uuid": "abstract-uuid",
  "name": "交差点信号機遵守論理シナリオ",
  "description": "パラメータ空間を定義した論理シナリオ",
  "created_at": "2026-02-09T10:01:00Z",
  "parameter_space": {
    "ego_vehicle": {
      "initial_speed": {
        "type": "float",
        "unit": "km/h",
        "distribution": "uniform",
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
      },
      "offset_z": {
        "type": "float",
        "unit": "m",
        "distribution": "constant",
        "value": 3.0,
        "description": "車両上方のカメラ位置Z"
      }
    }
  }
}
```

### サポートする分布タイプ

| 分布タイプ | 必須フィールド | 説明 | 例 |
|-----------|---------------|------|-----|
| `constant` | `value` | 固定値 | `{"distribution": "constant", "value": 10.0}` |
| `uniform` | `min`, `max` | 一様分布 | `{"distribution": "uniform", "min": 0, "max": 100}` |
| `normal` | `mean`, `std` | 正規分布 | `{"distribution": "normal", "mean": 50, "std": 10}` |
| `choice` | `choices` | 選択肢 | `{"distribution": "choice", "choices": ["A", "B", "C"]}` |

---

## 3. パラメータセット (Parameter Set)

**ファイル名**: `data/scenarios/logical_{logical_uuid}_parameters.json`

**目的**: 論理シナリオからサンプリングされた具体的な値の集合。

**重要**: 1つの論理シナリオから**複数のパラメータセット**を生成可能。

```json
{
  "logical_uuid": "logical-uuid",
  "created_at": "2026-02-09T10:02:00Z",
  "parameters": {
    "param-uuid-1": {
      "created_at": "2026-02-09T10:02:00Z",
      "seed": 42,
      "sampled_values": {
        "ego_vehicle": {
          "initial_speed": 35.2,
          "distance_to_light": 45.7
        },
        "traffic_light": {
          "red_duration": 5.3
        },
        "environment": {
          "weather": "ClearNoon"
        },
        "camera": {
          "offset_x": -6.0,
          "offset_z": 3.0
        }
      },
      "carla_config": {
        "host": "localhost",
        "port": 2000,
        "map": "Town10HD_Opt",
        "vehicle_type": "vehicle.tesla.model3"
      },
      "output": {
        "rrd_file": "data/rerun/logical-uuid_param-uuid-1.rrd",
        "mp4_file": "data/videos/logical-uuid_param-uuid-1.mp4"
      }
    },
    "param-uuid-2": {
      "created_at": "2026-02-09T10:05:00Z",
      "seed": 123,
      "sampled_values": {
        "ego_vehicle": {
          "initial_speed": 22.8,
          "distance_to_light": 68.2
        },
        "traffic_light": {
          "red_duration": 3.7
        },
        "environment": {
          "weather": "WetNoon"
        },
        "camera": {
          "offset_x": -6.0,
          "offset_z": 3.0
        }
      },
      "carla_config": {
        "host": "localhost",
        "port": 2000,
        "map": "Town10HD_Opt",
        "vehicle_type": "vehicle.tesla.model3"
      },
      "output": {
        "rrd_file": "data/rerun/logical-uuid_param-uuid-2.rrd",
        "mp4_file": "data/videos/logical-uuid_param-uuid-2.mp4"
      }
    }
  }
}
```

### フィールド説明

- **`seed`** (オプション): 乱数シード（再現性確保）
- **`sampled_values`**: 論理シナリオのparameter_spaceからサンプリングされた具体値
- **`carla_config`**: CARLA実行時の設定
- **`output`**: 生成されるファイルのパス

---

## 4. 実行トレース (Execution Trace)

**ファイル名**: `data/scenarios/execution_{logical_uuid}_{parameter_uuid}.json`

**目的**: シナリオ実行の記録。抽象→論理→パラメータ→実装の完全なトレーサビリティ。

```json
{
  "execution_uuid": "execution-uuid",
  "logical_uuid": "logical-uuid",
  "abstract_uuid": "abstract-uuid",
  "parameter_uuid": "param-uuid-1",
  "name": "交差点信号機遵守シナリオ",
  "description": "パラメータセット param-uuid-1 での実行",
  "executed_at": "2026-02-09T10:10:00Z",
  "trace": {
    "abstract_scenario_file": "data/scenarios/abstract_abstract-uuid.json",
    "logical_scenario_file": "data/scenarios/logical_logical-uuid.json",
    "parameter_file": "data/scenarios/logical_logical-uuid_parameters.json",
    "parameter_uuid": "param-uuid-1",
    "implementation": {
      "python_file": "scenarios/logical-uuid.py",
      "command": "uv run python scenarios/logical-uuid.py --params data/scenarios/logical_logical-uuid_parameters.json --param-uuid param-uuid-1",
      "exit_code": 0,
      "final_status": "success"
    }
  },
  "outputs": {
    "rrd_file": "data/rerun/logical-uuid_param-uuid-1.rrd",
    "mp4_file": "data/videos/logical-uuid_param-uuid-1.mp4"
  }
}
```

---

## トレーサビリティの確保

### ファイル参照チェーン

```
execution_{L}_{P}.json
  ├─ logical_uuid → logical_{L}.json
  │   └─ parent_abstract_uuid → abstract_{A}.json
  │       └─ original_prompt (元の自然言語要件)
  ├─ parameter_uuid → logical_{L}_parameters.json["parameters"]["P"]
  │   └─ sampled_values (具体値)
  └─ implementation.python_file → scenarios/{L}.py
```

### 質問に答えられること

1. **「このシナリオはどんな要件から生まれたか？」**
   - execution → logical → abstract → original_prompt

2. **「このパラメータはどう決まったか？」**
   - execution → parameter_file → parameters[parameter_uuid].sampled_values
   - logical_scenario_file → parameter_space (分布定義)

3. **「この論理シナリオから何個のパラメータセットが生成されたか？」**
   - logical_{L}_parameters.json → parameters のキー数

4. **「同じ論理シナリオの他の実行結果は？」**
   - `execution_{L}_*.json` をグロブ検索

---

## Python実装での使用方法

### 論理シナリオとパラメータの作成

```python
from scripts.scenario_manager import ScenarioManager

manager = ScenarioManager()

# 1. 抽象シナリオを作成
abstract_uuid = manager.create_abstract_scenario(
    name="交差点信号機遵守シナリオ",
    description="市街地の交差点で信号機に従って停止・発進する",
    original_prompt="信号機が赤から青に変わったら車両が発進するシナリオ",
    environment={...},
    actors=[...],
    scenario_type="traffic_light_compliance"
)

# 2. 論理シナリオを作成（分布情報のみ）
logical_uuid = manager.create_logical_scenario(
    parent_abstract_uuid=abstract_uuid,
    name="交差点信号機遵守論理シナリオ",
    description="パラメータ空間を定義",
    parameter_space={
        "ego_vehicle": {
            "initial_speed": {
                "type": "float",
                "unit": "km/h",
                "distribution": "uniform",
                "min": 20.0,
                "max": 40.0
            }
        }
    }
)

# 3. パラメータをサンプリング（具体値を生成）
param_uuid_1 = manager.sample_parameters(
    logical_uuid=logical_uuid,
    carla_config={
        "host": "localhost",
        "port": 2000,
        "map": "Town10HD_Opt"
    },
    seed=42  # 再現性
)

# 4. 同じ論理シナリオから別のパラメータセットを生成
param_uuid_2 = manager.sample_parameters(
    logical_uuid=logical_uuid,
    carla_config={...},
    seed=123
)

# 5. パラメータを取得
params = manager.get_parameters(logical_uuid, param_uuid_1)
print(params['sampled_values']['ego_vehicle']['initial_speed'])  # 35.2

# 6. 実行トレースを記録
manager.create_execution_trace(
    logical_uuid=logical_uuid,
    parameter_uuid=param_uuid_1,
    python_file=f"scenarios/{logical_uuid}.py",
    command="uv run python ...",
    exit_code=0,
    status="success"
)
```

---

## ファイル命名規則

| 種類 | ファイル名 | 例 |
|------|-----------|-----|
| 抽象シナリオ | `abstract_{uuid}.json` | `abstract_a1b2c3d4.json` |
| 論理シナリオ | `logical_{uuid}.json` | `logical_550e8400.json` |
| パラメータ | `logical_{logical_uuid}_parameters.json` | `logical_550e8400_parameters.json` |
| 実行トレース | `execution_{logical_uuid}_{param_uuid}.json` | `execution_550e8400_p1.json` |
| Python実装 | `{logical_uuid}.py` | `550e8400.py` |
| 動画出力 | `{logical_uuid}_{param_uuid}.mp4` | `550e8400_p1.mp4` |
| RRD出力 | `{logical_uuid}_{param_uuid}.rrd` | `550e8400_p1.rrd` |

---

## まとめ

### 重要な設計原則

1. **論理シナリオには分布情報のみ**
   - 具体値は入れない
   - トレーサビリティを保つため

2. **パラメータファイルには具体値のみ**
   - サンプリングされた値
   - 1つの論理シナリオから複数セット生成可能

3. **UUID-based命名規則**
   - すべてのファイルがUUIDで追跡可能
   - ファイル名から関係性がわかる

4. **完全なトレーサビリティ**
   - 要件 → 抽象 → 論理 → パラメータ → 実行
   - 各ステップが明示的にリンク
