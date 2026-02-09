---
name: scenario-writer
description: This skill should be used when the user asks to "create scenario", "generate CARLA scenario", "build new scenario", "シナリオ生成", "シナリオ作成", "新しいシナリオ", or provides natural language scenario requirements. Automates full workflow from requirements analysis through Python implementation and execution using PEGASUS 6 Layer framework.
---

# Scenario Writer Agent

**役割**: ユーザーの自然言語要件からCARLAシミュレーション用のシナリオを生成し、Python実装、実行、デバッグまでを自動化する統合エージェント。

## 🆕 PEGASUS 6 Layer統合

**重要**: シナリオ生成前に、必ず`pegasus-analyzer`スキルを使ってPEGASUS 6 Layerに基づいた要件分析を行うこと。

### ワークフロー

1. **Phase 0: PEGASUS分析** 🆕
   - ユーザー要件を受け取る
   - `pegasus-analyzer`スキルで6 Layerに基づいて分析
   - 構造化された情報を抽出（道路、インフラ、移動物体、環境、デジタル情報）
   - Criticalityレベルを評価

2. **Phase 1: 抽象シナリオ生成**
   - PEGASUS分析結果を基に抽象シナリオを生成
   - 6 Layerの情報をAbstractScenarioに統合

3. **Phase 2: 論理シナリオ生成**
   - パラメータ空間を定義
   - PEGASUS Layer 4, 5の情報からパラメータを抽出

4. **Phase 3-5: 実装・実行・トレース保存**
   - 従来通り

### PEGASUS分析の利用

PEGASUS分析で得られた情報は、以下のように活用されます：

- **Layer 1 (Road)**: CARLAマップ選択、スポーン位置の決定
- **Layer 2 (Infrastructure)**: 信号機、標識の配置（現在は限定的サポート）
- **Layer 3 (Manipulation)**: 特殊条件の実装（将来対応）
- **Layer 4 (Objects)**: 車両・歩行者の初期状態、マニューバー定義
- **Layer 5 (Environment)**: 天候、時間帯、路面状態の設定
- **Layer 6 (Digital)**: センサー設定、V2X通信（将来対応）

## 重要な制約事項

1. **すべての車両はCARLAのNPC**
   - 現時点では外部の自動運転スタックは統合されていない
   - 1台は「将来自動運転スタックを統合予定」のNPCとしてマーク（`is_autonomous_stack: true`）

2. **同期モードで実行（オプション）**
   - 決定性を担保する場合、CARLAを同期モードで動作させる
   - 固定タイムステップ（`fixed_delta_seconds=0.05`）で20Hz実行

3. **カメラ配置（オプション）**
   - 自動運転スタック予定NPCの運転席付近にカメラを配置可能
   - カメラ映像を記録する場合はOpenCVを使用

4. **ファイル命名規則**
   - 各シナリオは論理シナリオのUUIDで識別
   - Pythonファイル: `scenarios/{logical_uuid}.py`
   - パラメータファイル: `data/scenarios/params_{parameter_uuid}.json`
   - 出力ファイル: `{logical_uuid}_{parameter_uuid}.rrd`、`{logical_uuid}_{parameter_uuid}.mp4`
   - **理由**: 1つの論理シナリオを異なるパラメータで複数回実行可能

5. **Python実装**
   - CARLA Python APIを使用
   - ビルド不要、直接実行可能
   - `uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{parameter_uuid}.json`で実行

6. **🚨 CRITICAL: Traffic Managerで車両制御**
   - **すべての車両は必ずCARLA Traffic Managerで制御すること**
   - 単純な`vehicle.set_autopilot(True)`ではなく、明示的にTraffic Managerを取得・設定する
   - Traffic Managerの同期モードを有効化（`traffic_manager.set_synchronous_mode(True)`）
   - 信号機認識を100%守る設定（`ignore_lights_percentage(vehicle, 0)`）

   **実装例**:
   ```python
   # Traffic Managerを取得（ポート: CARLA_PORT + 6000）
   traffic_manager = client.get_trafficmanager(carla_config['port'] + 6000)
   traffic_manager.set_synchronous_mode(True)

   # Traffic Managerで車両を制御
   vehicle.set_autopilot(True, traffic_manager.get_port())

   # Traffic Manager設定
   traffic_manager.ignore_lights_percentage(vehicle, 0)  # 信号を100%守る
   traffic_manager.distance_to_leading_vehicle(vehicle, 2.0)  # 前方車両との距離
   traffic_manager.vehicle_percentage_speed_difference(vehicle, -20)  # 制限速度の20%減
   ```

   **理由**: Traffic Managerを使うことで、信号機認識、レーン追従、他車両との協調動作が確実に機能する

## 🚨 CARLA環境の制約

### 利用可能なマップ

現在のCARLA環境で利用可能なマップ：
- `Town10HD_Opt` （デフォルト推奨）
- `NishishinjukuMap`

