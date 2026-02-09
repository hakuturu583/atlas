#!/usr/bin/env python3
"""
OpenDRIVE Utilities サンプルスクリプト

このスクリプトは、opendrive_utilsライブラリの基本的な使い方を示します。
"""

import carla
import time
from opendrive_utils import (
    OpenDriveMap,
    CoordinateTransformer,
    SpawnHelper,
    WorldCoord,
    LaneCoord,
    RoadCoord,
)


def main():
    # CARLAに接続
    print("CARLAサーバーに接続中...")
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.get_world()
    print(f"マップ: {world.get_map().name}")

    # OpenDRIVEマップを読み込み
    print("\nOpenDRIVEマップを読み込み中...")
    od_map = OpenDriveMap(world)

    # 1. 道路情報を表示
    print("\n=== 道路情報 ===")
    roads = od_map.list_roads()
    print(f"道路数: {len(roads)}")

    # 最初の5つの道路を表示
    for road in roads[:5]:
        road_type = "交差点" if road['junction'] != -1 else "通常"
        print(f"  Road {road['id']}: 長さ={road['length']:.2f}m, タイプ={road_type}")

    # 特定の道路を詳しく見る
    target_road_id = roads[0]['id']
    print(f"\nRoad {target_road_id} の詳細:")
    road_length = od_map.get_road_length(target_road_id)
    available_lanes = od_map.get_available_lanes(target_road_id, s=10.0)
    print(f"  長さ: {road_length:.2f}m")
    print(f"  利用可能なレーン: {available_lanes}")

    # 2. 座標系変換のデモ
    print("\n=== 座標系変換 ===")
    transformer = CoordinateTransformer(od_map)

    # 世界座標からレーン座標へ
    world_coord = WorldCoord(x=100.0, y=50.0, z=0.0)
    print(f"世界座標: ({world_coord.x:.2f}, {world_coord.y:.2f}, {world_coord.z:.2f})")

    lane_coord = transformer.world_to_lane(world_coord)
    if lane_coord:
        print(f"  → {lane_coord}")

        # レーン座標から世界座標へ（逆変換）
        world_coord_back = transformer.lane_to_world(lane_coord)
        if world_coord_back:
            print(f"  → 世界座標: ({world_coord_back.x:.2f}, {world_coord_back.y:.2f}, {world_coord_back.z:.2f})")

    # レーン上の距離計算
    if available_lanes:
        lane_id = available_lanes[0]
        start = LaneCoord(road_id=target_road_id, lane_id=lane_id, s=10.0)
        end = LaneCoord(road_id=target_road_id, lane_id=lane_id, s=50.0)
        distance = transformer.calculate_distance_along_lane(start, end)
        print(f"\nレーン上の距離計算:")
        print(f"  {start}")
        print(f"  → {end}")
        print(f"  距離: {distance:.2f}m")

    # 3. スポーン位置の計算とデモ
    print("\n=== スポーン位置の計算 ===")
    spawn_helper = SpawnHelper(od_map)

    # スポーンする車両のBlueprint
    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter('vehicle.tesla.model3')[0]

    spawned_vehicles = []

    # 3-1. レーン座標からスポーン
    if available_lanes:
        lane_id = available_lanes[0]
        lane_coord = LaneCoord(road_id=target_road_id, lane_id=lane_id, s=50.0)
        transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)

        if transform:
            print(f"\nレーン座標からスポーン: {lane_coord}")
            print(f"  Transform: location=({transform.location.x:.2f}, {transform.location.y:.2f}, {transform.location.z:.2f}), "
                  f"yaw={transform.rotation.yaw:.2f}°")

            try:
                vehicle = world.spawn_actor(vehicle_bp, transform)
                spawned_vehicles.append(vehicle)
                print("  ✓ 車両をスポーンしました")
            except RuntimeError as e:
                print(f"  ✗ スポーン失敗: {e}")

        # 3-2. 指定距離前方にスポーン
        forward_transform = spawn_helper.get_spawn_transform_at_distance(
            lane_coord,
            distance=30.0
        )
        if forward_transform:
            print(f"\n30m前方にスポーン:")
            print(f"  Transform: location=({forward_transform.location.x:.2f}, {forward_transform.location.y:.2f})")

            try:
                vehicle = world.spawn_actor(vehicle_bp, forward_transform)
                spawned_vehicles.append(vehicle)
                print("  ✓ 車両をスポーンしました")
            except RuntimeError as e:
                print(f"  ✗ スポーン失敗: {e}")

        # 3-3. レーン上に複数の車両を配置
        print(f"\nレーン上に3台の車両を20m間隔で配置:")
        transforms = spawn_helper.get_spawn_points_along_lane(
            lane_coord,
            num_points=3,
            spacing=20.0
        )
        for i, t in enumerate(transforms):
            try:
                vehicle = world.spawn_actor(vehicle_bp, t)
                spawned_vehicles.append(vehicle)
                print(f"  ✓ 車両{i+1}をスポーン: ({t.location.x:.2f}, {t.location.y:.2f})")
            except RuntimeError as e:
                print(f"  ✗ 車両{i+1}のスポーン失敗: {e}")

    # 4. スポーンした車両を表示
    print(f"\n=== 結果 ===")
    print(f"スポーンした車両数: {len(spawned_vehicles)}")

    if spawned_vehicles:
        print("\n5秒間待機します（スペクテーターで確認してください）...")
        time.sleep(5)

        # クリーンアップ
        print("\n車両を削除中...")
        for vehicle in spawned_vehicles:
            vehicle.destroy()
        print("✓ すべての車両を削除しました")

    print("\n完了!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断されました")
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
