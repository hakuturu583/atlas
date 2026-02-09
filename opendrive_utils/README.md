# OpenDRIVE Utilities for CARLA

CARLAのOpenDRIVEファイルを解析し、座標系変換やスポーン位置計算を簡単に行うためのPythonライブラリです。

## 機能

1. **OpenDRIVEファイルの解析** (`parser.py`)
   - CARLA APIで取得した.xodrをpyxodrで解釈
   - 道路、レーン、交差点の情報取得

2. **座標系変換** (`coordinate_transform.py`)
   - 世界座標 ↔ Road座標
   - 世界座標 ↔ Lane座標
   - Road座標 ↔ Lane座標
   - レーン上の距離計算

3. **スポーン位置計算** (`spawn_helper.py`)
   - レーン座標からcarla.Transformを計算
   - 指定距離でのスポーン位置
   - 交差点内でのスポーン位置
   - 相対位置でのスポーン位置

## インストール

```bash
# プロジェクトの依存関係を同期
uv sync
```

## 基本的な使い方

### 1. OpenDRIVEマップの読み込み

```python
import carla
from opendrive_utils import OpenDriveMap

# CARLAに接続
client = carla.Client('localhost', 2000)
client.set_timeout(10.0)
world = client.get_world()

# OpenDRIVEマップを読み込み
od_map = OpenDriveMap(world)

# 道路情報を取得
roads = od_map.list_roads()
print(f"道路数: {len(roads)}")

# 特定の道路の情報
road_id = 10
road_length = od_map.get_road_length(road_id)
print(f"Road {road_id} の長さ: {road_length:.2f}m")

# 利用可能なレーンを取得
available_lanes = od_map.get_available_lanes(road_id, s=50.0)
print(f"利用可能なレーン: {available_lanes}")
```

### 2. 座標系変換

```python
from opendrive_utils import (
    OpenDriveMap,
    CoordinateTransformer,
    WorldCoord,
    LaneCoord,
    RoadCoord,
)

od_map = OpenDriveMap(world)
transformer = CoordinateTransformer(od_map)

# 世界座標からレーン座標へ変換
world_coord = WorldCoord(x=100.0, y=50.0, z=0.0)
lane_coord = transformer.world_to_lane(world_coord)
print(f"レーン座標: {lane_coord}")

# レーン座標から世界座標へ変換
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0, offset=0.0)
world_coord = transformer.lane_to_world(lane_coord)
print(f"世界座標: ({world_coord.x:.2f}, {world_coord.y:.2f}, {world_coord.z:.2f})")

# レーン上の距離を計算
start = LaneCoord(road_id=10, lane_id=-1, s=10.0)
end = LaneCoord(road_id=10, lane_id=-1, s=50.0)
distance = transformer.calculate_distance_along_lane(start, end)
print(f"距離: {distance:.2f}m")
```

### 3. スポーン位置の計算

```python
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

od_map = OpenDriveMap(world)
spawn_helper = SpawnHelper(od_map)

# レーン座標からスポーン位置を計算
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0, offset=0.0)
transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)

# 車両をスポーン
blueprint = world.get_blueprint_library().find('vehicle.tesla.model3')
vehicle = world.spawn_actor(blueprint, transform)
print(f"車両をスポーンしました: {transform.location}")

# 指定距離前方にスポーン
forward_transform = spawn_helper.get_spawn_transform_at_distance(
    lane_coord,
    distance=30.0  # 30m前方
)
vehicle2 = world.spawn_actor(blueprint, forward_transform)

# レーン上に複数の車両を配置
transforms = spawn_helper.get_spawn_points_along_lane(
    lane_coord,
    num_points=5,
    spacing=20.0  # 20m間隔
)
for t in transforms:
    world.spawn_actor(blueprint, t)
```

## 実践例

### 例1: 直線道路でのNPCスポーン

```python
import carla
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

client = carla.Client('localhost', 2000)
world = client.get_world()

od_map = OpenDriveMap(world)
spawn_helper = SpawnHelper(od_map)

# 直線道路（road_id=10）の右側レーン（lane_id=-1）
# s=100mの位置にNPCをスポーン
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=100.0)
transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)

bp = world.get_blueprint_library().find('vehicle.audi.a2')
npc = world.spawn_actor(bp, transform)
print(f"NPCをスポーン: road_id={lane_coord.road_id}, lane_id={lane_coord.lane_id}, s={lane_coord.s}")
```

### 例2: 交差点でのスポーン

```python
# 交差点内（junction road）でスポーン
junction_road_id = 25
transform = spawn_helper.get_spawn_transform_at_junction(
    junction_road_id=junction_road_id,
    entry_road_id=10,
    exit_road_id=15,
    progress=0.5  # 交差点の中央
)

bp = world.get_blueprint_library().find('vehicle.volkswagen.t2')
junction_vehicle = world.spawn_actor(bp, transform)
```

### 例3: 相対位置でのスポーン