**重要**: パラメータで指定するマップは必ず現在CARLAで読み込まれているマップと一致させること。

### 利用可能な車両

Town10HD_Optで利用可能な車両（2026年2月時点）：
- `vehicle.taxi.ford` （推奨）
- `vehicle.dodgecop.charger`
- `vehicle.ue4.chevrolet.impala`
- `vehicle.ue4.mercedes.ccc`
- `vehicle.ue4.ford.mustang`
- `vehicle.ue4.bmw.grantourer`
- `vehicle.dodge.charger`
- `vehicle.nissan.patrol`
- `vehicle.mini.cooper`
- `vehicle.lincoln.mkz`

その他17台の車両が利用可能。詳細は `uv run python scripts/list_vehicles.py` で確認。

### スペクターカメラと動画記録

**必須要件**: 全てのシナリオで以下を実装すること：

1. **スペクターカメラの配置**
   - ego車両の後方上に配置
   - オフセット: `(-5.0, 0.0, 2.5)` メートル
   - Pitch: `-15°` （やや下向き）

2. **動画記録**
   - imageioを使用
   - フォーマット: MP4 (H.264)
   - 解像度: 1280x720
   - フレームレート: 20 FPS
   - 出力: `data/videos/{{logical_uuid}}_{{parameter_uuid}}.mp4`

## ⚠️ 重要: Pythonスクリプトの使用

**UUID生成とJSON管理は`scripts/scenario_manager.py`を使用してください**。

このスキルの各Phaseは、以下のPythonスクリプトを使用して自動化されます：

```python
from scripts.scenario_manager import ScenarioManager

manager = ScenarioManager()

# Phase 1: 抽象シナリオ作成
abstract_uuid = manager.create_abstract_scenario(...)

# Phase 2: 論理シナリオ作成
logical_uuid = manager.create_logical_scenario(parent_abstract_uuid=abstract_uuid, ...)

# Phase 3: パラメータ作成
parameter_uuid = manager.create_parameters(logical_uuid=logical_uuid, ...)

# Phase 4実行後: 実行トレース作成
manager.create_execution_trace(logical_uuid=logical_uuid, parameter_uuid=parameter_uuid, ...)
```

詳細は`scripts/README_scenario_manager.md`を参照してください。

---

## ワークフロー

### Phase 1: 要件分析と抽象シナリオ生成

**目的**: ユーザーの自然言語要件を構造化された抽象シナリオに変換

**手順**:

1. **要件の受け取り**
   - ユーザーからの自然言語要件を確認
   - 例: "高速道路で前方車両を追従するシナリオ"

2. **不明点の確認**
   - `AskUserQuestion`ツールを使用して不明点を質問
   - 質問例:
     - 車両台数は？（デフォルト: 2台）
     - 追従距離は？（デフォルト: 20m）
     - シナリオの継続時間は？（デフォルト: 10秒）

3. **抽象シナリオの生成**
   - **UUID生成**: `uuid.uuid4()`で一意なIDを生成
   - MCPツール`generate_abstract_scenario`を呼び出し
   - 生成内容:
     - `uuid`: 抽象シナリオの一意なID
     - `name`: シナリオの短い名前
     - `description`: シナリオの概要
     - `original_prompt`: ユーザーの元の要件
     - `actors`: アクターのリスト（最低1台は`is_autonomous_stack: true`）
     - `maneuvers`: 操作・動作の列挙
     - `created_at`: 生成日時（ISO 8601形式）

4. **JSONファイルに保存**
   - `data/scenarios/abstract_{uuid}.json`として保存
   - トレーサビリティのため永続化

5. **ユーザー確認**
   - 生成された抽象シナリオをユーザーに提示
   - 承認を得る

**出力例**:
```json
{
  "uuid": "a1b2c3d4-e5f6-4789-a012-3456789abcde",
  "name": "highway_follow",
  "description": "高速道路で前方車両を20m間隔で追従するシナリオ",
  "original_prompt": "高速道路で前方車両を追従するシナリオ",
  "created_at": "2026-02-06T23:50:00Z",
  "actors": [
    {
      "id": "ego_vehicle",
      "role": "自動運転スタック予定",
      "type": "vehicle",
      "is_autonomous_stack": true
    },
    {
      "id": "lead_vehicle",
      "role": "前方車両",
      "type": "vehicle",
      "is_autonomous_stack": false
    }
  ],
  "maneuvers": [
    {
      "actor": "lead_vehicle",
      "action": "一定速度で走行",
      "duration": "10s"
    },
    {
      "actor": "ego_vehicle",
      "action": "前方車両を追従",
      "duration": "10s",
      "conditions": ["距離を20m維持"]
    }
  ]
}
```

**ファイルパス**: `data/scenarios/abstract_a1b2c3d4-e5f6-4789-a012-3456789abcde.json`

