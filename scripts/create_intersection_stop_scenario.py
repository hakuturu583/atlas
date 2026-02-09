#!/usr/bin/env python3
"""
交差点停止シナリオ生成スクリプト

信号機が赤の状態で交差点に接近し、停止線で停止するシナリオ
"""
from scenario_manager import ScenarioManager

def main():
    manager = ScenarioManager()

    # 1. 抽象シナリオを作成
    print("=" * 60)
    print("1. 抽象シナリオを作成")
    print("=" * 60)

    abstract_uuid = manager.create_abstract_scenario(
        name="交差点停止シナリオ",
        description="赤信号の交差点に接近して停止線で停止する",
        original_prompt="信号機が赤の状態で交差点に接近し、停止線で停止するシナリオ",
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
                "role": "交差点の信号機（赤）"
            },
            {
                "id": "chase_camera",
                "type": "camera",
                "role": "車両を追従する独立カメラ"
            }
        ],
        scenario_type="intersection_stop"
    )

    print()

    # 2. 論理シナリオを作成
    print("=" * 60)
    print("2. 論理シナリオを作成（パラメータ空間定義）")
    print("=" * 60)

    logical_uuid = manager.create_logical_scenario(
        parent_abstract_uuid=abstract_uuid,
        name="交差点停止シナリオ",
        description="赤信号での停止動作のパラメータ空間",
        parameter_space={
            "ego_vehicle": {
                "initial_speed": {
                    "type": "float",
                    "unit": "km/h",
                    "distribution": "uniform",
                    "min": 25.0,
                    "max": 45.0,
                    "description": "接近時の初期速度"
                },
                "distance_to_light": {
                    "type": "float",
                    "unit": "m",
                    "distribution": "uniform",
                    "min": 40.0,
                    "max": 80.0,
                    "description": "信号機までの初期距離"
                }
            },
            "traffic_light": {
                "red_duration": {
                    "type": "float",
                    "unit": "s",
                    "distribution": "constant",
                    "value": 10.0,
                    "description": "赤信号の継続時間（停止を確認するため長めに）"
                }
            },
            "scenario": {
                "duration": {
                    "type": "float",
                    "unit": "s",
                    "distribution": "constant",
                    "value": 15.0,
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

    # 3. パラメータをサンプリング
    print("=" * 60)
    print("3. パラメータをサンプリング")
    print("=" * 60)

    parameter_uuid = manager.sample_parameters(
        logical_uuid=logical_uuid,
        carla_config={
            "host": "localhost",
            "port": 2000,
            "map": "Town10HD_Opt",
            "vehicle_type": "vehicle.taxi.ford"
        },
        seed=42  # 再現性のため
    )

    # サンプリング結果を表示
    params = manager.get_parameters(logical_uuid, parameter_uuid)
    print("\n✓ サンプリングされたパラメータ:")
    print(f"  初期速度: {params['sampled_values']['ego_vehicle']['initial_speed']:.1f} km/h")
    print(f"  信号機までの距離: {params['sampled_values']['ego_vehicle']['distance_to_light']:.1f} m")
    print(f"  赤信号継続時間: {params['sampled_values']['traffic_light']['red_duration']:.1f} s")

    print()

    # 4. 結果のサマリー
    print("=" * 60)
    print("4. 作成完了")
    print("=" * 60)
    print(f"抽象シナリオUUID: {abstract_uuid}")
    print(f"論理シナリオUUID: {logical_uuid}")
    print(f"パラメータUUID: {parameter_uuid}")
    print()
    print("次のステップ:")
    print(f"1. Pythonスクリプトを生成: scenarios/{logical_uuid}.py")
    print(f"2. パラメータファイルを確認: data/scenarios/logical_{logical_uuid}_parameters.json")
    print(f"3. シナリオを実行して動画を記録")

    return logical_uuid, parameter_uuid

if __name__ == "__main__":
    main()
