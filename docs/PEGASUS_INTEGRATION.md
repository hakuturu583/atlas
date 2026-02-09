---


# PEGASUS 6 Layer統合ガイド

ATLASプロジェクトにPEGASUS 6 Layerシナリオモデルを統合しました。

## 📚 概要

### PEGASUS とは

PEGASUS（**P**roject for **E**stablishing **G**enerally **A**ccepted Quality Criteria, Tools and Methods as well as **S**cenarios for the Safety Validation of Highly Automated Vehicles）は、自動運転車の安全性検証のための標準的なフレームワークです。

- **ISO 34501**: シナリオベーステストの標準
- **ISO 34502**: シナリオベース安全評価フレームワーク
- **6 Layer Model**: シナリオを6つのレイヤーで構造化

### なぜPEGASUSを使うのか？

1. **標準化**: 国際標準に準拠したシナリオ記述
2. **構造化**: 6つのレイヤーで明確に整理
3. **網羅性**: すべての要素を体系的にカバー
4. **再利用性**: 構造化されたシナリオは再利用しやすい
5. **トレーサビリティ**: 要件からシナリオまで追跡可能

## 🏗️ 6つのレイヤー

### Layer 1: Road-level（道路レベル）

道路の物理的特性を定義します。

**データモデル**: `RoadLevel`

**主要属性**:
- `road_type`: 高速道路、市街地、郊外、駐車場
- `topology`: 直線、カーブ、交差点、合流、分岐
- `num_lanes`: レーン数
- `lane_width`: レーン幅
- `curvature`: 曲率（カーブの場合）
- `elevation`: 勾配
- `friction_coefficient`: 路面摩擦係数

**例**:
```python
from app.models.pegasus_layers import RoadLevel, RoadType, RoadTopology

road = RoadLevel(
    road_type=RoadType.HIGHWAY,
    topology=RoadTopology.STRAIGHT,
    num_lanes=3,
    lane_width=3.5,
    friction_coefficient=0.8
)
```

### Layer 2: Traffic Infrastructure（交通インフラ）

信号機、標識、路面標示などを定義します。

**データモデル**: `TrafficInfrastructure`, `TrafficLight`, `TrafficSign`, `RoadMarking`

**主要要素**:
- 信号機（状態、サイクル時間）
- 交通標識（停止、速度制限、一方通行）
- 路面標示（車線、停止線、横断歩道）
- 障壁、ガードレール

**例**:
```python
from app.models.pegasus_layers import (
    TrafficInfrastructure,
    TrafficLight,
    TrafficLightState
)

infrastructure = TrafficInfrastructure(
    traffic_lights=[
        TrafficLight(
            id="tl_001",
            state=TrafficLightState.RED,
            red_duration=5.0,
            yellow_duration=3.0,
            green_duration=7.0
        )
    ]
)
```

### Layer 3: Temporary Manipulation（一時的な変更）

工事、事故、レーン閉鎖などの一時的な状況を定義します。

**データモデル**: `TemporaryManipulation`

**主要タイプ**:
- 工事
- 事故
- 道路封鎖
- レーン閉鎖
- 仮設標識

**例**:
```python
from app.models.pegasus_layers import (
    TemporaryManipulation,
    ManipulationType
)

manipulation = TemporaryManipulation(
    manipulation_type=ManipulationType.CONSTRUCTION,
    description="右車線工事中",
    affected_lanes=[2]
)
```

### Layer 4: Moving Objects（移動物体）

車両、歩行者、自転車などの移動物体を定義します。

**データモデル**: `MovingObject`, `InitialState`, `ManeuverType`

**主要属性**:
- `object_type`: 車両、歩行者、自転車
- `initial_state`: 位置、速度、加速度
- `maneuver`: レーン追従、車線変更、右左折
- `is_autonomous`: 自動運転車両かどうか

**マニューバータイプ**:
- `FOLLOW_LANE`: レーン追従
- `LANE_CHANGE_LEFT/RIGHT`: 車線変更
- `TURN_LEFT/RIGHT`: 右左折
- `OVERTAKE`: 追い越し
- `MERGE`: 合流
- `STOP`: 停止
- `ACCELERATION/DECELERATION`: 加減速

