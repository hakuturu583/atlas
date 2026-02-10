"""
agent_controller使用例

このスクリプトは、agent_controllerパッケージの使い方を示します。
レーンチェンジ、カットイン、タイミング突入などの振る舞いを実行します。
"""

import sys
import time
from pathlib import Path

import carla

# agent_controllerをインポート
sys.path.append(str(Path(__file__).parent.parent))

from agent_controller import (
    TrafficManagerWrapper,
    STAMPLogger,
    CommandTracker,
    LaneChangeBehavior,
    CutInBehavior,
    TimedApproachBehavior,
    FollowBehavior,
    StopBehavior,
)


def main():
    """メイン関数"""
    print("=== agent_controller Example ===\n")

    # シナリオUUID
    scenario_uuid = "example_scenario_001"

    # CARLAクライアント接続
    print("Connecting to CARLA...")
    client = carla.Client("localhost", 2000)
    client.set_timeout(10.0)
    world = client.get_world()

    # 同期モード設定
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05  # 20 FPS
    world.apply_settings(settings)

    # ロガー初期化
    print("Initializing loggers...")
    stamp_logger = STAMPLogger(scenario_uuid=scenario_uuid)
    command_tracker = CommandTracker(scenario_uuid=scenario_uuid)

    # Traffic Manager Wrapper初期化
    print("Initializing Traffic Manager Wrapper...")
    tm_wrapper = TrafficManagerWrapper(
        client=client,
        port=8000,
        stamp_logger=stamp_logger,
        command_tracker=command_tracker,
    )

    try:
        # 車両をスポーン
        print("\nSpawning vehicles...")
        blueprint_library = world.get_blueprint_library()
        vehicle_bp = blueprint_library.find("vehicle.tesla.model3")
        spawn_points = world.get_map().get_spawn_points()

        # Ego車両
        ego_vehicle = world.spawn_actor(vehicle_bp, spawn_points[0])
        print(f"  Ego vehicle spawned: ID={ego_vehicle.id}")

        # NPC車両
        npc_vehicle = world.spawn_actor(vehicle_bp, spawn_points[1])
        print(f"  NPC vehicle spawned: ID={npc_vehicle.id}")

        # 車両を登録
        print("\nRegistering vehicles...")
        ego_id = tm_wrapper.register_vehicle(
            vehicle=ego_vehicle,
            auto_lane_change=False,  # 手動でレーンチェンジを制御
            distance_to_leading=5.0,
            speed_percentage=80.0,
        )
        print(f"  Ego vehicle registered: ID={ego_id}")

        npc_id = tm_wrapper.register_vehicle(
            vehicle=npc_vehicle,
            auto_lane_change=True,
            distance_to_leading=3.0,
            speed_percentage=60.0,
        )
        print(f"  NPC vehicle registered: ID={npc_id}")

        # シミュレーション実行
        print("\n=== Starting Simulation ===\n")
        frame = 0

        # 100フレーム走行
        print("Phase 1: Normal driving...")
        for i in range(100):
            world.tick()
            frame += 1

        # レーンチェンジ実行
        print("\nPhase 2: Lane change...")
        lane_change = LaneChangeBehavior(tm_wrapper)
        result = lane_change.execute(
            vehicle_id=ego_id,
            frame=frame,
            direction="left",
            duration_frames=100,
        )
        print(f"  {result.message}")
        print(f"  Distance traveled: {result.metrics['distance_traveled']:.2f}m")

        # レーンチェンジ完了まで待機
        for i in range(100):
            world.tick()
            frame += 1

        # カットイン実行
        print("\nPhase 3: Cut in...")
        cut_in = CutInBehavior(tm_wrapper)
        result = cut_in.execute(
            vehicle_id=ego_id,
            frame=frame,
            target_vehicle_id=npc_id,
            gap_distance=3.0,
            speed_boost=120.0,
        )
        print(f"  {result.message}")

        # カットイン完了まで待機
        for i in range(150):
            world.tick()
            frame += 1

        # 追従走行
        print("\nPhase 4: Following...")
        follow = FollowBehavior(tm_wrapper)
        result = follow.execute(
            vehicle_id=ego_id,
            frame=frame,
            target_vehicle_id=npc_id,
            distance=5.0,
            duration_frames=200,
        )
        print(f"  {result.message}")

        # 追従完了まで待機
        for i in range(200):
            world.tick()
            frame += 1

        # 停止
        print("\nPhase 5: Stopping...")
        stop = StopBehavior(tm_wrapper)
        result = stop.execute(
            vehicle_id=ego_id,
            frame=frame,
            duration_frames=50,
        )
        print(f"  {result.message}")

        # 停止完了まで待機
        for i in range(50):
            world.tick()
            frame += 1

        print(f"\nSimulation completed. Total frames: {frame}")

        # ログをファイナライズ
        print("\n=== Finalizing Logs ===")
        stamp_log_path = stamp_logger.finalize()
        command_log_path = command_tracker.finalize()

        print(f"  STAMP log saved: {stamp_log_path}")
        print(f"  Command log saved: {command_log_path}")

        # サマリー出力
        stamp_logger.print_summary()
        command_tracker.print_summary()

    finally:
        # クリーンアップ
        print("\n=== Cleanup ===")
        tm_wrapper.cleanup()

        if "ego_vehicle" in locals():
            ego_vehicle.destroy()
            print("  Ego vehicle destroyed")

        if "npc_vehicle" in locals():
            npc_vehicle.destroy()
            print("  NPC vehicle destroyed")

        # 非同期モードに戻す
        settings = world.get_settings()
        settings.synchronous_mode = False
        world.apply_settings(settings)
        print("  Synchronous mode disabled")

    print("\n=== Example Completed ===")


if __name__ == "__main__":
    main()
