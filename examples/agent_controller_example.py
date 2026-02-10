"""
agent_controller使用例（コールバックベース）

このスクリプトは、agent_controllerパッケージの新しいコールバックベースAPIの使い方を示します。
world.tick()やフレーム管理が不要になり、シナリオを直感的に記述できます。
"""

import sys
from pathlib import Path

# agent_controllerをインポート
sys.path.append(str(Path(__file__).parent.parent))

from agent_controller import AgentController
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord


def main():
    """メイン関数"""
    print("=== agent_controller Example ===\n")

    # AgentControllerが自動的にCARLAに接続し、同期モードを設定
    with AgentController(
        scenario_uuid="example_scenario_001",
        carla_host="localhost",
        carla_port=2000,
        synchronous_mode=True,
        fixed_delta_seconds=0.05,  # 20 FPS
    ) as controller:
        print(f"Connected to CARLA: {controller.get_map().name}\n")

        # 接続確認
        if controller.is_alive():
            print("✓ CARLA server is alive\n")

        # 車両をスポーン（自動登録）
        print("Spawning vehicles...")

        # Ego車両（レーン座標から自動スポーン＆登録）
        lane_coord_1 = LaneCoord(road_id=10, lane_id=-1, s=50.0)
        ego_vehicle, ego_id = controller.spawn_vehicle_from_lane(
            "vehicle.tesla.model3",
            lane_coord_1,
            auto_register=True,
            auto_lane_change=False,
            distance_to_leading=5.0,
            speed_percentage=80.0,
        )
        print(f"  Ego vehicle spawned: ID={ego_id}")

        # NPC車両（レーン座標から自動スポーン＆登録）
        lane_coord_2 = LaneCoord(road_id=10, lane_id=-1, s=80.0)
        npc_vehicle, npc_id = controller.spawn_vehicle_from_lane(
            "vehicle.tesla.model3",
            lane_coord_2,
            auto_register=True,
            auto_lane_change=True,
            distance_to_leading=3.0,
            speed_percentage=60.0,
        )
        print(f"  NPC vehicle spawned: ID={npc_id}")

        # ========================================
        # シナリオをトリガー関数で定義
        # （world.tick()とフレーム管理が不要！）
        # ========================================
        print("\n=== Defining Scenario with Trigger Functions ===\n")

        # Phase 1は通常走行（フレーム0-99）なのでコールバックなし

        # Phase 2: フレーム100でレーンチェンジ
        def on_frame_100():
            print("\n→ Phase 2: Lane change...")
            result = controller.lane_change(
                vehicle_id=ego_id,
                direction="left",
                duration_frames=100,
            )
            print(f"  {result.message}")
            if "distance_traveled" in result.metrics:
                print(
                    f"  Distance traveled: {result.metrics['distance_traveled']:.2f}m"
                )

        controller.register_callback(controller.when_timestep_equals(100), on_frame_100)

        # Phase 3: フレーム200でカットイン
        def on_frame_200():
            print("\n→ Phase 3: Cut in...")
            result = controller.cut_in(
                vehicle_id=ego_id,
                target_vehicle_id=npc_id,
                gap_distance=3.0,
                speed_boost=120.0,
            )
            print(f"  {result.message}")

        controller.register_callback(controller.when_timestep_equals(200), on_frame_200)

        # Phase 4: フレーム350で追従
        def on_frame_350():
            print("\n→ Phase 4: Following...")
            result = controller.follow(
                vehicle_id=ego_id,
                target_vehicle_id=npc_id,
                distance=5.0,
                duration_frames=200,
            )
            print(f"  {result.message}")

        controller.register_callback(controller.when_timestep_equals(350), on_frame_350)

        # Phase 5: フレーム550で停止
        def on_frame_550():
            print("\n→ Phase 5: Stopping...")
            result = controller.stop(
                vehicle_id=ego_id,
                duration_frames=50,
            )
            print(f"  {result.message}")

        controller.register_callback(controller.when_timestep_equals(550), on_frame_550)

        # ========================================
        # シミュレーション実行
        # （world.tick()は自動的に呼ばれる）
        # ========================================
        controller.run_simulation(total_frames=600)

    # コンテキストマネージャを抜けると自動的に:
    # - スポーンした車両が自動的に破棄される
    # - ログがファイナライズ・保存される
    # - サマリーが出力される
    # - 同期モードが元に戻される
    # - クリーンアップが実行される

    print("\n=== Example Completed ===")


if __name__ == "__main__":
    main()
