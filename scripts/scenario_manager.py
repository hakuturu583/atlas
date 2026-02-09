#!/usr/bin/env python3
"""
シナリオ管理ツール（再設計版）

階層構造:
  抽象シナリオ (Abstract) - どんな場所でどんな物体が登場するか
    ↓ 1:N
  論理シナリオ (Logical) - パラメータの定義と分布
    ↓ 1:N
  パラメータ (Parameters) - サンプリングされた具体値
    ↓ 1:1
  実行 (Execution) - 実行結果
"""
import json
import uuid
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class ScenarioManager:
    """シナリオ管理クラス"""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.scenarios_dir = self.base_dir / "data" / "scenarios"
        self.python_dir = self.base_dir / "scenarios"
        self.rerun_dir = self.base_dir / "data" / "rerun"
        self.videos_dir = self.base_dir / "data" / "videos"

        # ディレクトリを作成
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.python_dir.mkdir(parents=True, exist_ok=True)
        self.rerun_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)

    def create_abstract_scenario(
        self,
        name: str,
        description: str,
        original_prompt: str,
        environment: Dict[str, Any],
        actors: List[Dict[str, Any]],
        scenario_type: str
    ) -> str:
        """
        抽象シナリオを作成

        Args:
            name: シナリオ名
            description: 説明
            original_prompt: ユーザーの元の要件
            environment: 環境設定 (location_type, features)
            actors: アクターのリスト
            scenario_type: シナリオタイプ

        Returns:
            生成された抽象シナリオのUUID
        """
        abstract_uuid = str(uuid.uuid4())

        abstract_scenario = {
            "uuid": abstract_uuid,
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "environment": environment,
            "actors": actors,
            "scenario_type": scenario_type,
            "original_prompt": original_prompt
        }

        # JSONファイルに保存
        file_path = self.scenarios_dir / f"abstract_{abstract_uuid}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(abstract_scenario, f, indent=2, ensure_ascii=False)

        print(f"✓ 抽象シナリオを作成: {file_path}")
        print(f"  UUID: {abstract_uuid}")
        return abstract_uuid

    def create_logical_scenario(
        self,
        parent_abstract_uuid: str,
        name: str,
        description: str,
        parameter_space: Dict[str, Any]
    ) -> str:
        """
        論理シナリオを作成

        Args:
            parent_abstract_uuid: 親の抽象シナリオUUID
            name: シナリオ名
            description: 説明
            parameter_space: パラメータ空間の定義

        Returns:
            生成された論理シナリオのUUID
        """
        logical_uuid = str(uuid.uuid4())

        # 親の抽象シナリオが存在するか確認
        abstract_file = self.scenarios_dir / f"abstract_{parent_abstract_uuid}.json"
        if not abstract_file.exists():
            raise FileNotFoundError(f"親の抽象シナリオが見つかりません: {abstract_file}")

        logical_scenario = {
            "uuid": logical_uuid,
            "parent_abstract_uuid": parent_abstract_uuid,
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "parameter_space": parameter_space
        }

        # JSONファイルに保存
        file_path = self.scenarios_dir / f"logical_{logical_uuid}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(logical_scenario, f, indent=2, ensure_ascii=False)

        # パラメータファイルを初期化
        params_file = self.scenarios_dir / f"logical_{logical_uuid}_parameters.json"
        params_data = {
            "logical_uuid": logical_uuid,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "parameters": {}
        }
        with open(params_file, 'w', encoding='utf-8') as f:
            json.dump(params_data, f, indent=2, ensure_ascii=False)

        print(f"✓ 論理シナリオを作成: {file_path}")
        print(f"  UUID: {logical_uuid}")
        print(f"  親: {parent_abstract_uuid}")
        print(f"✓ パラメータファイルを初期化: {params_file}")
        return logical_uuid

    def sample_parameters(
        self,
        logical_uuid: str,
        carla_config: Dict[str, Any],
        seed: Optional[int] = None
    ) -> str:
        """
        論理シナリオからパラメータをサンプリング

        Args:
            logical_uuid: 論理シナリオUUID
            carla_config: CARLA設定
            seed: 乱数シード（再現性のため）

        Returns:
            生成されたパラメータのUUID
        """
        if seed is not None:
            random.seed(seed)

        # 論理シナリオを読み込み
        logical_file = self.scenarios_dir / f"logical_{logical_uuid}.json"
        if not logical_file.exists():
            raise FileNotFoundError(f"論理シナリオが見つかりません: {logical_file}")

        with open(logical_file, encoding='utf-8') as f:
            logical = json.load(f)

        parameter_space = logical['parameter_space']

        # サンプリング
        sampled_values = {}
        for actor_id, params in parameter_space.items():
            sampled_values[actor_id] = {}
            for param_name, param_def in params.items():
                value = self._sample_value(param_def)
                sampled_values[actor_id][param_name] = value

        # パラメータUUIDを生成
        parameter_uuid = str(uuid.uuid4())

        # 出力ファイルパスを生成
        rrd_file = str(self.rerun_dir / f"{logical_uuid}_{parameter_uuid}.rrd")
        mp4_file = str(self.videos_dir / f"{logical_uuid}_{parameter_uuid}.mp4")

        parameter_entry = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "sampled_values": sampled_values,
            "carla_config": carla_config,
            "output": {
                "rrd_file": rrd_file,
                "mp4_file": mp4_file
            }
        }

        # パラメータファイルに追加
        params_file = self.scenarios_dir / f"logical_{logical_uuid}_parameters.json"
        with open(params_file, encoding='utf-8') as f:
            params_data = json.load(f)

        params_data['parameters'][parameter_uuid] = parameter_entry

        with open(params_file, 'w', encoding='utf-8') as f:
            json.dump(params_data, f, indent=2, ensure_ascii=False)

        print(f"✓ パラメータをサンプリング: {params_file}")
        print(f"  パラメータUUID: {parameter_uuid}")
        print(f"  論理シナリオ: {logical_uuid}")
        return parameter_uuid

    def _sample_value(self, param_def: Dict[str, Any]) -> float:
        """パラメータ定義から値をサンプリング"""
        distribution = param_def.get('distribution', 'constant')

        if distribution == 'constant':
            return param_def['value']

        elif distribution == 'uniform':
            min_val = param_def['min']
            max_val = param_def['max']
            return random.uniform(min_val, max_val)

        elif distribution == 'normal':
            mean = param_def['mean']
            std = param_def['std']
            return random.gauss(mean, std)

        elif distribution == 'choice':
            choices = param_def['choices']
            return random.choice(choices)

        else:
            raise ValueError(f"未対応の分布: {distribution}")

    def get_parameters(self, logical_uuid: str, parameter_uuid: str) -> Dict[str, Any]:
        """
        特定のパラメータセットを取得

        Args:
            logical_uuid: 論理シナリオUUID
            parameter_uuid: パラメータUUID

        Returns:
            パラメータセット
        """
        params_file = self.scenarios_dir / f"logical_{logical_uuid}_parameters.json"
        if not params_file.exists():
            raise FileNotFoundError(f"パラメータファイルが見つかりません: {params_file}")

        with open(params_file, encoding='utf-8') as f:
            params_data = json.load(f)

        if parameter_uuid not in params_data['parameters']:
            raise KeyError(f"パラメータUUID {parameter_uuid} が見つかりません")

        return params_data['parameters'][parameter_uuid]

    def list_parameters(self, logical_uuid: str) -> Dict[str, Dict[str, Any]]:
        """
        論理シナリオの全パラメータを取得

        Args:
            logical_uuid: 論理シナリオUUID

        Returns:
            パラメータセットの辞書
        """
        params_file = self.scenarios_dir / f"logical_{logical_uuid}_parameters.json"
        if not params_file.exists():
            return {}

        with open(params_file, encoding='utf-8') as f:
            params_data = json.load(f)

        return params_data['parameters']

    def create_execution_trace(
        self,
        logical_uuid: str,
        parameter_uuid: str,
        python_file: str,
        command: str,
        exit_code: int,
        status: str = "success"
    ) -> str:
        """
        実行トレースを作成

        Args:
            logical_uuid: 論理シナリオUUID
            parameter_uuid: パラメータUUID
            python_file: Python実装ファイルパス
            command: 実行コマンド
            exit_code: 終了コード
            status: ステータス（success/failed）

        Returns:
            実行トレースファイルのパス
        """
        # 論理シナリオから抽象シナリオを取得
        logical_file = self.scenarios_dir / f"logical_{logical_uuid}.json"
        with open(logical_file, encoding='utf-8') as f:
            logical = json.load(f)

        abstract_uuid = logical['parent_abstract_uuid']
        name = logical['name']
        description = logical['description']

        # パラメータから出力ファイルパスを取得
        parameters = self.get_parameters(logical_uuid, parameter_uuid)

        execution_trace = {
            "execution_uuid": parameter_uuid,
            "logical_uuid": logical_uuid,
            "abstract_uuid": abstract_uuid,
            "parameter_uuid": parameter_uuid,
            "name": name,
            "description": description,
            "executed_at": datetime.utcnow().isoformat() + "Z",
            "trace": {
                "abstract_scenario_file": str(self.scenarios_dir / f"abstract_{abstract_uuid}.json"),
                "logical_scenario_file": str(logical_file),
                "parameter_file": str(self.scenarios_dir / f"logical_{logical_uuid}_parameters.json"),
                "parameter_uuid": parameter_uuid,
                "implementation": {
                    "python_file": python_file,
                    "command": command,
                    "exit_code": exit_code,
                    "final_status": status
                }
            },
            "outputs": parameters['output']
        }

        # JSONファイルに保存
        file_path = self.scenarios_dir / f"execution_{logical_uuid}_{parameter_uuid}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(execution_trace, f, indent=2, ensure_ascii=False)

        print(f"✓ 実行トレースを作成: {file_path}")
        return str(file_path)

    def list_abstract_scenarios(self) -> List[Dict[str, str]]:
        """抽象シナリオの一覧を取得"""
        scenarios = []
        for file_path in sorted(self.scenarios_dir.glob("abstract_*.json")):
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)
                scenarios.append({
                    "uuid": data['uuid'],
                    "name": data['name'],
                    "description": data['description'],
                    "scenario_type": data.get('scenario_type', 'unknown'),
                    "file": str(file_path)
                })
        return scenarios

    def list_logical_scenarios(self, parent_abstract_uuid: Optional[str] = None) -> List[Dict[str, str]]:
        """論理シナリオの一覧を取得"""
        scenarios = []
        for file_path in sorted(self.scenarios_dir.glob("logical_*.json")):
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)
                if parent_abstract_uuid and data['parent_abstract_uuid'] != parent_abstract_uuid:
                    continue

                # パラメータ数を取得
                params = self.list_parameters(data['uuid'])
                param_count = len(params)

                scenarios.append({
                    "uuid": data['uuid'],
                    "parent_abstract_uuid": data['parent_abstract_uuid'],
                    "name": data['name'],
                    "description": data['description'],
                    "parameter_count": param_count,
                    "file": str(file_path)
                })
        return scenarios


