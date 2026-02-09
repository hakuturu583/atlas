---
name: carla-python-scenario
description: This skill should be used when the user asks to "create CARLA scenario in Python", "write Python CARLA script", "implement scenario with Python API", "use CARLA Python API", or mentions "carla python", "pythonでシナリオ", "python実装". Supports CARLA Python API scenario development with reference to official documentation.
---

# CARLA Python Scenario Writer

このスキルは、CARLA Python APIを使ったシナリオの記述をサポートします。

## 📚 必須リファレンス

**CARLA Python API Reference**: https://carla.readthedocs.io/en/latest/python_api/

このリファレンスを**必ず参照**してからコードを書いてください。主要なクラス：

- `carla.Client` - CARLAサーバーへの接続
- `carla.World` - ワールドオブジェクト
- `carla.Actor` - アクター（車両、歩行者など）
- `carla.Vehicle` - 車両制御
- `carla.Sensor` - センサー
- `carla.Transform` - 位置・姿勢
- `carla.Location` - 座標
- `carla.Rotation` - 回転
- `carla.VehicleControl` - 車両制御パラメータ

## 🎯 実装フロー

### 1. シナリオ要件を確認

ユーザーが実装したいシナリオの内容を確認：
- どのような動作をさせたいか
- 車両の数、種類
- センサーの有無
- 実行時間・条件
- 出力データ

### 2. scenarios/*.py に実装

シナリオコードは `scenarios/` ディレクトリに新しいPythonファイルを作成します。

**ディレクトリ**: `/home/masaya/workspace/atlas/scenarios/`

### 3. 実行

```bash
uv run python scenarios/your_scenario.py
```

## 📝 基本パターン

**🚨 IMPORTANT**: `get_spawn_points()`は使用禁止。必ず`opendrive_utils`を使用してください。

```python
#!/usr/bin/env python3
import carla
import time
import sys
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord


def main():
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.get_world()

    # opendrive_utils初期化
    od_map = OpenDriveMap(world)
    spawn_helper = SpawnHelper(od_map)

    actors = []
    try:
        blueprint_library = world.get_blueprint_library()
        vehicle_bp = blueprint_library.filter('vehicle.*')[0]

        # ✅ GOOD: opendrive_utilsでスポーン位置を計算
        lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
        transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)

        vehicle = world.spawn_actor(vehicle_bp, transform)
        actors.append(vehicle)

        # シナリオロジック
        control = carla.VehicleControl(throttle=0.5)
        for _ in range(100):
            vehicle.apply_control(control)
            time.sleep(0.1)

        return 0

    finally:
        for actor in actors:
            actor.destroy()


if __name__ == "__main__":
    sys.exit(main())
```

## ⚠️ 重要事項

1. **CARLAサーバーが起動しているか確認**
2. **必ず`try-finally`でクリーンアップ**
3. **スポーンしたアクターは`destroy()`を呼ぶ**

4. **🚨 CRITICAL: `get_spawn_points()`は使用禁止**
   - **`carla.Map.get_spawn_points()`を使用しないこと**
   - 理由: ランダムな位置になり、狙った位置に配置できない
   - **必ず`opendrive_utils`を使用してスポーン位置を計算すること**

   **❌ BAD（禁止）**:
   ```python
   spawn_points = world.get_map().get_spawn_points()
   transform = spawn_points[0]  # ランダムな位置
   vehicle = world.spawn_actor(blueprint, transform)
   ```

   **✅ GOOD（必須）**:
   ```python
   from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

   od_map = OpenDriveMap(world)
   spawn_helper = SpawnHelper(od_map)

   # レーン座標から精密にスポーン
   lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
   transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)
   vehicle = world.spawn_actor(blueprint, transform)
   ```

5. **🚨 CRITICAL: 車両制御は必ずTraffic Managerを使用**
   - 車両をautopilotで動かす場合は、必ずCARLA Traffic Managerを明示的に設定すること
   - 同期モードでTraffic Managerを動作させること

   **実装例**:
   ```python
   # Traffic Managerを取得（ポート: CARLA_PORT + 6000）
   traffic_manager = client.get_trafficmanager(2000 + 6000)
   traffic_manager.set_synchronous_mode(True)

   # Traffic Managerで車両を制御
   vehicle.set_autopilot(True, traffic_manager.get_port())

   # Traffic Manager設定（信号機認識など）
   traffic_manager.ignore_lights_percentage(vehicle, 0)  # 信号を100%守る
   traffic_manager.distance_to_leading_vehicle(vehicle, 2.0)  # 前方車両との距離
   traffic_manager.vehicle_percentage_speed_difference(vehicle, -20)  # 制限速度の20%減
   ```

## 📖 opendrive_utilsの使い方

詳細なドキュメントは `opendrive_utils/README.md` を参照してください。

### 基本的な使い方

```python
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

# 初期化
od_map = OpenDriveMap(world)
spawn_helper = SpawnHelper(od_map)

# レーン座標からスポーン
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)
vehicle = world.spawn_actor(blueprint, transform)
```

### 信号機を考慮したスポーン

```python
from opendrive_utils import AdvancedFeatures

advanced = AdvancedFeatures(od_map)

# 信号機を検索
signals = advanced.get_traffic_signals()
signal = signals[0]

# 信号機の10m手前にスポーン
transform = advanced.get_spawn_before_signal(signal, lane_id=-1, distance_before=10.0)
vehicle = world.spawn_actor(blueprint, transform)
```

---

**CARLA Python API Reference**: https://carla.readthedocs.io/en/latest/python_api/
