"""
agent_controller メトリクス使用例

AgentControllerの安全性メトリクス機能を使って、
TTC、急ブレーキ、急加速などの自動運転評価指標を自動計算する方法を示します。
"""

import sys
from pathlib import Path

# agent_controllerをインポート
sys.path.append(str(Path(__file__).parent.parent))

from agent_controller import (
    AgentController,
    VehicleConfig,
    MetricsConfig,
    NORMAL_DRIVER,
    AGGRESSIVE_DRIVER,
)
from opendrive_utils import LaneCoord


def main():
    """メイン関数"""
    print("=== agent_controller Metrics Example ===\n")

    # メトリクス設定をカスタマイズ
    metrics_config = MetricsConfig(
        ttc_threshold=3.0,  # TTC閾値: 3秒以下で警告
        sudden_braking_threshold=5.0,  # 急ブレーキ: 5 m/s^2以上で検出
        sudden_acceleration_threshold=4.0,  # 急加速: 4 m/s^2以上で検出
        lateral_acceleration_threshold=3.0,  # 横方向加速度: 3 m/s^2以上で検出
        jerk_threshold=10.0,  # ジャーク: 10 m/s^3以上で検出
        min_distance_threshold=2.0,  # 最小車間距離: 2m以下で警告
        speed_violation_margin=10.0,  # 速度違反マージン: +10 km/h
    )

    # メトリクス計算を有効化
    with AgentController(
        scenario_uuid="metrics_example",
        carla_host="localhost",
        carla_port=2000,
        synchronous_mode=True,
        fixed_delta_seconds=0.05,  # 20 FPS
        enable_metrics=True,  # メトリクス有効化
        metrics_config=metrics_config,  # カスタム設定
    ) as controller:
        print(f"Connected to CARLA: {controller.get_map().name}\n")

        # 車両をスポーン
        print("Spawning vehicles...\n")

        # Ego車両（通常のドライバー）
        ego_config = NORMAL_DRIVER
        lane_coord_1 = LaneCoord(road_id=10, lane_id=-1, s=50.0)
        ego_vehicle, ego_id = controller.spawn_vehicle_from_lane(
            "vehicle.tesla.model3",
            lane_coord_1,
            config=ego_config,
        )
        print(f"  Ego vehicle spawned: ID={ego_id}")

        # NPC車両（アグレッシブなドライバー）
        npc_config = AGGRESSIVE_DRIVER
        lane_coord_2 = LaneCoord(road_id=10, lane_id=-1, s=80.0)
        npc_vehicle, npc_id = controller.spawn_vehicle_from_lane(
            "vehicle.tesla.model3",
            lane_coord_2,
            config=npc_config,
        )
        print(f"  NPC vehicle spawned: ID={npc_id}")

        # シナリオを定義
        print("\n=== Defining Scenario ===\n")

        # フレーム100: Egoが加速してNPCに接近
        controller.register_callback(
            controller.when_timestep_equals(100),
            lambda: print("\nPhase 1: Ego accelerating...")
            or controller.tm_wrapper.set_speed_percentage(ego_id, 150.0, frame=100),
        )

        # フレーム200: Egoが急ブレーキ
        controller.register_callback(
            controller.when_timestep_equals(200),
            lambda: print("\nPhase 2: Ego braking hard...")
            or controller.stop(ego_id, duration_frames=50),
        )

        # フレーム300: Egoが再加速
        controller.register_callback(
            controller.when_timestep_equals(300),
            lambda: print("\nPhase 3: Ego re-accelerating...")
            or controller.tm_wrapper.set_speed_percentage(ego_id, 120.0, frame=300),
        )

        # フレーム400: Egoがレーンチェンジ（横方向加速度を発生）
        controller.register_callback(
            controller.when_timestep_equals(400),
            lambda: print("\nPhase 4: Ego lane changing...")
            or controller.lane_change(ego_id, direction="left", duration_frames=100),
        )

        # フレーム550: Egoが追従（TTC計測）
        controller.register_callback(
            controller.when_timestep_equals(550),
            lambda: print("\nPhase 5: Ego following NPC...")
            or controller.follow(ego_id, target_vehicle_id=npc_id, distance=3.0),
        )

        # シミュレーション実行（メトリクスは自動的に計算される）
        controller.run_simulation(total_frames=700)

        # メトリクスを取得
        metrics = controller.get_metrics()
        if metrics:
            print("\n" + "=" * 60)
            print("  Metrics Analysis")
            print("=" * 60)

            # イベントをタイプ別に表示
            event_types = [
                "sudden_braking",
                "sudden_acceleration",
                "high_jerk",
                "low_ttc",
                "min_distance_violation",
            ]

            for event_type in event_types:
                events = metrics.get_events_by_type(event_type)
                if events:
                    print(f"\n【{event_type}】")
                    for event in events[:5]:  # 最初の5件のみ表示
                        print(
                            f"  Frame {event.frame}: {event.description} at ({event.location[0]:.1f}, {event.location[1]:.1f})"
                        )
                    if len(events) > 5:
                        print(f"  ... and {len(events) - 5} more events")

            # 意味論的カバレッジを表示
            coverage = controller.get_semantic_coverage()
            if coverage:
                print(f"\n【意味論的カバレッジ】")
                for event_type, occurred in coverage.items():
                    status = "✓" if occurred else "✗"
                    print(f"  {status} {event_type}")

                coverage_rate = sum(coverage.values()) / len(coverage) * 100
                print(f"\n  カバレッジ率: {coverage_rate:.1f}%")

    # メトリクスログはdata/logs/metrics/に保存される
    print("\n=== Example Completed ===")
    print(f"Metrics log saved to: data/logs/metrics/{controller.scenario_uuid}_metrics.json")


if __name__ == "__main__":
    main()