**例**:
```python
from app.models.pegasus_layers import (
    MovingObject,
    ObjectType,
    InitialState,
    ManeuverType
)

ego_vehicle = MovingObject(
    id="ego_vehicle",
    object_type=ObjectType.VEHICLE,
    initial_state=InitialState(
        position=(100.0, 0.0, 0.5),
        velocity=27.8,  # 100 km/h
        heading=0.0
    ),
    maneuver=ManeuverType.FOLLOW_LANE,
    is_autonomous=True
)
```

### Layer 5: Environment Conditions（環境条件）

天候、時間帯、路面状態などの環境を定義します。

**データモデル**: `EnvironmentConditions`

**主要属性**:
- `weather`: 晴れ、雨、雪、霧
- `time_of_day`: 朝、昼、夕方、夜
- `road_surface`: 乾燥、湿潤、凍結
- `visibility`: 視程
- `temperature`: 気温

**例**:
```python
from app.models.pegasus_layers import (
    EnvironmentConditions,
    WeatherCondition,
    TimeOfDay,
    RoadSurface
)

environment = EnvironmentConditions(
    weather=WeatherCondition.RAIN,
    time_of_day=TimeOfDay.NIGHT,
    road_surface=RoadSurface.WET,
    visibility=500.0,  # 500m（雨天）
    temperature=15.0
)
```

### Layer 6: Digital Information（デジタル情報）

V2X通信、HDマップ、センサー設定などを定義します。

**データモデル**: `DigitalInformation`, `SensorConfiguration`, `HDMapInfo`

**主要要素**:
- V2X通信（V2V, V2I, V2P）
- HDマップ情報
- センサー設定（カメラ、LiDAR、レーダー）
- 自己位置推定精度

**例**:
```python
from app.models.pegasus_layers import (
    DigitalInformation,
    SensorConfiguration
)

digital = DigitalInformation(
    v2x_enabled=True,
    sensors=[
        SensorConfiguration(
            sensor_type="camera",
            range=100.0,
            fov=90.0,
            resolution=(1920, 1080),
            frequency=30.0
        ),
        SensorConfiguration(
            sensor_type="lidar",
            range=200.0,
            fov=360.0,
            frequency=10.0
        )
    ],
    localization_accuracy=0.1
)
```

## 🚀 使用方法

### 1. PEGASUS分析スキルの使用

```
ユーザー: "高速道路で前方車両が急ブレーキをかけるシナリオを分析して"

Claude: pegasus-analyzerスキルを起動し、6 Layerに基づいて分析します。

【分析結果】
Layer 1: highway, straight, 3 lanes
Layer 2: speed_limit sign
Layer 3: なし
Layer 4: ego_vehicle (autonomous), lead_vehicle
Layer 5: clear, afternoon, dry
Layer 6: camera, radar, lidar

【パラメータ空間】
ego_vehicle.initial_speed: 80-120 km/h
lead_vehicle.deceleration_rate: -8 to -12 m/s^2
...
```

### 2. AbstractScenarioへの統合

```python
from app.models.scenario_hierarchy import AbstractScenario
from app.models.pegasus_layers import (
    RoadLevel,
    TrafficInfrastructure,
    MovingObject,
    EnvironmentConditions
)

abstract = AbstractScenario(
    uuid="...",
    name="高速道路急ブレーキシナリオ",
    description="...",
    original_prompt="...",
    # 従来のフィールド
    environment=...,
    actors=...,
    maneuvers=...,
    # PEGASUS統合
    pegasus_layer1_road=RoadLevel(...),
    pegasus_layer2_infrastructure=TrafficInfrastructure(...),
    pegasus_layer4_objects=[ego_vehicle, lead_vehicle],
    pegasus_layer5_environment=EnvironmentConditions(...),
    pegasus_criticality_level=4
)
```

### 3. シナリオ生成ワークフロー

