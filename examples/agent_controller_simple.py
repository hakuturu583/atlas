"""
agent_controller 簡易使用例

AgentControllerクラスを使った最もシンプルな使い方を示します。
CARLAへの接続、同期モード設定、ログ保存、クリーンアップがすべて自動化されています。
"""

import sys
from pathlib import Path

# agent_controllerをインポート
sys.path.append(str(Path(__file__).parent.parent))

from agent_controller import AgentController
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord


def main():
    """メイン関数"""
    print("=== agent_controller Simple Example ===\n")

    # AgentControllerが自動的に:
    # - CARLAに接続
    # - 同期モードを設定
    # - ログを初期化
    # コンテキストマネージャを抜けると自動的に:
    # - ログを保存
    # - 同期モードを元に戻す
    # - クリーンアップを実行
    with AgentController(
        scenario_uuid="simple_example",
        carla_host="localhost",
        carla_port=2000,
        synchronous_mode=True,
        fixed_delta_seconds=0.05,  # 20 FPS
    ) as controller:
        world = controller.world
        print(f"Connected to CARLA: {world.get_map().name}\n")
        try:
            # 車両をスポーン
            print("\nSpawning vehicles...")
            blueprint_library = world.get_blueprint_library()
            vehicle_bp = blueprint_library.find("vehicle.tesla.model3")

            # opendrive_utilsでスポーン位置を計算
            od_map = OpenDriveMap(world)
            spawn_helper = SpawnHelper(od_map)

            lane_coord_1 = LaneCoord(road_id=10, lane_id=-1, s=50.0)
            transform_1 = spawn_helper.get_spawn_transform_from_lane(lane_coord_1)

            lane_coord_2 = LaneCoord(road_id=10, lane_id=-1, s=80.0)
            transform_2 = spawn_helper.get_spawn_transform_from_lane(lane_coord_2)

            ego_vehicle = world.spawn_actor(vehicle_bp, transform_1)
            npc_vehicle = world.spawn_actor(vehicle_bp, transform_2)
            print(f"  Ego vehicle spawned: ID={ego_vehicle.id}")
            print(f"  NPC vehicle spawned: ID={npc_vehicle.id}")

            # 車両を登録
            print("\nRegistering vehicles...")
            ego_id = controller.register_vehicle(
                vehicle=ego_vehicle,
                auto_lane_change=False,
                distance_to_leading=5.0,
                speed_percentage=80.0,
            )
            print(f"  Ego vehicle registered: ID={ego_id}")

            npc_id = controller.register_vehicle(
                vehicle=npc_vehicle,
                auto_lane_change=True,
                distance_to_leading=3.0,
                speed_percentage=60.0,
            )
            print(f"  NPC vehicle registered: ID={npc_id}")

            # シミュレーション実行
            print("\n=== Starting Simulation ===\n")
            frame = 0

            # Phase 1: 通常走行（100フレーム）
            print("Phase 1: Normal driving...")
            for i in range(100):
                world.tick()
                frame += 1

            # Phase 2: レーンチェンジ
            print("\nPhase 2: Lane change...")
            result = controller.lane_change(
                vehicle_id=ego_id,
                frame=frame,
                direction="left",
                duration_frames=100,
            )
            print(f"  {result.message}")

            for i in range(100):
                world.tick()
                frame += 1

            # Phase 3: カットイン
            print("\nPhase 3: Cut in...")
            result = controller.cut_in(
                vehicle_id=ego_id,
                frame=frame,
                target_vehicle_id=npc_id,
                gap_distance=3.0,
                speed_boost=120.0,
            )
            print(f"  {result.message}")

            for i in range(150):
                world.tick()
                frame += 1

            # Phase 4: 追従
            print("\nPhase 4: Following...")
            result = controller.follow(
                vehicle_id=ego_id,
                frame=frame,
                target_vehicle_id=npc_id,
                distance=5.0,
                duration_frames=200,
            )
            print(f"  {result.message}")

            for i in range(200):
                world.tick()
                frame += 1

            # Phase 5: 停止
            print("\nPhase 5: Stopping...")
            result = controller.stop(
                vehicle_id=ego_id,
                frame=frame,
                duration_frames=50,
            )
            print(f"  {result.message}")

            for i in range(50):
                world.tick()
                frame += 1

            print(f"\nSimulation completed. Total frames: {frame}")

            # 車両を破棄
            ego_vehicle.destroy()
            npc_vehicle.destroy()

    # コンテキストマネージャを抜けると自動的に:
    # - ログがファイナライズ・保存される
    # - サマリーが出力される
    # - 同期モードが元に戻される
    # - クリーンアップが実行される

    print("\n=== Example Completed ===")


if __name__ == "__main__":
    main()