def main():
    """CLIインターフェース"""
    import sys

    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python scenario_manager.py list-abstract")
        print("  python scenario_manager.py list-logical [abstract_uuid]")
        print("  python scenario_manager.py list-params <logical_uuid>")
        sys.exit(1)

    manager = ScenarioManager()
    command = sys.argv[1]

    if command == "list-abstract":
        scenarios = manager.list_abstract_scenarios()
        print(f"=== 抽象シナリオ ({len(scenarios)}件) ===")
        for s in scenarios:
            print(f"  {s['uuid'][:8]}... {s['name']}")
            print(f"    タイプ: {s['scenario_type']}")
            print(f"    説明: {s['description']}")
            print()

    elif command == "list-logical":
        parent_uuid = sys.argv[2] if len(sys.argv) > 2 else None
        scenarios = manager.list_logical_scenarios(parent_uuid)
        print(f"=== 論理シナリオ ({len(scenarios)}件) ===")
        for s in scenarios:
            print(f"  {s['uuid'][:8]}... {s['name']}")
            print(f"    親: {s['parent_abstract_uuid'][:8]}...")
            print(f"    パラメータ数: {s['parameter_count']}")
            print()

    elif command == "list-params":
        if len(sys.argv) < 3:
            print("エラー: 論理シナリオUUIDを指定してください")
            sys.exit(1)

        logical_uuid = sys.argv[2]
        parameters = manager.list_parameters(logical_uuid)
        print(f"=== パラメータ ({len(parameters)}件) ===")
        print(f"論理シナリオ: {logical_uuid}")
        print()
        for param_uuid, param_data in parameters.items():
            print(f"  {param_uuid[:8]}...")
            print(f"    作成: {param_data['created_at']}")
            print(f"    動画: {param_data['output']['mp4_file']}")
            print()


if __name__ == "__main__":
    main()
