#!/usr/bin/env python3
"""
OpenDRIVE高度な機能のサンプルスクリプト

交差点、信号機、停止線などの機能を使ったシナリオ例
AgentControllerクラスを使用して車両を制御します
"""

import carla
import time
import sys
from pathlib import Path

# agent_controllerをインポート
sys.path.append(str(Path(__file__).parent.parent))

from opendrive_utils import (
    OpenDriveMap,
    AdvancedFeatures,
    LaneCoord,
)
from agent_controller import AgentController


def demo_traffic_signals(world, advanced):
    """信号機機能のデモ"""
    print("\n" + "=" * 60)
    print("=== 信号機機能のデモ ===")
    print("=" * 60)

    # すべての信号機を取得
    signals = advanced.get_traffic_signals()
    print(f"\n全体で{len(signals)}個の信号機が見つかりました")

    if not signals:
        print("信号機が見つかりませんでした")
        return []

    # 最初の5つを表示
    print("\n最初の5つの信号機:")
    for signal in signals[:5]:
        print(f"  {signal}")

    # 特定の道路上の信号機を取得
    if signals:
        first_signal = signals[0]
        road_signals = advanced.get_signals_on_road(first_signal.road_id)
        print(f"\nRoad {first_signal.road_id} 上の信号機: {len(road_signals)}個")

        # 信号機の位置にマーカーを描画
        for signal in road_signals[:3]:
            transform = advanced.get_signal_transform(signal)
            if transform:
                # 緑色のマーカーを描画
                world.debug.draw_point(
                    transform.location,
                    size=0.3,
                    color=carla.Color(0, 255, 0),
                    life_time=10.0
                )
                print(f"  信号機 {signal.id} の位置: ({transform.location.x:.2f}, {transform.location.y:.2f})")

    return signals


def demo_stop_lines(world, advanced, signals):
    """停止線機能のデモ"""
    print("\n" + "=" * 60)
    print("=== 停止線機能のデモ ===")
    print("=" * 60)

    # 停止線を取得
    stop_lines = advanced.get_stop_lines()
    print(f"\n{len(stop_lines)}個の停止線が見つかりました")

    if not stop_lines:
        print("停止線が見つかりませんでした")
        return

    # 最初の5つを表示
    print("\n最初の5つの停止線:")
    for stop_line in stop_lines[:5]:
        print(f"  {stop_line}")
        if stop_line.signal_id:
            print(f"    対応する信号機: {stop_line.signal_id}")

    # 停止線の位置にマーカーを描画
    for stop_line in stop_lines[:10]:
        transform = advanced.get_stop_line_transform(stop_line)
        if transform:
            # 赤色のマーカーを描画
            world.debug.draw_point(
                transform.location,
                size=0.2,
                color=carla.Color(255, 0, 0),
                life_time=10.0
            )


def demo_junctions(world, advanced):
    """交差点機能のデモ"""
    print("\n" + "=" * 60)
    print("=== 交差点機能のデモ ===")
    print("=" * 60)

    # すべての交差点を取得
    junctions = advanced.get_junctions()
    print(f"\n{len(junctions)}個の交差点が見つかりました")

    if not junctions:
        print("交差点が見つかりませんでした")
        return None

    # 最初の3つを表示
    print("\n最初の3つの交差点:")
    for junction_id, junction in list(junctions.items())[:3]:
        print(f"  {junction}")
        for conn in junction.connections[:2]:  # 最初の2つの接続
            print(f"    {conn}")

    # 最初の交差点の中心位置を取得
    first_junction_id = list(junctions.keys())[0]
    center_transform = advanced.get_junction_center_transform(first_junction_id)

    if center_transform:
        print(f"\n交差点{first_junction_id}の中心位置:")
        print(f"  ({center_transform.location.x:.2f}, {center_transform.location.y:.2f})")

        # 青色のマーカーを描画
        world.debug.draw_point(
            center_transform.location,
            size=0.5,
            color=carla.Color(0, 0, 255),
            life_time=10.0
        )

    return first_junction_id, junctions


