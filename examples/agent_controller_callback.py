"""
agent_controller トリガー関数ベース使用例

AgentControllerのトリガー関数を使って、
シナリオを宣言的に記述する方法を示します。
world.tick()は自動的に呼ばれ、トリガー条件が満たされたときに
コールバックが実行されます。
"""

import sys
from pathlib import Path

# agent_controllerをインポート
sys.path.append(str(Path(__file__).parent.parent))

from agent_controller import AgentController
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord


def main():
    """メイン関数"""
    print("=== agent_controller Callback Example ===\n")

    with AgentController(
        scenario_uuid="callback_example",
        carla_host="localhost",
        carla_port=2000,
        synchronous_mode=True,
        fixed_delta_seconds=0.05,  # 20 FPS
    ) as controller:
        print(f"Connected to CARLA: {controller.get_map().name}\n")

        # 車両をスポーン（自動登録）
        print("Spawning vehicles...")

        # Ego車両
        lane_coord_1 = LaneCoord(road_id=10, lane_id=-1, s=50.0)
        ego_vehicle, ego_id = controller.spawn_vehicle_from_lane(
            "vehicle.tesla.model3",
            lane_coord_1,
            auto_lane_change=False,
            distance_to_leading=5.0,
            speed_percentage=80.0,
        )
        print(f"  Ego vehicle spawned: ID={ego_id}")

        # NPC車両
        lane_coord_2 = LaneCoord(road_id=10, lane_id=-1, s=80.0)
        npc_vehicle, npc_id = controller.spawn_vehicle_from_lane(
            "vehicle.tesla.model3",
            lane_coord_2,
            auto_lane_change=True,
            distance_to_leading=3.0,
            speed_percentage=60.0,
        )
        print(f"  NPC vehicle spawned: ID={npc_id}")

        # ========================================
        # パターン1: トリガー関数を使用（推奨）
        # ========================================
        print("\n=== Pattern 1: Using Trigger Functions (Recommended) ===")

        # フレーム100でレーンチェンジ
        def on_frame_100():
            print("\n→ Frame 100: Lane change...")
            result = controller.lane_change(
                vehicle_id=ego_id,
                direction="left",
                duration_frames=100,
            )
            print(f"  {result.message}")

        # フレーム200でカットイン
        def on_frame_200():
            print("\n→ Frame 200: Cut in...")
            result = controller.cut_in(
                vehicle_id=ego_id,
                target_vehicle_id=npc_id,
                gap_distance=3.0,
                speed_boost=120.0,
            )
            print(f"  {result.message}")

        # フレーム350で追従
        def on_frame_350():
            print("\n→ Frame 350: Following...")
            result = controller.follow(
                vehicle_id=ego_id,
                target_vehicle_id=npc_id,
                distance=5.0,
                duration_frames=200,
            )
            print(f"  {result.message}")

        # フレーム550で停止
        def on_frame_550():
            print("\n→ Frame 550: Stopping...")
            result = controller.stop(
                vehicle_id=ego_id,
                duration_frames=50,
            )
            print(f"  {result.message}")

        # トリガー関数でコールバックを登録
        controller.register_callback(
            controller.when_timestep_equals(100), on_frame_100
        )
        controller.register_callback(
            controller.when_timestep_equals(200), on_frame_200
        )
        controller.register_callback(
            controller.when_timestep_equals(350), on_frame_350
        )
        controller.register_callback(
            controller.when_timestep_equals(550), on_frame_550
        )

        # より高度なトリガー例
        print("\n=== Advanced Trigger Examples ===")

        # 車両間距離が10m以下になったら警告（リピート）
        controller.register_callback(
            controller.when_distance_between(ego_id, npc_id, 10.0, operator="less"),
            lambda: print("⚠ Warning: Distance less than 10m!"),
            one_shot=False,  # リピート実行
        )

        # 速度が100km/hを超えたら警告
        controller.register_callback(
            controller.when_speed_greater_than(ego_id, 100.0),
            lambda: print("⚠ Warning: Speed exceeded 100 km/h!"),
        )

        # シミュレーション実行（自動的にworld.tick()が呼ばれる）
        controller.run_simulation(total_frames=600)

        # 車両を破棄
        controller.destroy_vehicle(ego_id)
        controller.destroy_vehicle(npc_id)

    print("\n=== Example Completed ===")


def example_pattern_2():
    """パターン2: on_tickコールバックを使用"""
    print("\n=== Pattern 2: Using on_tick callback ===")

    with AgentController(
        scenario_uuid="callback_example_2",
        carla_host="localhost",
        carla_port=2000,
    ) as controller:
        world = controller.world

        # 車両をスポーン・登録（省略）
        # ego_id, npc_id = ...

        # 毎フレーム呼ばれるコールバック
        def on_tick(frame: int):
            if frame == 100:
                print(f"\n→ Frame {frame}: Lane change...")
                controller.lane_change(ego_id, direction="left")

            elif frame == 200:
                print(f"\n→ Frame {frame}: Cut in...")
                controller.cut_in(ego_id, target_vehicle_id=npc_id)

            elif frame == 350:
                print(f"\n→ Frame {frame}: Following...")
                controller.follow(ego_id, target_vehicle_id=npc_id)

            elif frame == 550:
                print(f"\n→ Frame {frame}: Stopping...")
                controller.stop(ego_id)

        # シミュレーション実行（on_tickが毎フレーム呼ばれる）
        controller.run_simulation(total_frames=600, on_tick=on_tick)


if __name__ == "__main__":
    # パターン1を実行
    main()

    # パターン2も試したい場合はコメント解除
    # example_pattern_2()