### Phase 2: 論理シナリオ生成

**目的**: 抽象シナリオからOpenDRIVE非依存の論理シナリオを生成

**手順**:

1. **論理シナリオの生成**
   - **UUID生成**: `uuid.uuid4()`で新しいUUIDを生成（論理シナリオ用）
   - MCPツール`generate_logical_scenario`を呼び出し
   - OpenDRIVE非依存の記述を作成:
     - `uuid`: 論理シナリオの一意なID
     - `parent_abstract_uuid`: 親の抽象シナリオUUID（**トレーサビリティ**）
     - `name`: シナリオ名（抽象シナリオから継承）
     - `description`: 詳細な説明
     - `map_requirements`: 地図の要件（道路タイプ、レーン数など）
     - `initial_conditions`: 初期状態（symbolic location）
     - `events`: イベント列（時刻とアクション）
     - `created_at`: 生成日時

2. **JSONファイルに保存**
   - `data/scenarios/logical_{uuid}.json`として保存
   - `parent_abstract_uuid`により親子関係を保持

3. **ユーザー確認**
   - 生成された論理シナリオをユーザーに提示
   - 承認を得る

**出力例**:
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "parent_abstract_uuid": "a1b2c3d4-e5f6-4789-a012-3456789abcde",
  "name": "highway_follow",
  "description": "高速道路で前方車両を20m間隔で追従する論理シナリオ",
  "created_at": "2026-02-06T23:51:00Z",
  "map_requirements": {
    "road_type": "highway",
    "lanes": 3,
    "length_min": 500
  },
  "initial_conditions": {
    "ego_vehicle": {
      "location": "highway_lane_2",
      "speed": 50.0,
      "distance_behind_lead": 20.0
    },
    "lead_vehicle": {
      "location": "highway_lane_2_front",
      "speed": 80.0
    }
  },
  "events": [
    {
      "time": 0.0,
      "type": "start_scenario"
    },
    {
      "time": 0.0,
      "type": "lead_vehicle_set_constant_speed",
      "speed": 80.0
    },
    {
      "time": 0.0,
      "type": "ego_vehicle_follow_lead",
      "target_distance": 20.0
    },
    {
      "time": 10.0,
      "type": "end_scenario"
    }
  ]
}
```

**ファイルパス**: `data/scenarios/logical_550e8400-e29b-41d4-a716-446655440000.json`

**トレーサビリティ**:
- `parent_abstract_uuid`を読めば、どの抽象シナリオから生成されたかがわかる
- `data/scenarios/abstract_a1b2c3d4-e5f6-4789-a012-3456789abcde.json`を参照可能

### Phase 3: Python実装生成と具体パラメータ作成

**目的**: 論理シナリオからCARLA Python実装と具体的なパラメータファイルを生成

**手順**:

1. **Python実装の生成**
   - 論理シナリオからPythonコードを直接生成
   - **ファイル名**: 論理シナリオの`uuid`を使用
   - `scenarios/{logical_uuid}.py`として保存
   - ファイル内に`logical_uuid`をコメントで記録
   - 要件:
     - CARLA Python APIを使用
     - **🚨 CRITICAL: `opendrive_utils`ライブラリを必ず使用**（詳細は下記）
     - コマンドライン引数 `--params` でパラメータファイルを受け取る
     - 同期モード設定（オプション）
     - カメラ記録（オプション、imageio使用）
     - Rerun統合（オプション）
     - try-finally でクリーンアップ

---

## 🚨 CRITICAL: opendrive_utilsライブラリの使用

**重要**: シナリオ実装では、必ず`opendrive_utils`ライブラリを使用してスポーン位置を計算してください。

### ❌ 禁止事項

**`carla.Map.get_spawn_points()`を使用しないこと**

理由:
- 事前定義されたスポーン位置はランダムで、狙った位置に配置できない
- シナリオの再現性が保証されない
- レーン座標や信号機との位置関係を正確に制御できない

```python
# ❌ BAD: Spawn Pointsを使用（禁止）
spawn_points = world.get_map().get_spawn_points()
transform = spawn_points[0]  # ランダムな位置
vehicle = world.spawn_actor(blueprint, transform)
```

### ✅ 必須: opendrive_utilsの使用

**すべてのスポーン位置は`opendrive_utils`で計算すること**

```python
# ✅ GOOD: opendrive_utilsを使用
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

od_map = OpenDriveMap(world)
spawn_helper = SpawnHelper(od_map)

# レーン座標から精密にスポーン
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)
vehicle = world.spawn_actor(blueprint, transform)
```

### 基本的な使い方

#### 1. 初期化

```python
import carla
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

# CARLA接続
client = carla.Client('localhost', 2000)
world = client.get_world()

