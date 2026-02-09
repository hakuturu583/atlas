#!/usr/bin/env python3
"""
シナリオ作成の使用例

このスクリプトは、scenario_manager.pyを使用してシナリオを作成する例を示します。
"""
from scenario_manager import ScenarioManager


def main():
    """シナリオ作成例"""
    manager = ScenarioManager()

    print("=== 1. 抽象シナリオの作成 ===")
    abstract_uuid = manager.create_abstract_scenario(
        name="highway_follow",
        description="高速道路で前方車両を20m間隔で追従するシナリオ",
        original_prompt="高速道路で前方車両を追従するシナリオ",
        actors=[
            {
                "id": "ego_vehicle",
                "role": "自動運転スタック予定",
                "type": "vehicle",
                "is_autonomous_stack": True
            },
            {
                "id": "lead_vehicle",
                "role": "前方車両",
                "type": "vehicle",
                "is_autonomous_stack": False
            }
        ],
        maneuvers=[
            {
                "actor": "lead_vehicle",
                "action": "一定速度で走行",
                "duration": "10s"
            },
            {
                "actor": "ego_vehicle",
                "action": "前方車両を追従",
                "duration": "10s",
                "conditions": ["距離を20m維持"]
            }
        ]
    )
    print()

    print("=== 2. 論理シナリオの作成 ===")
    logical_uuid = manager.create_logical_scenario(
        parent_abstract_uuid=abstract_uuid,
        name="highway_follow",
        description="高速道路で前方車両を20m間隔で追従する論理シナリオ",
        map_requirements={
            "road_type": "highway",
            "lanes": 3,
            "length_min": 500
        },
        initial_conditions={
            "ego_vehicle": {
                "location": "highway_lane_2",
                "speed": 50.0,
                "distance_behind_lead": 20.0
            },
            "lead_vehicle": {
                "location": "highway_lane_2_front",
                "speed": 80.0
            }
        },
        events=[
            {"time": 0.0, "type": "start_scenario"},
            {"time": 0.0, "type": "lead_vehicle_set_constant_speed", "speed": 80.0},
            {"time": 0.0, "type": "ego_vehicle_follow_lead", "target_distance": 20.0},
            {"time": 10.0, "type": "end_scenario"}
        ]
    )
    print()

    print("=== 3. パラメータの作成（ケース1: Town04） ===")
    param_uuid_1 = manager.create_parameters(
        logical_uuid=logical_uuid,
        carla_config={
            "host": "localhost",
            "port": 2000,
            "map": "Town04"
        },
        vehicles={
            "ego": {
                "spawn": {"x": 100.0, "y": 200.0, "z": 0.3, "yaw": 0.0},
                "initial_speed": 50.0
            },
            "lead": {
                "spawn": {"x": 120.0, "y": 200.0, "z": 0.3, "yaw": 0.0},
                "initial_speed": 80.0
            }
        },
        scenario={
            "duration": 10.0,
            "target_distance": 20.0
        },
        camera={
            "fov": 90.0,
            "image_size_x": 640,
            "image_size_y": 480
        }
    )
    print()

    print("=== 4. パラメータの作成（ケース2: Town05、異なる速度） ===")
    param_uuid_2 = manager.create_parameters(
        logical_uuid=logical_uuid,
        carla_config={
            "host": "localhost",
            "port": 2000,
            "map": "Town05"
        },
        vehicles={
            "ego": {
                "spawn": {"x": 150.0, "y": 250.0, "z": 0.3, "yaw": 90.0},
                "initial_speed": 60.0
            },
            "lead": {
                "spawn": {"x": 170.0, "y": 250.0, "z": 0.3, "yaw": 90.0},
                "initial_speed": 100.0
            }
        },
        scenario={
            "duration": 15.0,
            "target_distance": 25.0
        }
    )
    print()

    print("=== 5. 作成されたファイルの確認 ===")
    print(f"抽象シナリオ: data/scenarios/abstract_{abstract_uuid}.json")
    print(f"論理シナリオ: data/scenarios/logical_{logical_uuid}.json")
    print(f"パラメータ1:   data/scenarios/params_{param_uuid_1}.json")
    print(f"パラメータ2:   data/scenarios/params_{param_uuid_2}.json")
    print()

    print("=== 6. 実行コマンド例 ===")
    print(f"# ケース1を実行:")
    print(f"uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{param_uuid_1}.json")
    print()
    print(f"# ケース2を実行:")
    print(f"uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{param_uuid_2}.json")
    print()

    print("✓ シナリオ作成が完了しました！")
    print("  同じ論理シナリオを2つの異なるパラメータで実行できます。")


if __name__ == "__main__":
    main()
