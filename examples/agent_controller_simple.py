"""
agent_controller 簡易使用例

AgentControllerクラスを使った最もシンプルな使い方を示します。
CARLAへの接続、同期モード設定、ログ保存、クリーンアップがすべて自動化されています。
"""

import sys
from pathlib import Path

# agent_controllerをインポート
sys.path.append(str(Path(__file__).parent.parent))

from agent_controller import AgentController, VehicleConfig
from opendrive_utils import LaneCoord


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
        print(f"Connected to CARLA: {controller.get_map().name}\n")
        try:
            # 車両をスポーン（自動登録）
            print("Spawning vehicles...")

            # 車両設定
            ego_config = VehicleConfig(
                auto_lane_change=False,
                distance_to_leading=5.0,
                speed_percentage=80.0,
            )
            npc_config = VehicleConfig(
                auto_lane_change=True,
                distance_to_leading=3.0,
                speed_percentage=60.0,
            )

            # Ego車両
            lane_coord_1 = LaneCoord(road_id=10, lane_id=-1, s=50.0)
            ego_vehicle, ego_id = controller.spawn_vehicle_from_lane(
                "vehicle.tesla.model3",
                lane_coord_1,
                config=ego_config,
            )
            print(f"  Ego vehicle spawned: ID={ego_id}")

            # NPC車両
            lane_coord_2 = LaneCoord(road_id=10, lane_id=-1, s=80.0)
            npc_vehicle, npc_id = controller.spawn_vehicle_from_lane(
                "vehicle.tesla.model3",
                lane_coord_2,
                config=npc_config,
            )
            print(f"  NPC vehicle spawned: ID={npc_id}")

            # シナリオをトリガー関数で定義（フレーム管理不要！）
            print("\n=== Defining Scenario ===\n")

            # フレーム100: レーンチェンジ
            controller.register_callback(
                controller.when_timestep_equals(100),
                lambda: print("Phase 2: Lane change...")
                or controller.lane_change(ego_id, direction="left", duration_frames=100),
            )

            # フレーム200: カットイン
            controller.register_callback(
                controller.when_timestep_equals(200),
                lambda: print("\nPhase 3: Cut in...")
                or controller.cut_in(
                    ego_id,
                    target_vehicle_id=npc_id,
                    gap_distance=3.0,
                    speed_boost=120.0,
                ),
            )

            # フレーム350: 追従
            controller.register_callback(
                controller.when_timestep_equals(350),
                lambda: print("\nPhase 4: Following...")
                or controller.follow(
                    ego_id, target_vehicle_id=npc_id, distance=5.0, duration_frames=200
                ),
            )

            # フレーム550: 停止
            controller.register_callback(
                controller.when_timestep_equals(550),
                lambda: print("\nPhase 5: Stopping...")
                or controller.stop(ego_id, duration_frames=50),
            )

            # シミュレーション実行（world.tick()は自動的に呼ばれる）
            controller.run_simulation(total_frames=600)

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
