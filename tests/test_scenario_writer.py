"""シナリオライターの統合テスト

このテストは、シナリオライターエージェントの完全なワークフローを検証します。
"""

import pytest
import json
from pathlib import Path
from app.services.scenario_writer import scenario_writer
from app.models.scenario_trace import (
    AbstractScenario,
    LogicalScenario,
    ScenarioTrace,
    Actor,
    Maneuver
)


class TestScenarioWriter:
    """シナリオライターのテストスイート"""

    def test_generate_abstract_scenario(self):
        """抽象シナリオ生成のテスト"""
        prompt = "高速道路で前方車両を追従するシナリオ"

        abstract = scenario_writer.generate_abstract_scenario(prompt)

        assert isinstance(abstract, AbstractScenario)
        assert abstract.description
        assert len(abstract.actors) >= 2
        assert len(abstract.maneuvers) >= 1

        # 自動運転スタック予定のNPCが含まれているか確認
        has_autonomous_stack = any(
            actor.is_autonomous_stack for actor in abstract.actors
        )
        assert has_autonomous_stack, "At least one actor should be marked as autonomous stack"

    def test_generate_logical_scenario(self):
        """論理シナリオ生成のテスト"""
        abstract = AbstractScenario(
            description="テストシナリオ",
            actors=[
                Actor(
                    id="ego_vehicle",
                    role="自動運転スタック予定",
                    type="vehicle",
                    is_autonomous_stack=True
                ),
                Actor(
                    id="lead_vehicle",
                    role="前方車両",
                    type="vehicle",
                    is_autonomous_stack=False
                )
            ],
            maneuvers=[
                Maneuver(
                    actor="ego_vehicle",
                    action="追従",
                    duration="10s"
                )
            ]
        )

        logical = scenario_writer.generate_logical_scenario(abstract)

        assert isinstance(logical, LogicalScenario)
        assert "road_type" in logical.map_requirements
        assert logical.initial_conditions
        assert len(logical.events) > 0

    def test_generate_concrete_scenario(self):
        """具体シナリオ生成のテスト"""
        logical = LogicalScenario(
            map_requirements={"road_type": "highway", "lanes": 3},
            initial_conditions={"ego_vehicle": {"location": "lane_2", "speed": 50.0}},
            events=[{"time": 0.0, "type": "start"}]
        )

        concrete, json_str = scenario_writer.generate_concrete_scenario(
            logical, carla_map="Town04"
        )

        assert concrete.carla_map == "Town04"
        assert concrete.spawn_points
        assert concrete.camera_config

        # JSONパラメータの検証
        json_data = json.loads(json_str)
        assert json_data["carla_map"] == "Town04"
        assert "spawn_points" in json_data
        assert "camera_config" in json_data

    def test_save_and_load_trace(self):
        """トレース保存・読み込みのテスト"""
        # テストトレースを作成
        trace = ScenarioTrace(
            id="test_scenario_001",
            name="テストシナリオ",
            description="統合テスト用シナリオ",
            trace={
                "original_prompt": "テスト用プロンプト",
                "generated_at": "2026-02-06T00:00:00Z"
            }
        )

        # 保存
        file_path = scenario_writer.save_trace(trace)
        assert Path(file_path).exists()

        # 読み込み
        loaded_trace = scenario_writer.load_trace("test_scenario_001")
        assert loaded_trace is not None
        assert loaded_trace.id == trace.id
        assert loaded_trace.name == trace.name

        # クリーンアップ
        Path(file_path).unlink()

    def test_analyze_build_error_patterns(self):
        """ビルドエラー解析のテスト"""
        test_cases = [
            {
                "logs": "undefined reference to `cv::VideoWriter::write'",
                "expected_fix": "add_opencv_library"
            },
            {
                "logs": "undefined reference to `carla::client::Client::GetWorld'",
                "expected_fix": "add_carla_library"
            },
            {
                "logs": "error: no matching function for call to 'spawn'",
                "expected_fix": "check_carla_reference"
            },
            {
                "logs": "connection refused to localhost:2000",
                "expected_fix": "check_carla_running"
            },
            {
                "logs": "fatal error: rerun.hpp: No such file",
                "expected_fix": "add_missing_include"
            }
        ]

        for case in test_cases:
            error_info = scenario_writer._analyze_build_error(case["logs"])
            assert error_info["fix"] == case["expected_fix"], \
                f"Expected {case['expected_fix']}, got {error_info['fix']} for logs: {case['logs']}"

    def test_apply_fix_adds_comments(self):
        """自動修正がコメントを追加するかテスト"""
        cpp_code = "#include <iostream>\nint main() { return 0; }"

        error_info = {
            "message": "OpenCV link error",
            "fix": "add_opencv_library"
        }

        fixed_code = scenario_writer._apply_fix(cpp_code, error_info)

        assert "Auto-fix applied" in fixed_code
        assert "OpenCV" in fixed_code

    def test_cpp_implementation_prompt_generation(self):
        """C++実装プロンプト生成のテスト"""
        logical = LogicalScenario(
            map_requirements={"road_type": "highway"},
            initial_conditions={"ego_vehicle": {"location": "lane_1"}},
            events=[{"time": 0.0, "type": "start"}]
        )

        prompt = scenario_writer.generate_cpp_implementation_prompt(logical)

        assert "論理シナリオ" in prompt
        assert "carla-cpp-scenario" in prompt
        assert "rerun-carla-sdk" in prompt
        assert "main_template.cpp" in prompt
        assert "ScenarioConfig::load()" in prompt


@pytest.fixture(autouse=True)
def setup_test_environment():
    """テスト環境のセットアップ"""
    # data/scenariosディレクトリが存在することを確認
    scenarios_dir = Path("data/scenarios")
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    yield

    # テスト後のクリーンアップは個別のテストで行う


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
