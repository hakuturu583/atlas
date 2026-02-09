#!/usr/bin/env python3
"""
赤信号からの再発進シナリオ生成スクリプト

赤信号で停止後、信号が青に変わって再発進するシナリオ
"""
from scenario_manager import ScenarioManager

def main():
    manager = ScenarioManager()

    # 1. 抽象シナリオを作成
    print("=" * 60)
    print("1. 抽象シナリオを作成")
    print("=" * 60)

    abstract_uuid = manager.create_abstract_scenario(
        name="赤信号からの再発進シナリオ",
        description="赤信号で停止後、青信号に変わって再発進する",
        original_prompt="赤信号で停止し、信号が青に変わったら再発進するシナリオ",
        environment={
            "location_type": "urban_intersection",
            "features": ["traffic_light", "road", "stop_line", "buildings"]
        },
        actors=[
            {
                "id": "ego_vehicle",
                "type": "vehicle",
                "role": "自動運転車両"
            },
            {
                "id": "traffic_light",
                "type": "traffic_signal",
                "role": "交差点の信号機（赤→青）"
            },
            {
                "id": "chase_camera",
                "type": "camera",
                "role": "車両を追従する独立カメラ"
            }
        ],
        scenario_type="intersection_restart_from_red"
    )

    print()

    # 2. 論理シナリオを作成
    print("=" * 60)
    print("2. 論理シナリオを作成（パラメータ空間定義）")
    print("=" * 60)

    logical_uuid = manager.create_logical_scenario(
        parent_abstract_uuid=abstract_uuid,
        name="赤信号からの再発進シナリオ",
        description="赤信号停止後の再発進動作のパラメータ空間",
        parameter_space={
            "ego_vehicle": {
                "initial_speed": {
                    "type": "float",
                    "unit": "km/h",
                    "distribution": "uniform",
                    "min": 30.0,
                    "max": 50.0,
                    "description": "接近時の初期速度"
                },
                "distance_to_light": {
                    "type": "float",
                    "unit": "m",
                    "distribution": "uniform",
                    "min": 50.0,
                    "max": 100.0,
                    "description": "信号機までの初期距離"
                },
                "acceleration": {
                    "type": "float",
                    "unit": "m/s^2",
                    "distribution": "uniform",
                    "min": 1.5,
                    "max": 3.0,
                    "description": "再発進時の加速度"
                }
            },
            "traffic_light": {
                "red_duration": {
                    "type": "float",
                    "unit": "s",
                    "distribution": "uniform",
                    "min": 5.0,
                    "max": 10.0,
                    "description": "赤信号の継続時間"
                },
                "green_duration": {
                    "type": "float",
                    "unit": "s",
                    "distribution": "constant",
                    "value": 15.0,
                    "description": "青信号の継続時間"
                }
            },
            "scenario": {
                "duration": {
                    "type": "float",
                    "unit": "s",
                    "distribution": "constant",
                    "value": 30.0,
                    "description": "シナリオの総時間"
                }
            },
            "camera": {
                "offset_x": {
                    "type": "float",
                    "unit": "m",
                    "distribution": "constant",
                    "value": -6.0,
                    "description": "車両後方へのオフセット"
                },
                "offset_y": {
                    "type": "float",
                    "unit": "m",
                    "distribution": "constant",
                    "value": 0.0,
                    "description": "左右のオフセット"
                },
                "offset_z": {
                    "type": "float",
                    "unit": "m",
                    "distribution": "constant",
                    "value": 3.0,
                    "description": "高さのオフセット"
                },
                "pitch": {
                    "type": "float",
                    "unit": "deg",
                    "distribution": "constant",
                    "value": -20.0,
                    "description": "カメラの下向き角度"
                },
                "fov": {
                    "type": "float",
                    "unit": "deg",
                    "distribution": "constant",
                    "value": 90.0,
                    "description": "視野角"
                },
                "image_size_x": {
                    "type": "int",
                    "unit": "px",
                    "distribution": "constant",
                    "value": 1280,
                    "description": "画像の幅"
                },
                "image_size_y": {
                    "type": "int",
                    "unit": "px",
                    "distribution": "constant",
                    "value": 720,
                    "description": "画像の高さ"
                },
                "fps": {
                    "type": "int",
                    "unit": "fps",
                    "distribution": "constant",
                    "value": 20,
                    "description": "フレームレート"
                }
            }
        }
    )

    print()

    # 3. パラメータを3回サンプリング
    print("=" * 60)
    print("3. パラメータを3回サンプリング")
    print("=" * 60)

    parameter_uuids = []
    for i in range(3):
        print(f"\n--- パターン {i+1} ---")
        parameter_uuid = manager.sample_parameters(
            logical_uuid=logical_uuid,
            carla_config={
                "host": "localhost",
                "port": 2000,
                "map": "Town10HD_Opt",
                "vehicle_type": "vehicle.taxi.ford"
            },
            seed=100 + i  # 異なるシードで異なるパラメータを生成
        )
        parameter_uuids.append(parameter_uuid)

        # サンプリング結果を表示
        params = manager.get_parameters(logical_uuid, parameter_uuid)
        print(f"✓ パラメータUUID: {parameter_uuid}")
        print(f"  初期速度: {params['sampled_values']['ego_vehicle']['initial_speed']:.1f} km/h")
        print(f"  信号機までの距離: {params['sampled_values']['ego_vehicle']['distance_to_light']:.1f} m")
        print(f"  加速度: {params['sampled_values']['ego_vehicle']['acceleration']:.2f} m/s²")
        print(f"  赤信号継続時間: {params['sampled_values']['traffic_light']['red_duration']:.1f} s")

    print()

    # 4. 結果のサマリー
    print("=" * 60)
    print("4. 作成完了")
    print("=" * 60)
    print(f"抽象シナリオUUID: {abstract_uuid}")
    print(f"論理シナリオUUID: {logical_uuid}")
    print(f"パラメータUUID:")
    for i, uuid in enumerate(parameter_uuids, 1):
        print(f"  パターン{i}: {uuid}")
    print()
    print("次のステップ:")
    print(f"1. Pythonスクリプトを生成: scenarios/{logical_uuid}.py")
    print(f"2. 各パラメータでシナリオを実行")
    print(f"   例: uv run python scenarios/{logical_uuid}.py --logical-uuid {logical_uuid} --parameter-uuid {parameter_uuids[0]}")

    return logical_uuid, parameter_uuids

if __name__ == "__main__":
    main()