```python
# Ego車両の前方30m、左1.5mにNPCをスポーン
ego_transform = ego_vehicle.get_transform()

npc_transform = spawn_helper.calculate_relative_spawn(
    reference_transform=ego_transform,
    forward_distance=30.0,  # 前方30m
    lateral_offset=1.5,     # 左に1.5m
    z_offset=0.0
)

bp = world.get_blueprint_library().find('vehicle.bmw.grandtourer')
npc = world.spawn_actor(bp, npc_transform)
```

### 例4: レーン上の安全な位置を自動検出

```python
# 道路10、レーン-1上の安全なスポーン位置を10m間隔で取得
safe_transforms = spawn_helper.get_safe_spawn_points(
    road_id=10,
    lane_id=-1,
    min_spacing=10.0
)

print(f"安全なスポーン位置: {len(safe_transforms)}箇所")

# 最初の3つの位置に車両をスポーン
for i, transform in enumerate(safe_transforms[:3]):
    bp = world.get_blueprint_library().find('vehicle.mini.cooperst')
    world.spawn_actor(bp, transform)
```

## 座標系の説明

### 世界座標系 (World Coordinate)
- CARLAの絶対座標系
- `(x, y, z)` で表現
- 単位: メートル

### Road座標系 (Road Coordinate)
- `(road_id, s, t)` で表現
- `road_id`: 道路ID
- `s`: 道路の始点からの距離（メートル）
- `t`: 道路中心線からの横方向オフセット（メートル、左が正）

### Lane座標系 (Lane Coordinate)
- `(road_id, lane_id, s, offset)` で表現
- `road_id`: 道路ID
- `lane_id`: レーンID（正: 左側、負: 右側、0: 中央線）
- `s`: 道路の始点からの距離（メートル）
- `offset`: レーン中心からのオフセット（メートル）

## APIリファレンス

### OpenDriveMap

| メソッド | 説明 |
|---------|------|
| `get_road(road_id)` | Road IDからRoadオブジェクトを取得 |
| `get_lane_section(road_id, s)` | 指定したs座標でのLaneSectionを取得 |
| `get_lane(road_id, lane_id, s)` | 指定したレーンのLaneオブジェクトを取得 |
| `get_available_lanes(road_id, s)` | 利用可能なLane IDのリストを取得 |
| `get_road_length(road_id)` | Roadの長さを取得 |
| `get_lane_width(road_id, lane_id, s)` | レーン幅を取得 |
| `list_roads()` | すべての道路情報をリスト化 |
| `is_junction(road_id)` | 交差点かどうかを判定 |

### CoordinateTransformer

| メソッド | 説明 |
|---------|------|
| `world_to_road(world_coord)` | 世界座標→Road座標 |
| `road_to_world(road_coord)` | Road座標→世界座標 |
| `world_to_lane(world_coord)` | 世界座標→Lane座標 |
| `lane_to_world(lane_coord)` | Lane座標→世界座標 |
| `road_to_lane(road_coord, lane_id)` | Road座標→Lane座標 |
| `lane_to_road(lane_coord)` | Lane座標→Road座標 |
| `calculate_distance_along_lane(start, end)` | レーン上の距離を計算 |
| `calculate_lateral_offset(lane_coord, target_lane_id)` | 横方向オフセットを計算 |

### SpawnHelper

| メソッド | 説明 |
|---------|------|
| `get_spawn_transform_from_lane(lane_coord)` | レーン座標→Transform |
| `get_spawn_transform_from_road(road_coord)` | Road座標→Transform |
| `get_spawn_transform_at_distance(start, distance)` | 指定距離前方のTransform |
| `get_spawn_points_along_lane(lane_coord, num_points, spacing)` | レーン上に等間隔でTransformを配置 |
| `get_spawn_transform_at_junction(...)` | 交差点内のTransform |
| `find_spawn_point_near_location(location)` | 指定座標近くの有効なTransform |
| `get_safe_spawn_points(road_id, lane_id, min_spacing)` | 安全なスポーン位置をすべて取得 |
| `calculate_relative_spawn(reference, forward, lateral)` | 相対位置のTransform |

## 高度な機能

### 交差点、信号機、停止線の扱い

`AdvancedFeatures`クラスを使って、OpenDRIVEの高度な属性を利用できます。

#### 信号機情報の取得

```python
from opendrive_utils import OpenDriveMap, AdvancedFeatures

od_map = OpenDriveMap(world)
advanced = AdvancedFeatures(od_map)

# すべての信号機を取得
signals = advanced.get_traffic_signals()
print(f"信号機: {len(signals)}個")

# 特定の道路上の信号機
road_signals = advanced.get_signals_on_road(road_id=10)

# 最も近い信号機を検索
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
nearest_signal = advanced.get_nearest_signal(lane_coord, max_distance=100.0)

if nearest_signal:
    print(f"最も近い信号機: {nearest_signal.id}, 距離: {nearest_signal.s - lane_coord.s:.2f}m")

    # 信号機の世界座標を取得
    signal_transform = advanced.get_signal_transform(nearest_signal)
```

#### 信号機の手前にスポーン

```python
# 信号機の10m手前に車両をスポーン
signal = signals[0]
lane_id = -1  # 右側レーン

transform = advanced.get_spawn_before_signal(
    signal,
    lane_id=lane_id,
    distance_before=10.0  # 10m手前
)

vehicle = world.spawn_actor(blueprint, transform)
```

