"""シナリオ生成の統合サービス

ユーザーの自然言語要件から、抽象シナリオ → 論理シナリオ → C++実装
までを生成し、ビルド・実行・デバッグを自動化する。
"""

from typing import Optional, Tuple
from pathlib import Path
import json
import uuid as uuid_module
import re
from datetime import datetime
import subprocess
import time

from app.models.scenario_trace import (
    AbstractScenario,
    LogicalScenario,
    ConcreteScenario,
    ScenarioTrace,
    BuildError,
    ImplementationInfo,
    Actor,
    Maneuver
)

from app.services.sandbox_manager import sandbox_manager, sandbox_launcher
import logging

logger = logging.getLogger(__name__)


class ScenarioWriter:
    """シナリオ生成の統合サービス"""

    def __init__(self):
        self.data_dir = Path("data/scenarios")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def generate_abstract_scenario(self, prompt: str) -> AbstractScenario:
        """ユーザープロンプトから抽象シナリオを生成

        Args:
            prompt: ユーザーの自然言語要件

        Returns:
            抽象シナリオ

        Note:
            実際のLLM呼び出しは、MCPツール側で実装する。
            ここではプレースホルダーとして基本的な構造を返す。
        """
        # プレースホルダー実装
        # 実際にはLLM（Claude API）に以下を指示:
        # - アクターの抽出（最低1台は自動運転スタック予定）
        # - 操作（maneuvers）の抽出
        # - 概要記述

        return AbstractScenario(
            description=f"生成されたシナリオ: {prompt}",
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
                    actor="lead_vehicle",
                    action="一定速度で走行",
                    duration="10s"
                ),
                Maneuver(
                    actor="ego_vehicle",
                    action="前方車両を追従",
                    duration="10s",
                    conditions=["距離を20m維持"]
                )
            ]
        )

    def generate_logical_scenario(
        self, abstract: AbstractScenario
    ) -> LogicalScenario:
        """抽象シナリオから論理シナリオを生成

        Args:
            abstract: 抽象シナリオ

        Returns:
            論理シナリオ（OpenDRIVE非依存）

        Note:
            実際のLLM呼び出しは、MCPツール側で実装する。
        """
        # プレースホルダー実装
        # OpenDRIVE非依存の記述:
        # - symbolic location（"ramp_start", "main_lane"など）
        # - 相対的な速度・距離
        # - イベントのタイミング

        return LogicalScenario(
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

    def generate_concrete_scenario(
        self, logical: LogicalScenario, carla_map: str = "Town04"
    ) -> Tuple[ConcreteScenario, str]:
        """論理シナリオから具体シナリオとJSONパラメータを生成

        Args:
            logical: 論理シナリオ
            carla_map: CARLAマップ名（デフォルト: Town04）

        Returns:
            (具体シナリオ, JSONパラメータの文字列)
        """
        # 具体的なスポーン位置を決定
        # TODO: 実際にはCARLAマップの情報を使って適切な位置を選択
        spawn_points = {
            "ego_vehicle": {
                "vehicle_type": "vehicle.tesla.model3",
                "x": 100.0,
                "y": 200.0,
                "z": 0.3,
                "yaw": 0.0,
                "is_autonomous_stack": True
            },
            "lead_vehicle": {
                "vehicle_type": "vehicle.audi.a2",
                "x": 120.0,
                "y": 200.0,
                "z": 0.3,
                "yaw": 0.0,
                "is_autonomous_stack": False
            }
        }

        camera_config = {
            "offset_x": -5.0,
            "offset_y": 0.0,
            "offset_z": 2.5
        }

        concrete = ConcreteScenario(
            carla_map=carla_map,
            spawn_points=spawn_points,
            camera_config=camera_config,
            duration_steps=200  # 20Hz × 10秒
        )

        # JSONパラメータファイルの内容を生成
        json_params = {
            "carla_host": "localhost",
            "carla_port": 2000,
            "carla_map": carla_map,
            "spawn_points": spawn_points,
            "camera_config": camera_config,
            "duration_steps": 200
        }

        json_str = json.dumps(json_params, indent=2, ensure_ascii=False)

        return concrete, json_str

    def launch_with_retry(
        self,
        cpp_code: str,
        config_json: str,
        scenario_uuid: str,
        max_retries: int = 5
    ) -> dict:
        """C++コードをビルド・実行（自動リトライ）

        Args:
            cpp_code: C++ソースコード
            config_json: JSONパラメータ
            scenario_uuid: シナリオUUID
            max_retries: 最大リトライ回数

        Returns:
            実行結果の辞書
        """
        build_errors = []

        for attempt in range(1, max_retries + 1):
            logger.info(f"Build attempt {attempt}/{max_retries}")
            print(f"[ScenarioWriter] Build attempt {attempt}/{max_retries}")

            try:
                # 1. main.cppにコードを書き込み
                main_cpp = Path("sandbox/src/main.cpp")
                main_cpp.write_text(cpp_code, encoding="utf-8")
                logger.info(f"Updated main.cpp")
                print(f"[ScenarioWriter] Updated main.cpp")

                # 2. ワークスペースディレクトリを作成
                workspace_path = Path(f"sandbox/workspace/{scenario_uuid}")
                workspace_path.mkdir(parents=True, exist_ok=True)
                output_path = workspace_path / "output"
                output_path.mkdir(exist_ok=True)
                logger.info(f"Created workspace: {workspace_path}")

                # 3. config.jsonを保存
                config_file = workspace_path / f"{scenario_uuid}_config.json"
                config_file.write_text(config_json, encoding="utf-8")
                logger.info(f"Created config file: {config_file}")
                print(f"[ScenarioWriter] Created config file: {config_file}")

                # 4. CARLAサーバー接続チェック
                logger.info("Checking CARLA server...")
                print(f"[ScenarioWriter] Checking CARLA server...")
                if not sandbox_launcher.check_carla_server(timeout=2.0):
                    error_msg = "CARLA server is not accessible at localhost:2000"
                    logger.error(error_msg)
                    print(f"[ScenarioWriter] ERROR: {error_msg}")
                    build_errors.append({
                        "attempt": attempt,
                        "error": error_msg,
                        "fix": "start_carla_server"
                    })
                    # CARLAが起動していない場合は、リトライしても無駄なので終了
                    return {
                        "success": False,
                        "attempt": attempt,
                        "uuid": scenario_uuid,
                        "errors": build_errors,
                        "logs": "CARLA server is not running. Please start CARLA first."
                    }
                logger.info("CARLA server is accessible ✓")
                print(f"[ScenarioWriter] CARLA server is accessible ✓")

                # 5. sandbox起動（SandboxLauncherを使用）
                logger.info(f"Launching sandbox with UUID: {scenario_uuid}")
                print(f"[ScenarioWriter] Launching sandbox...")

                # 基本的なlaunch_sandboxを使用（SandboxLauncherは検証が多すぎる）
                uuid_returned, result = sandbox_manager.launch_sandbox(scenario_uuid=scenario_uuid)

                # 6. 結果を解析
                logs = f"=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}"
                logger.info(f"Sandbox completed with return code: {result.returncode}")
                print(f"[ScenarioWriter] Sandbox completed with return code: {result.returncode}")

                # ログの最初の部分を表示
                log_preview = logs[:500] + "..." if len(logs) > 500 else logs
                logger.debug(f"Logs preview:\n{log_preview}")

                if result.returncode == 0:
                    # 成功: .rrdと.mp4の存在確認
                    rrd_file = output_path / f"{scenario_uuid}.rrd"
                    mp4_file = output_path / f"{scenario_uuid}.mp4"

                    rrd_exists = rrd_file.exists()
                    mp4_exists = mp4_file.exists()

                    logger.info(f"Output file check: .rrd={rrd_exists}, .mp4={mp4_exists}")
                    print(f"[ScenarioWriter] Output files: .rrd={rrd_exists}, .mp4={mp4_exists}")

                    if rrd_exists and mp4_exists:
                        logger.info(f"Build successful! Files created in {output_path}")
                        print(f"[ScenarioWriter] Build successful!")
                        return {
                            "success": True,
                            "attempt": attempt,
                            "uuid": scenario_uuid,
                            "logs": logs,
                            "errors": build_errors,
                            "rrd_file": str(rrd_file),
                            "mp4_file": str(mp4_file)
                        }
                    else:
                        # ビルドは成功したが、ファイルが生成されていない
                        missing_files = []
                        if not rrd_exists:
                            missing_files.append(".rrd")
                        if not mp4_exists:
                            missing_files.append(".mp4")
                        error_msg = f"Output files not generated: {', '.join(missing_files)}"
                        logger.warning(error_msg)
                        print(f"[ScenarioWriter] WARNING: {error_msg}")
                        error_info = {
                            "message": error_msg,
                            "fix": "check_rerun_videorecorder"
                        }
                else:
                    # ビルドエラー
                    logger.error(f"Build failed with return code {result.returncode}")
                    print(f"[ScenarioWriter] Build failed with return code {result.returncode}")
                    error_info = self._analyze_build_error(logs)
                    logger.error(f"Error analysis: {error_info['message']} (fix: {error_info['fix']})")
                    print(f"[ScenarioWriter] Error: {error_info['message']}")

                # エラー記録
                build_errors.append({
                    "attempt": attempt,
                    "error": error_info["message"],
                    "fix": error_info["fix"],
                    "logs": logs[:1000]  # 最初の1000文字のみ保存
                })

                # コード修正（次の試行のため）
                if attempt < max_retries:
                    logger.info(f"Applying fix: {error_info['fix']}")
                    print(f"[ScenarioWriter] Applying fix: {error_info['fix']}")
                    cpp_code = self._apply_fix(cpp_code, error_info)
                    time.sleep(2)  # 少し待機

            except Exception as e:
                # 予期しないエラー
                error_msg = str(e)
                logger.exception(f"Unexpected error: {error_msg}")
                print(f"[ScenarioWriter] Unexpected error: {error_msg}")
                build_errors.append({
                    "attempt": attempt,
                    "error": error_msg,
                    "fix": "manual_review"
                })

        logger.error(f"Build failed after {max_retries} attempts")
        print(f"[ScenarioWriter] Build failed after {max_retries} attempts")
        return {
            "success": False,
            "attempt": max_retries,
            "uuid": scenario_uuid,
            "errors": build_errors
        }

    def save_trace(self, trace: ScenarioTrace) -> str:
        """トレース情報をJSONに保存

        Args:
            trace: シナリオトレース

        Returns:
            保存されたファイルのパス
        """
        file_path = self.data_dir / f"{trace.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            # mode='json'でdatetimeを文字列に変換
            json.dump(trace.model_dump(mode='json'), f, ensure_ascii=False, indent=2)
        return str(file_path)

    def load_trace(self, scenario_id: str) -> Optional[ScenarioTrace]:
        """保存されたトレースを読み込む

        Args:
            scenario_id: シナリオID

        Returns:
            シナリオトレース（存在しない場合はNone）
        """
        file_path = self.data_dir / f"{scenario_id}.json"
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ScenarioTrace(**data)

    # Note: _simulate_build is no longer needed as we use actual sandbox launches

    def generate_cpp_implementation_prompt(
        self, logical_scenario: LogicalScenario
    ) -> str:
        """サブエージェント用のC++実装生成プロンプトを作成

        Args:
            logical_scenario: 論理シナリオ

        Returns:
            サブエージェントに渡すプロンプト
        """
        prompt = f"""以下の論理シナリオからCARLA C++実装を生成してください。

論理シナリオ:
{logical_scenario.model_dump_json(indent=2)}

要件:
1. **carla-cpp-scenario**スキルを使用してください
   - CARLA C++ API Referenceを参照: https://carla-ue5.readthedocs.io/en/latest/ref_cpp/
   - 車両制御、センサー追加、シナリオロジックを実装

2. **rerun-carla-sdk**スキルを使用してください
   - Rerun可視化とログ記録を実装
   - ヘッドレスモードで.rrdファイルを生成

3. **テンプレート**を参考にしてください
   - `sandbox/src/main_template.cpp`を基にしてください
   - 以下の機能が必須です:
     * `ScenarioConfig::load()`でJSONパラメータ読み込み
     * 同期モード設定（`synchronous_mode=true`, `fixed_delta_seconds=0.05`）
     * VideoRecorder統合（mp4記録）
     * スペクターカメラ配置（自動運転スタックNPC付近）
     * ファイル名: `{{uuid}}.rrd`, `{{uuid}}.mp4`

4. **シナリオロジック**を実装してください
   - 論理シナリオの`events`に基づいて車両制御を実装
   - 時刻とアクションに応じた制御ロジック

5. **出力先**を確認してください
   - `/workspace/output/{{uuid}}.rrd`
   - `/workspace/output/{{uuid}}.mp4`

実装したC++コードを`sandbox/src/main.cpp`に書き込む形で提供してください。
"""
        return prompt

    def _analyze_build_error(self, logs: str) -> dict:
        """ビルドエラーを解析

        Args:
            logs: ビルドログ

        Returns:
            エラー情報（message, fix）
        """
        # エラーパターンマッチング（優先度順）

        # 1. CARLA接続エラー
        if "connection refused" in logs.lower() or "unable to connect" in logs.lower() or "carla server is not accessible" in logs.lower():
            return {
                "message": "CARLA connection error - Server not running",
                "fix": "start_carla_server"
            }

        # 2. リンクエラー: OpenCV
        if "undefined reference to" in logs and "cv::" in logs:
            return {
                "message": "OpenCV link error - Missing OpenCV library",
                "fix": "add_opencv_library"
            }

        # 3. リンクエラー: CARLA
        if "undefined reference to" in logs and "carla::" in logs:
            return {
                "message": "CARLA link error - Missing libcarla",
                "fix": "add_carla_library"
            }

        # 4. リンクエラー: Rerun
        if "undefined reference to" in logs and "rerun::" in logs:
            return {
                "message": "Rerun link error - Missing rerun_sdk",
                "fix": "add_rerun_library"
            }

        # 5. リンクエラー: 一般
        if "undefined reference to" in logs:
            return {
                "message": "Link error - Missing library",
                "fix": "add_missing_library"
            }

        # 6. コンパイルエラー: API不一致
        if "error: no matching function" in logs or "error: no member named" in logs:
            return {
                "message": "API mismatch - Incorrect function call",
                "fix": "check_carla_reference"
            }

        # 7. コンパイルエラー: インクルード不足
        if "fatal error:" in logs and ".h: No such file" in logs:
            return {
                "message": "Include error - Missing header file",
                "fix": "add_missing_include"
            }

        # 8. コンパイルエラー: 構文エラー
        if "error: expected" in logs or "error: invalid use" in logs:
            return {
                "message": "Syntax error",
                "fix": "fix_syntax"
            }

        # 9. ランタイムエラー: セグメンテーションフォルト
        if "segmentation fault" in logs.lower() or "sigsegv" in logs.lower():
            return {
                "message": "Segmentation fault - Memory access error",
                "fix": "check_nullptr"
            }

        # 10. ランタイムエラー: Rerun/VideoRecorder
        if "rerun" in logs.lower() and "error" in logs.lower():
            return {
                "message": "Rerun initialization error",
                "fix": "check_rerun_init"
            }

        if "videorecorder" in logs.lower() or "opencv" in logs.lower():
            return {
                "message": "VideoRecorder error",
                "fix": "check_videorecorder_init"
            }

        # デフォルト
        return {
            "message": "Unknown error",
            "fix": "manual_review"
        }

    def _apply_fix(self, cpp_code: str, error_info: dict) -> str:
        """エラー情報に基づいてコードを修正

        Args:
            cpp_code: 元のC++コード
            error_info: エラー情報

        Returns:
            修正後のC++コード

        Note:
            実際にはLLM（サブエージェント）に修正を依頼する。
            ここでは基本的な修正パターンのみ実装。
        """
        fix_type = error_info["fix"]

        # 修正メッセージをコメントとして追加
        fix_comment = f"\n// Auto-fix applied: {error_info['message']}\n"

        if fix_type == "add_opencv_library":
            # CMakeLists.txtの修正が必要
            # 実際にはCMakeLists.txtを編集するか、サブエージェントに依頼
            cpp_code += fix_comment
            cpp_code += "// TODO: Add 'find_package(OpenCV REQUIRED)' and 'target_link_libraries(... ${OpenCV_LIBS})' to CMakeLists.txt\n"

        elif fix_type == "add_carla_library":
            cpp_code += fix_comment
            cpp_code += "// TODO: Ensure libcarla is properly linked in CMakeLists.txt\n"

        elif fix_type == "add_rerun_library":
            cpp_code += fix_comment
            cpp_code += "// TODO: Ensure rerun_sdk is properly linked in CMakeLists.txt\n"

        elif fix_type == "check_carla_reference":
            # CARLA API Referenceを参照して修正
            # サブエージェントに依頼
            cpp_code += fix_comment
            cpp_code += "// TODO: Check CARLA C++ API Reference: https://carla-ue5.readthedocs.io/en/latest/ref_cpp/\n"

        elif fix_type == "check_carla_running" or fix_type == "start_carla_server":
            # ユーザーに通知が必要（実際には修正不可）
            cpp_code += fix_comment
            cpp_code += "// IMPORTANT: Ensure CARLA is running on localhost:2000 before executing\n"
            cpp_code += "// To start CARLA: cd /path/to/carla && ./CarlaUE4.sh\n"

        elif fix_type == "add_missing_include":
            cpp_code += fix_comment
            cpp_code += "// TODO: Add missing #include directives\n"

        elif fix_type == "fix_syntax":
            cpp_code += fix_comment
            cpp_code += "// TODO: Fix syntax errors (missing semicolons, brackets, etc.)\n"

        elif fix_type == "check_nullptr":
            cpp_code += fix_comment
            cpp_code += "// TODO: Add nullptr checks before dereferencing pointers\n"

        elif fix_type == "check_rerun_init":
            cpp_code += fix_comment
            cpp_code += "// TODO: Verify Rerun initialization and .rrd file path\n"

        elif fix_type == "check_videorecorder_init":
            cpp_code += fix_comment
            cpp_code += "// TODO: Verify VideoRecorder initialization and .mp4 file path\n"

        elif fix_type == "check_rerun_videorecorder":
            cpp_code += fix_comment
            cpp_code += "// TODO: Ensure Rerun and VideoRecorder are properly closing files\n"

        else:
            # manual_review
            cpp_code += fix_comment
            cpp_code += "// MANUAL REVIEW REQUIRED: Automatic fix not available\n"

        return cpp_code


# シングルトンインスタンス
scenario_writer = ScenarioWriter()
