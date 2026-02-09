#!/usr/bin/env python3
"""シナリオ階層構造の完全な使用例

dataclassベースのシナリオモデルを使った完全なワークフロー:
1. 抽象シナリオの作成
2. 論理シナリオの作成
3. パラメータのサンプリング
4. ファイルへの保存
5. ファイルからの読み込み
"""

from pathlib import Path
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.scenario_builder import (
    AbstractScenarioBuilder,
    ActorType,
    LocationType,
    LogicalScenarioBuilder,
    create_uniform_param,
    create_constant_param,
    create_choice_param,
    sample_parameter_set,
)
from app.models.scenario_hierarchy import CarlaConfig
from app.models.scenario_serializer import (
    save_abstract_scenario,
    save_logical_scenario,
    save_parameter_set,
    load_abstract_scenario,
    load_logical_scenario,
    load_parameter_set,
)


def main():
    print("=" * 60)
    print("シナリオ階層構造の使用例")
    print("=" * 60)

    # ========================================
    # 1. 抽象シナリオの作成
    # ========================================
    print("\n[1/5] 抽象シナリオを作成中...")

    abstract = (
        AbstractScenarioBuilder(
            name="交差点信号機シナリオ",
            description="市街地の交差点で信号機に従って停止・発進する",
            original_prompt="信号機が赤から青に変わったら車両が発進するシナリオを作成してください"
        )
        .with_environment(
            location_type=LocationType.INTERSECTION,
            features=["traffic_light", "road", "buildings", "crosswalk"],
            weather="Clear",
            time_of_day="Noon"
        )
        .add_actor(
            actor_id="ego_vehicle",
            actor_type=ActorType.VEHICLE,
            role="自動運転車両",
            is_autonomous_stack=True,
            metadata={"color": "blue", "model": "tesla_model3"}
        )
        .add_actor(
            actor_id="npc_vehicle",
            actor_type=ActorType.VEHICLE,
            role="前方車両",
            is_autonomous_stack=False
        )
        .add_maneuver(
            actor_id="ego_vehicle",
            action="信号機に従って停止・発進",
            duration="20s",
            conditions=["信号が赤の時は停止線で停止", "信号が青になったら発進"]
        )
        .add_maneuver(
            actor_id="npc_vehicle",
            action="一定速度で走行",
            duration="20s"
        )
        .with_scenario_type("traffic_light_compliance")
        .with_metadata(priority="high", tags=["traffic", "intersection"])
        .build()
    )

    print(f"  ✓ 抽象シナリオ作成完了")
    print(f"    UUID: {abstract.uuid}")
    print(f"    名前: {abstract.name}")
    print(f"    アクター数: {len(abstract.actors)}")
    print(f"    マニューバー数: {len(abstract.maneuvers)}")

    # ========================================
    # 2. 論理シナリオの作成
    # ========================================
    print("\n[2/5] 論理シナリオを作成中...")

    logical = (
        LogicalScenarioBuilder(
            parent_abstract_uuid=abstract.uuid,
            name="交差点信号機シナリオ（パラメータ空間）",
            description="パラメータの定義と分布"
        )
        .add_parameter_group(
            "ego_vehicle",
            {
                "initial_speed": create_uniform_param(
                    "initial_speed",
                    min_val=20.0,
                    max_val=40.0,
                    unit="km/h",
                    description="初期速度"
                ),
                "distance_to_light": create_uniform_param(
                    "distance_to_light",
                    min_val=30.0,
                    max_val=70.0,
                    unit="m",
                    description="信号機までの距離"
                ),
                "reaction_time": create_uniform_param(
                    "reaction_time",
                    min_val=0.3,
                    max_val=0.8,
                    unit="s",
                    description="反応時間"
                )
            }
        )
        .add_parameter_group(
            "traffic_light",
            {
                "red_duration": create_uniform_param(
                    "red_duration",
                    min_val=3.0,
                    max_val=7.0,
                    unit="s",
                    description="赤信号の継続時間"
                ),
                "yellow_duration": create_constant_param(
                    "yellow_duration",
                    value=3.0,
                )
            }
        )
        .add_parameter_group(
            "npc_vehicle",
            {
                "speed": create_uniform_param(
                    "speed",
                    min_val=30.0,
                    max_val=50.0,
                    unit="km/h"
                )
            }
        )
        .add_parameter_group(
            "camera",
            {
                "offset_x": create_constant_param("offset_x", -6.0),
                "offset_z": create_constant_param("offset_z", 3.0),
                "pitch": create_constant_param("pitch", -20.0)
            }
        )
        .add_parameter_group(
            "environment",
            {
                "weather": create_choice_param(
                    "weather",
                    choices=["Clear", "Cloudy", "WetCloudy"],
                    description="天候"
                )
            }
        )
        .with_metadata(version="1.0")
        .build()
    )

    print(f"  ✓ 論理シナリオ作成完了")
    print(f"    UUID: {logical.uuid}")
    print(f"    親UUID: {logical.parent_abstract_uuid}")
    print(f"    パラメータグループ数: {len(logical.parameter_space.groups)}")

    # ========================================
    # 3. パラメータのサンプリング
    # ========================================
    print("\n[3/5] パラメータをサンプリング中...")

    # 複数のパラメータセットを生成
    param_sets = []
    for i in range(3):
        param_set = sample_parameter_set(
            logical,
            carla_config=CarlaConfig(
                map="Town10HD_Opt",
                vehicle_type="vehicle.taxi.ford",
                port=2000 + i  # 各セットで異なるポート
            ),
            seed=42 + i
        )
        param_sets.append(param_set)

        print(f"  ✓ パラメータセット {i+1} 作成完了")
        print(f"    UUID: {param_set.uuid}")
        print(f"    シード: {param_set.seed}")
        print(f"    サンプル値:")
        for group_name, group_values in param_set.sampled_values.items():
            print(f"      {group_name}:")
            for param_name, value in group_values.items():
                print(f"        - {param_name}: {value}")

    # ========================================
    # 4. ファイルへの保存
    # ========================================
    print("\n[4/5] ファイルに保存中...")

    base_dir = Path("data/scenarios")
    base_dir.mkdir(parents=True, exist_ok=True)

    # 抽象シナリオを保存
    abstract_file = base_dir / f"abstract_{abstract.uuid}.json"
    save_abstract_scenario(abstract, abstract_file)
    print(f"  ✓ 抽象シナリオ保存: {abstract_file}")

    # 論理シナリオを保存
    logical_file = base_dir / f"logical_{logical.uuid}.json"
    save_logical_scenario(logical, logical_file)
    print(f"  ✓ 論理シナリオ保存: {logical_file}")

    # パラメータセットを保存
    for param_set in param_sets:
        param_file = base_dir / f"params_{param_set.uuid}.json"
        save_parameter_set(param_set, param_file)
        print(f"  ✓ パラメータセット保存: {param_file}")

    # ========================================
    # 5. ファイルからの読み込み
    # ========================================
    print("\n[5/5] ファイルから読み込み中...")

    # 読み込み
    abstract_loaded = load_abstract_scenario(abstract_file)
    logical_loaded = load_logical_scenario(logical_file)
    param_set_loaded = load_parameter_set(base_dir / f"params_{param_sets[0].uuid}.json")

    print(f"  ✓ 抽象シナリオ読み込み完了")
    print(f"    UUID: {abstract_loaded.uuid}")
    print(f"    名前: {abstract_loaded.name}")

    print(f"  ✓ 論理シナリオ読み込み完了")
    print(f"    UUID: {logical_loaded.uuid}")
    print(f"    親UUID: {logical_loaded.parent_abstract_uuid}")

    print(f"  ✓ パラメータセット読み込み完了")
    print(f"    UUID: {param_set_loaded.uuid}")
    print(f"    親UUID: {param_set_loaded.parent_logical_uuid}")

    # 検証
    assert abstract_loaded.uuid == abstract.uuid
    assert logical_loaded.parent_abstract_uuid == abstract.uuid
    assert param_set_loaded.parent_logical_uuid == logical.uuid

    print("\n" + "=" * 60)
    print("✓ すべての処理が正常に完了しました")
    print("=" * 60)

    print("\n📊 生成されたファイル:")
    print(f"  - {abstract_file}")
    print(f"  - {logical_file}")
    for param_set in param_sets:
        print(f"  - {base_dir / f'params_{param_set.uuid}.json'}")

    print("\n💡 次のステップ:")
    print("  1. 論理シナリオからPythonスクリプトを生成")
    print("  2. CARLAシミュレーターで実行")
    print("  3. .rrd/.mp4ファイルを生成")
    print("  4. ExecutionTraceを作成して保存")


if __name__ == "__main__":
    main()
