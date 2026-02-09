#!/usr/bin/env python3
"""
シナリオのトレーサビリティ分析ツール

抽象シナリオ→論理シナリオ→Python実装の階層関係を分析します。
"""
import json
import glob
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AbstractScenario:
    """抽象シナリオ"""
    uuid: str
    name: str
    description: str
    original_prompt: str
    file_path: str


@dataclass
class LogicalScenario:
    """論理シナリオ"""
    uuid: str
    parent_abstract_uuid: str
    name: str
    description: str
    file_path: str


@dataclass
class ScenarioImplementation:
    """シナリオ実装"""
    logical_uuid: str
    abstract_uuid: str
    python_file: str
    rerun_file: Optional[str] = None
    video_file: Optional[str] = None


class ScenarioAnalyzer:
    """シナリオ分析クラス"""

    def __init__(self, scenarios_dir: str = "data/scenarios"):
        self.scenarios_dir = Path(scenarios_dir)
        self.abstract_scenarios: Dict[str, AbstractScenario] = {}
        self.logical_scenarios: Dict[str, LogicalScenario] = {}
        self.implementations: Dict[str, ScenarioImplementation] = {}

    def load_all(self):
        """全てのシナリオファイルを読み込み"""
        # 抽象シナリオ
        for file_path in self.scenarios_dir.glob("abstract_*.json"):
            with open(file_path) as f:
                data = json.load(f)
                self.abstract_scenarios[data['uuid']] = AbstractScenario(
                    uuid=data['uuid'],
                    name=data['name'],
                    description=data['description'],
                    original_prompt=data['original_prompt'],
                    file_path=str(file_path)
                )

        # 論理シナリオ
        for file_path in self.scenarios_dir.glob("logical_*.json"):
            with open(file_path) as f:
                data = json.load(f)
                self.logical_scenarios[data['uuid']] = LogicalScenario(
                    uuid=data['uuid'],
                    parent_abstract_uuid=data['parent_abstract_uuid'],
                    name=data['name'],
                    description=data['description'],
                    file_path=str(file_path)
                )

        # トレースファイル（実装情報）
        for file_path in self.scenarios_dir.glob("trace_*.json"):
            with open(file_path) as f:
                data = json.load(f)
                self.implementations[data['logical_uuid']] = ScenarioImplementation(
                    logical_uuid=data['logical_uuid'],
                    abstract_uuid=data['abstract_uuid'],
                    python_file=data['files']['python'],
                    rerun_file=data['files'].get('rerun'),
                    video_file=data['files'].get('video')
                )

    def get_children_logical_scenarios(self, abstract_uuid: str) -> List[LogicalScenario]:
        """指定した抽象シナリオから派生した論理シナリオを全て取得"""
        return [
            logical for logical in self.logical_scenarios.values()
            if logical.parent_abstract_uuid == abstract_uuid
        ]

    def get_parent_abstract_scenario(self, logical_uuid: str) -> Optional[AbstractScenario]:
        """論理シナリオの親となる抽象シナリオを取得"""
        logical = self.logical_scenarios.get(logical_uuid)
        if logical:
            return self.abstract_scenarios.get(logical.parent_abstract_uuid)
        return None

    def get_implementation(self, logical_uuid: str) -> Optional[ScenarioImplementation]:
        """論理シナリオの実装を取得"""
        return self.implementations.get(logical_uuid)

    def print_hierarchy(self):
        """階層構造を表示"""
        print("=== シナリオ階層構造 ===\n")

        for abstract_uuid, abstract in self.abstract_scenarios.items():
            print(f"📋 抽象シナリオ: {abstract.name}")
            print(f"   UUID: {abstract_uuid}")
            print(f"   説明: {abstract.description}")
            print(f"   元の要件: {abstract.original_prompt}")
            print()

            # 派生した論理シナリオ
            children = self.get_children_logical_scenarios(abstract_uuid)
            if children:
                for logical in children:
                    print(f"  └─ 📐 論理シナリオ: {logical.name}")
                    print(f"      UUID: {logical.uuid}")
                    print(f"      説明: {logical.description}")

                    # 実装
                    impl = self.get_implementation(logical.uuid)
                    if impl:
                        print(f"      └─ 🐍 Python実装: {impl.python_file}")
                        if impl.rerun_file:
                            print(f"          📊 Rerunログ: {impl.rerun_file}")
                        if impl.video_file:
                            print(f"          🎥 動画: {impl.video_file}")
                    print()
            else:
                print("  └─ (論理シナリオなし)")
                print()

    def print_summary(self):
        """サマリーを表示"""
        print("=== サマリー ===")
        print(f"抽象シナリオ: {len(self.abstract_scenarios)}件")
        print(f"論理シナリオ: {len(self.logical_scenarios)}件")
        print(f"実装済み: {len(self.implementations)}件")
        print()

    def trace_lineage(self, logical_uuid: str):
        """特定の論理シナリオの系譜を追跡"""
        print(f"=== 系譜追跡: {logical_uuid} ===\n")

        # 論理シナリオ
        logical = self.logical_scenarios.get(logical_uuid)
        if not logical:
            print(f"論理シナリオ {logical_uuid} が見つかりません")
            return

        # 親の抽象シナリオ
        abstract = self.get_parent_abstract_scenario(logical_uuid)
        if abstract:
            print(f"1️⃣  抽象シナリオ")
            print(f"   UUID: {abstract.uuid}")
            print(f"   名前: {abstract.name}")
            print(f"   元の要件: {abstract.original_prompt}")
            print(f"   ファイル: {abstract.file_path}")
            print()

        print(f"2️⃣  論理シナリオ")
        print(f"   UUID: {logical.uuid}")
        print(f"   名前: {logical.name}")
        print(f"   親: {logical.parent_abstract_uuid}")
        print(f"   ファイル: {logical.file_path}")
        print()

        # 実装
        impl = self.get_implementation(logical_uuid)
        if impl:
            print(f"3️⃣  実装")
            print(f"   Python: {impl.python_file}")
            if impl.rerun_file:
                print(f"   Rerun: {impl.rerun_file}")
            if impl.video_file:
                print(f"   動画: {impl.video_file}")
        else:
            print(f"3️⃣  実装: (未実装)")


def main():
    """メイン関数"""
    import sys

    analyzer = ScenarioAnalyzer()
    analyzer.load_all()

    if len(sys.argv) > 1:
        # 特定のUUIDを追跡
        uuid = sys.argv[1]
        analyzer.trace_lineage(uuid)
    else:
        # 全体のサマリーと階層を表示
        analyzer.print_summary()
        analyzer.print_hierarchy()


if __name__ == "__main__":
    main()