```
Phase 0: PEGASUS分析
  ↓
  ├─ Layer 1: 道路タイプ、トポロジー
  ├─ Layer 2: インフラ
  ├─ Layer 3: 一時的変更
  ├─ Layer 4: 移動物体
  ├─ Layer 5: 環境条件
  └─ Layer 6: デジタル情報
  ↓
Phase 1: 抽象シナリオ生成（PEGASUS情報を含む）
  ↓
Phase 2: 論理シナリオ生成（パラメータ空間）
  ↓
Phase 3: Python実装
  ↓
Phase 4: 実行
```

## 📊 Criticalityレベル

シナリオの危険度を1-5で評価します。

| Level | 説明 | 例 |
|-------|------|-----|
| **1** | 基本シナリオ | 直線走行 |
| **2** | 低リスク | 通常の車線変更 |
| **3** | 中リスク | 合流、右左折 |
| **4** | 高リスク | 急ブレーキ、カットイン |
| **5** | 極めて高リスク | 衝突回避、緊急回避 |

## 🔧 実装例

### 完全なPEGASUSシナリオ

```python
from app.models.pegasus_layers import PegasusScenario

scenario = PegasusScenario(
    scenario_id="highway_emergency_brake",
    name="高速道路急ブレーキシナリオ",
    description="高速道路で前方車両が急ブレーキをかける",
    layer1_road=RoadLevel(
        road_type=RoadType.HIGHWAY,
        topology=RoadTopology.STRAIGHT,
        num_lanes=3,
        lane_width=3.5
    ),
    layer2_infrastructure=TrafficInfrastructure(
        traffic_signs=[
            TrafficSign(
                id="speed_limit",
                sign_type=TrafficSignType.SPEED_LIMIT,
                value="100"
            )
        ]
    ),
    layer4_objects=[
        MovingObject(
            id="ego_vehicle",
            object_type=ObjectType.VEHICLE,
            initial_state=InitialState(
                position=(0.0, 0.0, 0.5),
                velocity=27.8  # 100 km/h
            ),
            maneuver=ManeuverType.FOLLOW_LANE,
            is_autonomous=True
        ),
        MovingObject(
            id="lead_vehicle",
            object_type=ObjectType.VEHICLE,
            initial_state=InitialState(
                position=(50.0, 0.0, 0.5),
                velocity=27.8
            ),
            maneuver=ManeuverType.DECELERATION,
            target_velocity=0.0
        )
    ],
    layer5_environment=EnvironmentConditions(
        weather=WeatherCondition.CLEAR,
        time_of_day=TimeOfDay.AFTERNOON,
        road_surface=RoadSurface.DRY
    ),
    layer6_digital=DigitalInformation(
        v2x_enabled=False,
        sensors=[
            SensorConfiguration(
                sensor_type="camera",
                range=100.0
            )
        ]
    ),
    criticality_level=4,
    tags=["highway", "emergency_brake", "high_risk"]
)

# 辞書形式に変換
scenario_dict = scenario.to_dict()
```

## 📚 参考資料

### ISO標準
- **ISO 34501**: Road vehicles - Test scenarios for automated driving systems
- **ISO 34502**: Road vehicles - Test scenarios for automated driving systems - Scenario based safety evaluation framework

### 論文・資料
- PEGASUS Method: An Overview (2019)
- PEGASUS Project Final Report
- OpenSCENARIO format specification

### 関連ツール
- **OpenSCENARIO**: シナリオ記述言語
- **OpenDRIVE**: 道路ネットワーク記述言語

## 🎯 今後の拡張

1. **Layer 3のサポート強化**
   - 工事、事故などの動的シナリオ

2. **Layer 6のV2X統合**
   - V2V, V2I通信のシミュレーション

3. **OpenSCENARIOエクスポート**
   - PEGASUSシナリオをOpenSCENARIO形式で出力

4. **自動パラメータ抽出**
   - PEGASUS分析からパラメータ空間を自動生成

5. **シナリオカタログ**
   - PEGASUSベースのシナリオライブラリ