#### 停止線の取得

```python
# すべての停止線を取得
stop_lines = advanced.get_stop_lines()

for stop_line in stop_lines:
    print(f"{stop_line}")

    # 停止線の位置を取得
    transform = advanced.get_stop_line_transform(stop_line)

    # 停止線の2m手前にスポーン
    spawn_transform = advanced.get_spawn_at_stop_line(
        stop_line,
        offset_before=2.0
    )
    vehicle = world.spawn_actor(blueprint, spawn_transform)
```

#### 交差点情報の取得

```python
# すべての交差点を取得
junctions = advanced.get_junctions()

for junction_id, junction in junctions.items():
    print(f"交差点: {junction.name} (ID: {junction_id})")
    print(f"  接続数: {len(junction.connections)}")

    # 交差点の中心位置
    center_transform = advanced.get_junction_center_transform(junction_id)

    # 各接続情報
    for connection in junction.connections:
        print(f"  {connection.incoming_road} → {connection.connecting_road}")
```

#### 交差点の流入・流出点

```python
junction_id = 1
incoming_road_id = 10

# 交差点への流入点
entry_points = advanced.get_junction_entry_points(
    junction_id,
    incoming_road_id
)

for transform in entry_points:
    vehicle = world.spawn_actor(blueprint, transform)

# 交差点からの流出点
outgoing_road_id = 15
exit_points = advanced.get_junction_exit_points(
    junction_id,
    outgoing_road_id
)
```

#### 交差点経路の検索

```python
# 交差点内の経路を取得
path = advanced.find_path_through_junction(
    junction_id=1,
    incoming_road_id=10,
    outgoing_road_id=15
)

if path:
    print(f"経路: {' → '.join(map(str, path))}")
```

### 実践例: 信号機シナリオ

```python
import carla
from opendrive_utils import OpenDriveMap, AdvancedFeatures, LaneCoord

client = carla.Client('localhost', 2000)
world = client.get_world()

od_map = OpenDriveMap(world)
advanced = AdvancedFeatures(od_map)

# 信号機を取得
signals = advanced.get_traffic_signals()
signal = signals[0]

print(f"信号機 {signal.id} を使用")
print(f"  位置: Road {signal.road_id}, s={signal.s:.2f}m")

# 信号機の手前に3台の車両を配置
lane_id = -1  # 右側レーン
distances = [10.0, 20.0, 30.0]  # 10m, 20m, 30m手前

blueprint = world.get_blueprint_library().find('vehicle.audi.a2')

for distance in distances:
    transform = advanced.get_spawn_before_signal(signal, lane_id, distance)
    if transform:
        vehicle = world.spawn_actor(blueprint, transform)
        print(f"✓ 信号機の{distance}m手前に車両をスポーン")
```

### AdvancedFeaturesクラスのAPIリファレンス

#### 信号機関連

| メソッド | 説明 |
|---------|------|
| `get_traffic_signals()` | すべての信号機を取得 |
| `get_signals_on_road(road_id)` | 指定した道路上の信号機を取得 |
| `get_nearest_signal(lane_coord, max_distance)` | 最も近い信号機を検索 |
| `get_signal_transform(signal)` | 信号機の世界座標Transform |
| `get_spawn_before_signal(signal, lane_id, distance_before)` | 信号機の手前にスポーン位置を計算 |

#### 停止線関連

| メソッド | 説明 |
|---------|------|
| `get_stop_lines()` | すべての停止線を取得 |
| `get_stop_line_transform(stop_line)` | 停止線の世界座標Transform |
| `get_spawn_at_stop_line(stop_line, offset_before)` | 停止線の手前にスポーン位置を計算 |

#### 交差点関連

| メソッド | 説明 |
|---------|------|
| `get_junctions()` | すべての交差点を取得 |
| `get_junction_by_road(road_id)` | 指定した道路が属する交差点を取得 |
| `get_junction_entry_points(junction_id, incoming_road_id)` | 交差点への流入点 |
| `get_junction_exit_points(junction_id, outgoing_road_id)` | 交差点からの流出点 |
| `find_path_through_junction(junction_id, incoming_road_id, outgoing_road_id)` | 交差点内の経路を検索 |
| `get_junction_center_transform(junction_id)` | 交差点の中心位置 |

## 注意事項

- レーンIDは、進行方向に対して左側が正、右側が負です
- s座標は道路の始点からの距離で、道路の長さを超えないようにしてください
- 交差点（Junction）内では、レーン構造が複雑になる場合があります
- スポーン位置の計算では、必ず`carla.World.spawn_actor()`で実際にスポーン可能か確認してください
- 信号機の`orientation`は進行方向を示します（'+': 正の方向、'-': 負の方向）
- 停止線の位置は信号機の位置から推定されるため、実際の停止線とは若干ずれる場合があります

## サンプルスクリプト

```bash
# 基本的な使い方
uv run python examples/opendrive_utils_example.py

# 高度な機能（信号機、交差点）
uv run python examples/advanced_features_example.py
```

## ライセンス

MIT License