# opendrive_utils初期化
od_map = OpenDriveMap(world)
spawn_helper = SpawnHelper(od_map)
```

#### 2. レーン座標からスポーン

```python
# レーン座標を指定
lane_coord = LaneCoord(
    road_id=10,      # 道路ID
    lane_id=-1,      # レーンID（負: 右側、正: 左側）
    s=50.0,          # 道路の始点からの距離（メートル）
    offset=0.0       # レーン中心からのオフセット
)

# Transformを計算
transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)

# 車両をスポーン
blueprint = world.get_blueprint_library().find('vehicle.tesla.model3')
vehicle = world.spawn_actor(blueprint, transform)
```

#### 3. 指定距離前方にスポーン

```python
# 基準位置から30m前方にスポーン
start_lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)

forward_transform = spawn_helper.get_spawn_transform_at_distance(
    start_lane_coord,
    distance=30.0  # 30m前方
)

vehicle2 = world.spawn_actor(blueprint, forward_transform)
```

#### 4. レーン上に複数車両を配置

```python
# レーン上に5台を20m間隔で配置
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)

transforms = spawn_helper.get_spawn_points_along_lane(
    lane_coord,
    num_points=5,
    spacing=20.0  # 20m間隔
)

for transform in transforms:
    vehicle = world.spawn_actor(blueprint, transform)
    vehicles.append(vehicle)
```

### 高度な機能: 信号機・交差点を考慮したスポーン

#### 1. 信号機の手前にスポーン

```python
from opendrive_utils import AdvancedFeatures

advanced = AdvancedFeatures(od_map)

# 信号機を検索
signals = advanced.get_traffic_signals()
if signals:
    signal = signals[0]

    # 信号機の10m手前にスポーン
    transform = advanced.get_spawn_before_signal(
        signal,
        lane_id=-1,           # 右側レーン
        distance_before=10.0  # 10m手前
    )

    vehicle = world.spawn_actor(blueprint, transform)
```

#### 2. 最も近い信号機を検索してスポーン

```python
# 現在のレーン座標から最も近い信号機を検索
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
nearest_signal = advanced.get_nearest_signal(
    lane_coord,
    max_distance=100.0  # 最大100m先まで検索
)

if nearest_signal:
    # 信号機の手前にスポーン
    transform = advanced.get_spawn_before_signal(
        nearest_signal,
        lane_id=-1,
        distance_before=15.0
    )
    vehicle = world.spawn_actor(blueprint, transform)
```

#### 3. 交差点の流入点にスポーン

```python
# 交差点情報を取得
junctions = advanced.get_junctions()
junction = list(junctions.values())[0]

# 交差点への流入点
entry_transforms = advanced.get_junction_entry_points(
    junction.id,
    incoming_road_id=10
)

for transform in entry_transforms[:3]:  # 最初の3つの流入点
    vehicle = world.spawn_actor(blueprint, transform)
    vehicles.append(vehicle)
```

#### 4. 停止線の手前にスポーン

```python
# 停止線を取得
stop_lines = advanced.get_stop_lines()

for stop_line in stop_lines[:5]:
    # 停止線の2m手前にスポーン
    transform = advanced.get_spawn_at_stop_line(
        stop_line,
        offset_before=2.0  # 2m手前
    )

    vehicle = world.spawn_actor(blueprint, transform)
    vehicles.append(vehicle)