def demo_spawn_scenarios(world, client, advanced, signals):
    """信号機を使ったスポーンシナリオ"""
    print("\n" + "=" * 60)
    print("=== 信号機シナリオ ===")
    print("=" * 60)

    if not signals:
        print("信号機が見つからないため、スキップします")
        return [], None

    spawned_vehicles = []
    vehicle_ids = []
    blueprint = world.get_blueprint_library().filter('vehicle.tesla.model3')[0]

    # AgentControllerを初期化
    controller = AgentController(
        client=client,
        scenario_uuid="advanced_features_demo",
        enable_logging=True,
    )

    # 最初の信号機の手前に車両をスポーン
    signal = signals[0]
    print(f"\n信号機 {signal.id} (Road {signal.road_id}) を使用")

    # 利用可能なレーンを取得
    od_map = advanced.od_map
    available_lanes = od_map.get_available_lanes(signal.road_id, signal.s)

    if available_lanes:
        # 進行方向のレーンを選択
        lane_id = None
        if signal.orientation == '+':
            # 負のレーン（右側）
            lane_id = [lid for lid in available_lanes if lid < 0]
            lane_id = lane_id[0] if lane_id else None
        else:
            # 正のレーン（左側）
            lane_id = [lid for lid in available_lanes if lid > 0]
            lane_id = lane_id[0] if lane_id else None

        if lane_id:
            # 信号機の10m手前に車両をスポーン
            transform = advanced.get_spawn_before_signal(signal, lane_id, distance_before=10.0)

            if transform:
                try:
                    vehicle = world.spawn_actor(blueprint, transform)
                    spawned_vehicles.append(vehicle)

                    # AgentControllerに登録
                    vehicle_id = controller.register_vehicle(
                        vehicle=vehicle,
                        auto_lane_change=False,
                        distance_to_leading=5.0,
                        speed_percentage=60.0,
                        ignore_lights=False,  # 信号を守る
                    )
                    vehicle_ids.append(vehicle_id)

                    print(f"✓ 信号機の10m手前に車両をスポーン: ({transform.location.x:.2f}, {transform.location.y:.2f})")
                    print(f"  AgentControllerに登録: vehicle_id={vehicle_id}")
                except RuntimeError as e:
                    print(f"✗ スポーン失敗: {e}")

            # さらに20m手前に2台目
            transform2 = advanced.get_spawn_before_signal(signal, lane_id, distance_before=30.0)
            if transform2:
                try:
                    vehicle2 = world.spawn_actor(blueprint, transform2)
                    spawned_vehicles.append(vehicle2)

                    # AgentControllerに登録
                    vehicle_id2 = controller.register_vehicle(
                        vehicle=vehicle2,
                        auto_lane_change=False,
                        distance_to_leading=5.0,
                        speed_percentage=60.0,
                        ignore_lights=False,  # 信号を守る
                    )
                    vehicle_ids.append(vehicle_id2)

                    print(f"✓ 信号機の30m手前に車両をスポーン: ({transform2.location.x:.2f}, {transform2.location.y:.2f})")
                    print(f"  AgentControllerに登録: vehicle_id={vehicle_id2}")
                except RuntimeError as e:
                    print(f"✗ スポーン失敗: {e}")

    print(f"\n✓ {len(vehicle_ids)}台の車両をAgentControllerで制御中")
    return spawned_vehicles, controller


def demo_junction_navigation(world, advanced, junction_id, junctions):
    """交差点ナビゲーションのデモ"""
    print("\n" + "=" * 60)
    print("=== 交差点ナビゲーション ===")
    print("=" * 60)

    if junction_id is None or not junctions:
        print("交差点が見つからないため、スキップします")
        return

    junction = junctions[junction_id]
    print(f"\n交差点 {junction.name} (ID: {junction_id})")

    # 最初の接続を使用
    if junction.connections:
        connection = junction.connections[0]
        print(f"\n接続: {connection}")

        # 流入点を取得
        entry_points = advanced.get_junction_entry_points(
            junction_id,
            connection.incoming_road
        )
        print(f"流入点: {len(entry_points)}箇所")

        # 流入点にマーカーを描画
        for i, transform in enumerate(entry_points[:3]):
            world.debug.draw_point(
                transform.location,
                size=0.3,
                color=carla.Color(255, 255, 0),
                life_time=10.0
            )
            print(f"  流入点{i+1}: ({transform.location.x:.2f}, {transform.location.y:.2f})")


def main():
    # CARLAに接続
    print("CARLAサーバーに接続中...")
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.get_world()
    print(f"マップ: {world.get_map().name}")

    # OpenDRIVEマップと高度な機能を初期化
    print("\nOpenDRIVEマップを読み込み中...")
    od_map = OpenDriveMap(world)
    advanced = AdvancedFeatures(od_map)

    controller = None
    spawned_vehicles = []

    try:
        # 各デモを実行
        signals = demo_traffic_signals(world, advanced)
        demo_stop_lines(world, advanced, signals)
        junction_id, junctions = demo_junctions(world, advanced)
        spawned_vehicles, controller = demo_spawn_scenarios(world, client, advanced, signals)
        demo_junction_navigation(world, advanced, junction_id, junctions)

        # 結果表示
        print("\n" + "=" * 60)
        print("=== デモ完了 ===")
        print("=" * 60)
        print(f"\nスポーンした車両: {len(spawned_vehicles)}台")
        print("マーカーは10秒間表示されます")

        if spawned_vehicles:
            print("\n10秒間待機します（スペクテーターで確認してください）...")
            time.sleep(10)

    finally:
        # クリーンアップ
        if spawned_vehicles:
            print("\n車両を削除中...")
            for vehicle in spawned_vehicles:
                vehicle.destroy()
            print("✓ すべての車両を削除しました")

        # AgentControllerのログをファイナライズ
        if controller:
            print("\nログを保存中...")
            stamp_log, command_log = controller.finalize()
            if stamp_log:
                print(f"  STAMP log: {stamp_log}")
            if command_log:
                print(f"  Command log: {command_log}")
            controller.cleanup()

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