```

### 実装例: 信号機待ちシナリオ

```python
#!/usr/bin/env python3
"""
信号機待ちシナリオ

Logical Scenario UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
"""
import carla
import time
import sys
import json
import argparse
from opendrive_utils import (
    OpenDriveMap,
    SpawnHelper,
    AdvancedFeatures,
    LaneCoord,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--params', required=True)
    args = parser.parse_args()

    with open(args.params) as f:
        params = json.load(f)

    # CARLA接続
    client = carla.Client(params['carla']['host'], params['carla']['port'])
    client.set_timeout(10.0)
    world = client.get_world()

    # opendrive_utils初期化
    od_map = OpenDriveMap(world)
    spawn_helper = SpawnHelper(od_map)
    advanced = AdvancedFeatures(od_map)

    actors = []
    try:
        blueprint_library = world.get_blueprint_library()
        vehicle_bp = blueprint_library.find('vehicle.tesla.model3')

        # 信号機を検索
        signals = advanced.get_traffic_signals()
        if not signals:
            print("信号機が見つかりません", file=sys.stderr)
            return 1

        # パラメータから道路情報を取得
        target_road_id = params['scenario']['road_id']
        target_lane_id = params['scenario']['lane_id']

        # その道路上の信号機を検索
        road_signals = [s for s in signals if s.road_id == target_road_id]
        if not road_signals:
            print(f"Road {target_road_id} に信号機が見つかりません", file=sys.stderr)
            return 1

        signal = road_signals[0]
        print(f"信号機 {signal.id} を使用: Road {signal.road_id}, s={signal.s:.2f}m")

        # Ego車両: 信号機の10m手前にスポーン
        ego_transform = advanced.get_spawn_before_signal(
            signal,
            lane_id=target_lane_id,
            distance_before=10.0
        )
        ego_vehicle = world.spawn_actor(vehicle_bp, ego_transform)
        actors.append(ego_vehicle)
        print(f"✓ Ego車両をスポーン: 信号機の10m手前")

        # NPC車両1: 信号機の30m手前にスポーン
        npc_transform_1 = advanced.get_spawn_before_signal(
            signal,
            lane_id=target_lane_id,
            distance_before=30.0
        )
        npc1 = world.spawn_actor(vehicle_bp, npc_transform_1)
        actors.append(npc1)
        print(f"✓ NPC1をスポーン: 信号機の30m手前")

        # NPC車両2: 信号機の50m手前にスポーン
        npc_transform_2 = advanced.get_spawn_before_signal(
            signal,
            lane_id=target_lane_id,
            distance_before=50.0
        )
        npc2 = world.spawn_actor(vehicle_bp, npc_transform_2)
        actors.append(npc2)
        print(f"✓ NPC2をスポーン: 信号機の50m手前")

        # Traffic Managerで制御
        traffic_manager = client.get_trafficmanager(params['carla']['port'] + 6000)
        traffic_manager.set_synchronous_mode(True)

        for vehicle in actors:
            vehicle.set_autopilot(True, traffic_manager.get_port())
            traffic_manager.ignore_lights_percentage(vehicle, 0)  # 信号を100%守る

        # シナリオ実行
        duration = params['scenario']['duration']
        steps = int(duration / 0.05)

        for i in range(steps):
            world.tick()
            time.sleep(0.05)

            if i % 20 == 0:  # 1秒ごとに出力
                ego_loc = ego_vehicle.get_location()
                signal_transform = advanced.get_signal_transform(signal)
                distance_to_signal = ego_loc.distance(signal_transform.location)
                print(f"t={i*0.05:.2f}s: 信号機まで {distance_to_signal:.2f}m")

        print("✓ シナリオ完了")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        for actor in actors:
            actor.destroy()


if __name__ == "__main__":
    sys.exit(main())
```

### パラメータファイルの構造

opendrive_utilsを使う場合、パラメータファイルには以下を含めます:

```json
{
  "parameter_uuid": "abc12345-...",
  "logical_uuid": "550e8400-...",
  "carla": {
    "host": "localhost",
    "port": 2000,
    "map": "Town10HD_Opt"
  },
  "scenario": {
    "road_id": 10,
    "lane_id": -1,
    "duration": 20.0
  },
  "output": {
    "rrd_file": "data/rerun/550e8400-..._abc12345-....rrd",
    "mp4_file": "data/videos/550e8400-..._abc12345-....mp4"
  }
}
```

**重要**: スポーン位置の座標（x, y, z, yaw）は**含めない**。代わりに`road_id`、`lane_id`、`s`（距離）を指定し、実行時に`opendrive_utils`で計算します。

### まとめ

- ✅ **必ず`opendrive_utils`を使用してスポーン位置を計算**
- ❌ **`carla.Map.get_spawn_points()`は使用禁止**
- ✅ **レーン座標（road_id, lane_id, s）から精密に配置**
- ✅ **信号機・交差点・停止線を考慮したスポーンが可能**
- ✅ **シナリオの再現性と精度が保証される**

---

2. **具体パラメータの生成**
   - **パラメータUUID生成**: `uuid.uuid4()`で新しいUUIDを生成
   - 論理シナリオから具体的なパラメータを生成:
     - CARLAマップ名（例: Town04）
     - 車両スポーン位置（x, y, z, yaw）
     - 初期速度
     - シミュレーション時間
     - カメラ設定
     - 出力ファイルパス: `{logical_uuid}_{parameter_uuid}.rrd/mp4`
   - `data/scenarios/params_{parameter_uuid}.json`として保存

3. **生成コードの確認**
   - 以下が含まれていることを検証:
     - ✅ `argparse`でパラメータファイルを受け取る
     - ✅ JSONファイルからパラメータをロード
     - ✅ `carla.Client`で接続
     - ✅ アクターのスポーン
     - ✅ 車両制御ロジック
     - ✅ finallyブロックでクリーンアップ

4. **パラメータファイル例** (`data/scenarios/params_abc12345-6789-0123-4567-890abcdef012.json`):
   ```json
   {
     "parameter_uuid": "abc12345-6789-0123-4567-890abcdef012",
     "logical_uuid": "550e8400-e29b-41d4-a716-446655440000",
     "carla": {
       "host": "localhost",
       "port": 2000,
       "map": "Town04"
     },
     "vehicles": {
       "ego": {
         "spawn": {"x": 100.0, "y": 200.0, "z": 0.3, "yaw": 0.0},
         "initial_speed": 50.0
       },
       "lead": {
         "spawn": {"x": 120.0, "y": 200.0, "z": 0.3, "yaw": 0.0},
         "initial_speed": 80.0
       }
     },
     "scenario": {
       "duration": 10.0,
       "target_distance": 20.0
     },
     "output": {
       "rrd_file": "data/rerun/550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.rrd",
       "mp4_file": "data/videos/550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.mp4"
     }
   }
   ```

5. **実装例** (`scenarios/550e8400-e29b-41d4-a716-446655440000.py`):
   ```python
   #!/usr/bin/env python3
   """
   高速道路追従シナリオ

   Logical Scenario UUID: 550e8400-e29b-41d4-a716-446655440000
   Parent Abstract Scenario UUID: a1b2c3d4-e5f6-4789-a012-3456789abcde
   """
   import carla
   import time
   import math
   import sys
   import json
   import argparse


   def get_distance(v1, v2):
       """Calculate distance between two vehicles"""
       l1 = v1.get_location()
       l2 = v2.get_location()
       return math.sqrt((l1.x - l2.x)**2 + (l1.y - l2.y)**2)


   def main():
       # コマンドライン引数からパラメータファイルを読み込み
       parser = argparse.ArgumentParser()
       parser.add_argument('--params', required=True, help='Path to parameter JSON file')
       args = parser.parse_args()

       with open(args.params) as f:
           params = json.load(f)

       # CARLA接続
       client = carla.Client(params['carla']['host'], params['carla']['port'])
       client.set_timeout(10.0)
       world = client.get_world()

       actors = []
       try:
           blueprint_library = world.get_blueprint_library()
           vehicle_bp = blueprint_library.filter('vehicle.*')[0]

           # 先行車両をスポーン
           lead_spawn = params['vehicles']['lead']['spawn']
           lead_transform = carla.Transform(
               carla.Location(x=lead_spawn['x'], y=lead_spawn['y'], z=lead_spawn['z']),
               carla.Rotation(yaw=lead_spawn['yaw'])
           )
           lead_vehicle = world.spawn_actor(vehicle_bp, lead_transform)
           actors.append(lead_vehicle)

           # 追従車両をスポーン
           ego_spawn = params['vehicles']['ego']['spawn']
           ego_transform = carla.Transform(
               carla.Location(x=ego_spawn['x'], y=ego_spawn['y'], z=ego_spawn['z']),
               carla.Rotation(yaw=ego_spawn['yaw'])
           )
           follow_vehicle = world.spawn_actor(vehicle_bp, ego_transform)
           actors.append(follow_vehicle)

           # シナリオ実行
           duration = params['scenario']['duration']
           target_distance = params['scenario']['target_distance']
           steps = int(duration / 0.05)

           for i in range(steps):
               # 先行車両は一定速度
               lead_control = carla.VehicleControl(throttle=0.5)
               lead_vehicle.apply_control(lead_control)

               # 追従車両は距離に応じて速度調整
               distance = get_distance(lead_vehicle, follow_vehicle)
               throttle = 0.6 if distance > target_distance else 0.3
               follow_control = carla.VehicleControl(throttle=throttle)
               follow_vehicle.apply_control(follow_control)

               print(f"t={i*0.05:.2f}: distance={distance:.2f}m")
               time.sleep(0.05)

           print(f"✓ 出力: {params['output']['rrd_file']}")
           print(f"✓ 出力: {params['output']['mp4_file']}")
           return 0

       except Exception as e:
           print(f"Error: {e}", file=sys.stderr)
           return 1

       finally:
           for actor in actors:
               actor.destroy()


   if __name__ == "__main__":
       sys.exit(main())
   ```

### Phase 4: 実行・デバッグ

**目的**: Pythonコードを実行し、エラーを自動修正

**手順**:

1. **Python実行**
   - Bashツールで実行: `uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{parameter_uuid}.json`
   - CARLAサーバーが起動しているか事前確認
   - 出力ファイル: `data/rerun/{logical_uuid}_{parameter_uuid}.rrd`、`data/videos/{logical_uuid}_{parameter_uuid}.mp4`

2. **エラー検出と修正**
   - エラーの種類に応じた修正を適用:
     - `RuntimeError: time-out`: CARLA未起動 → ユーザーに通知
     - `RuntimeError: failed to spawn`: スポーンポイント不足 → 複数試行
     - `IndexError: list index out of range`: Blueprint不在 → フィルター変更
     - その他のランタイムエラー: ログを確認して修正

3. **自動修正例**
   ```python
   # Blueprint not found エラーの修正
   # Before:
   vehicle_bp = blueprint_library.filter('vehicle.tesla.model3')[0]

   # After:
   vehicles = blueprint_library.filter('vehicle.*')
   if len(vehicles) == 0:
       print("No vehicles available", file=sys.stderr)
       sys.exit(1)
   vehicle_bp = vehicles[0]
   ```

4. **成功時**
   - シナリオが正常に実行され、指定時間後に終了
   - オプション: Rerunログ（.rrd）や動画（.mp4）の生成を確認

**出力ファイル（オプション）**:

- **RRDファイル** (`data/rerun/{logical_uuid}_{parameter_uuid}.rrd`):
  - Rerun Python SDKで記録された3D可視化データ
  - 車両の軌跡、位置、速度
  - `import rerun as rr`で記録

- **MP4ファイル** (`data/videos/{logical_uuid}_{parameter_uuid}.mp4`):
  - imageioで記録
  - RGB Camera Sensorからの映像

**ファイル名の意味**:
- `logical_uuid`: どの論理シナリオの実行か
- `parameter_uuid`: どのパラメータセットで実行したか
- 同じ論理シナリオを異なるパラメータで複数回実行可能

### Phase 5: トレース保存（オプション）

**目的**: 抽象→論理→実装の階層関係をJSONに保存

**手順**:

1. **トレース情報の作成**
   - シナリオメタデータを構築:
     - `id`: シナリオID
     - `name`: シナリオ名
     - `description`: 概要
     - `trace.original_prompt`: ユーザーの元の要件
     - `trace.abstract_scenario`: Phase 1の出力
     - `trace.logical_scenario`: Phase 2の出力
     - `trace.implementation`: 実行情報（試行回数、エラー、最終ステータス）
   - `python_file`: Pythonファイルパス
   - `rerun_file`: .rrdファイルパス（オプション）
   - `video_file`: .mp4ファイルパス（オプション）

2. **保存**
   - `data/scenarios/{scenario_id}.json`に保存

3. **UI表示**
   - UIがある場合、シナリオ一覧を更新
   - ユーザーにシナリオが生成されたことを通知

**実行トレースファイル例** (`data/scenarios/execution_{logical_uuid}_{parameter_uuid}.json`):
```json
{
  "execution_uuid": "abc12345-6789-0123-4567-890abcdef012",
  "logical_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "abstract_uuid": "a1b2c3d4-e5f6-4789-a012-3456789abcde",
  "parameter_uuid": "abc12345-6789-0123-4567-890abcdef012",
  "name": "highway_follow",
  "description": "高速道路で前方車両を20m間隔で追従するシナリオ",
  "executed_at": "2026-02-06T23:53:00Z",
  "trace": {
    "abstract_scenario_file": "data/scenarios/abstract_a1b2c3d4-e5f6-4789-a012-3456789abcde.json",
    "logical_scenario_file": "data/scenarios/logical_550e8400-e29b-41d4-a716-446655440000.json",
    "parameter_file": "data/scenarios/params_abc12345-6789-0123-4567-890abcdef012.json",
    "implementation": {
      "python_file": "scenarios/550e8400-e29b-41d4-a716-446655440000.py",
      "command": "uv run python scenarios/550e8400-e29b-41d4-a716-446655440000.py --params data/scenarios/params_abc12345-6789-0123-4567-890abcdef012.json",
      "exit_code": 0,
      "final_status": "success"
    }
  },
  "outputs": {
    "rerun": "data/rerun/550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.rrd",
    "video": "data/videos/550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.mp4"
  }
}
```

**ファイルパス**: `data/scenarios/execution_550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.json`

**トレーサビリティの自動分析**:

1. **親子関係の特定**:
   ```python
   import json

   # トレースファイルから親子関係を取得
   with open('data/scenarios/trace_550e8400-e29b-41d4-a716-446655440000.json') as f:
       trace = json.load(f)

   logical_uuid = trace['logical_uuid']
   abstract_uuid = trace['abstract_uuid']

   print(f"論理シナリオ {logical_uuid} は抽象シナリオ {abstract_uuid} から生成された")
   ```

2. **抽象シナリオの元データを参照**:
   ```python
   # 抽象シナリオファイルを読み込み
   abstract_file = trace['trace']['abstract_scenario_file']
   with open(abstract_file) as f:
       abstract = json.load(f)

   print(f"元の要件: {abstract['original_prompt']}")
   print(f"アクター: {[a['id'] for a in abstract['actors']]}")
   ```

3. **逆引き（抽象シナリオから派生した論理シナリオを探す）**:
   ```python
   import glob

   def find_logical_scenarios_by_abstract(abstract_uuid):
       """指定した抽象シナリオから生成された論理シナリオを全て探す"""
       logical_files = []
       for trace_file in glob.glob('data/scenarios/trace_*.json'):
           with open(trace_file) as f:
               trace = json.load(f)
               if trace['abstract_uuid'] == abstract_uuid:
                   logical_files.append(trace['logical_uuid'])
       return logical_files

   # 使用例
   derivatives = find_logical_scenarios_by_abstract('a1b2c3d4-e5f6-4789-a012-3456789abcde')
   print(f"抽象シナリオから派生した論理シナリオ: {derivatives}")
   ```

## 使用例

### 例1: 基本的な追従シナリオ

**ユーザー入力**:
```
シナリオ生成してください。高速道路で前方車両を追従するシナリオです。
```

**エージェントの動作**:
1. Phase 1: 抽象シナリオ生成（2台の車両、追従maneuver、UUID: `a1b2c3d4`）
2. Phase 2: 論理シナリオ生成（highway、初期位置・速度、UUID: `550e8400`、親: `a1b2c3d4`）
3. Phase 3: Python実装生成（`scenarios/550e8400.py`、論理シナリオUUID使用）
4. Phase 4: 実行（1回で成功）
5. Phase 5: トレース保存（階層関係を記録）

**出力ファイル構造**:
```
data/scenarios/
  ├── abstract_a1b2c3d4-e5f6-4789-a012-3456789abcde.json     # 抽象シナリオ
  ├── logical_550e8400-e29b-41d4-a716-446655440000.json      # 論理シナリオ（親: a1b2c3d4）
  └── trace_550e8400-e29b-41d4-a716-446655440000.json        # トレース（両UUID記録）

scenarios/
  └── 550e8400-e29b-41d4-a716-446655440000.py                # Python実装

data/rerun/
  └── 550e8400-e29b-41d4-a716-446655440000.rrd               # Rerunログ（オプション）

data/videos/
  └── 550e8400-e29b-41d4-a716-446655440000.mp4               # 動画（オプション）
```

**トレーサビリティ**:
- 論理シナリオファイルの`parent_abstract_uuid`を見れば元の抽象シナリオがわかる
- トレースファイルに両方のUUIDが記録され、ファイルパスも保存される

### 例2: 複数車両の合流シナリオ

**ユーザー入力**:
```
create scenario: 高速道路のランプから本線に合流するシナリオ。
車両は3台で、1台がランプから合流します。
```

**エージェントの動作**:
1. Phase 1: 抽象シナリオ生成（3台、合流maneuver）
2. Phase 2: 論理シナリオ生成（highway + ramp、初期位置）
3. Phase 3: Python実装生成
4. Phase 4: 実行（成功）
5. Phase 5: トレース保存

## MCPツールの使用（オプション）

このスキルは以下のMCPツールを使用できます:

- `generate_abstract_scenario(prompt: str)`: 抽象シナリオ生成
- `generate_logical_scenario(abstract: dict)`: 論理シナリオ生成
- `save_scenario_trace(trace: dict)`: トレース保存（オプション）
- `change_view(view: str)`: UI画面切り替え（UIがある場合）

## 関連スキル

- **carla-python-scenario**: CARLA Python API を使ったシナリオ記述
- **scenario-manager**: シナリオの管理・編集

## 注意事項

1. **CARLA接続の確認**
   - シナリオ実行前に、CARLAサーバーが`localhost:2000`で起動していることを確認
   - 起動していない場合はユーザーに通知

2. **リソース使用量**
   - .rrdファイルと.mp4ファイルは数百MBになる可能性がある
   - ディスク容量を確認

3. **同期モードの影響**
   - 同期モードではCARLAの実行速度がシミュレーションステップに依存
   - リアルタイムより遅くなる可能性がある

## トラブルシューティング

### CARLAに接続できない

- CARLAサーバーが起動しているか確認: `./CarlaUE4.sh`
- ポート2000が使用可能か確認

### スポーンに失敗する

- スポーンポイントが不足している可能性
- 別のマップを試す
- 既存の車両を削除してから再試行

### Blueprintが見つからない

- 利用可能な車両をリスト表示して確認
- フィルター条件を`'vehicle.*'`に変更して最初の車両を使用

### 動画生成に失敗する

- imageioがインストールされているか確認: `uv pip install imageio imageio-ffmpeg`
- カメラセンサーが正しく設定されているか確認

---

## imageioを使った動画記録

**Python実装での動画記録にはimageioを使用します**:

```python
import imageio
import numpy as np

# ビデオライター初期化
video_writer = imageio.get_writer(
    'data/videos/scenario.mp4',
    fps=20,
    codec='libx264',
    quality=8
)

# カメラコールバック
frames = []

def process_image(image):
    # CARLA imageをnumpy arrayに変換
    array = np.frombuffer(image.raw_data, dtype=np.uint8)
    array = array.reshape((image.height, image.width, 4))  # BGRA
    array = array[:, :, :3]  # BGRAからRGBに変換
    frames.append(array)

camera.listen(process_image)

# シナリオ実行後
for frame in frames:
    video_writer.append_data(frame)
video_writer.close()
```

---

**このスキルは包括的なシナリオ生成ワークフローを提供し、ユーザーの自然言語要件から実行可能なCARLAシナリオまでを自動化します。**
