#!/usr/bin/env python3
"""
シナリオとログデータのクリーンアップツール

使用例:
  # ドライラン（削除せずリスト表示のみ）
  python cleanup_scenarios.py --dry-run

  # すべて削除
  python cleanup_scenarios.py --all

  # 特定の論理シナリオを削除
  python cleanup_scenarios.py --logical-uuid <uuid>

  # 特定の抽象シナリオとその子孫を削除
  python cleanup_scenarios.py --abstract-uuid <uuid>

  # 古いシナリオのみ削除（N日前より古い）
  python cleanup_scenarios.py --older-than-days 30
"""
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set


class ScenarioCleanup:
    """シナリオクリーンアップクラス"""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.scenarios_dir = self.base_dir / "data" / "scenarios"
        self.python_dir = self.base_dir / "scenarios"
        self.rerun_dir = self.base_dir / "data" / "rerun"
        self.videos_dir = self.base_dir / "data" / "videos"

    def find_all_files(self) -> Dict[str, List[Path]]:
        """すべてのシナリオ関連ファイルを検索"""
        files = {
            "abstract": list(self.scenarios_dir.glob("abstract_*.json")),
            "logical": list(self.scenarios_dir.glob("logical_*.json")),
            "parameters": list(self.scenarios_dir.glob("logical_*_parameters.json")),
            "execution": list(self.scenarios_dir.glob("execution_*.json")),
            "python": list(self.python_dir.glob("*.py")),
            "videos": list(self.videos_dir.glob("*.mp4")),
            "rerun": list(self.rerun_dir.glob("*.rrd"))
        }
        return files

    def find_files_by_abstract_uuid(self, abstract_uuid: str) -> Dict[str, List[Path]]:
        """抽象シナリオUUIDから関連するすべてのファイルを検索"""
        files = {
            "abstract": [],
            "logical": [],
            "parameters": [],
            "execution": [],
            "python": [],
            "videos": [],
            "rerun": []
        }

        # 抽象シナリオファイル
        abstract_file = self.scenarios_dir / f"abstract_{abstract_uuid}.json"
        if abstract_file.exists():
            files["abstract"].append(abstract_file)

        # 論理シナリオを検索
        logical_uuids = self._find_logical_by_abstract(abstract_uuid)

        for logical_uuid in logical_uuids:
            # 論理シナリオファイル
            logical_file = self.scenarios_dir / f"logical_{logical_uuid}.json"
            if logical_file.exists():
                files["logical"].append(logical_file)

            # パラメータファイル
            params_file = self.scenarios_dir / f"logical_{logical_uuid}_parameters.json"
            if params_file.exists():
                files["parameters"].append(params_file)

            # 実行トレース
            files["execution"].extend(
                self.scenarios_dir.glob(f"execution_{logical_uuid}_*.json")
            )

            # Pythonスクリプト
            python_file = self.python_dir / f"{logical_uuid}.py"
            if python_file.exists():
                files["python"].append(python_file)

            # 動画とRRDファイル
            files["videos"].extend(self.videos_dir.glob(f"{logical_uuid}_*.mp4"))
            files["rerun"].extend(self.rerun_dir.glob(f"{logical_uuid}_*.rrd"))

        return files

    def find_files_by_logical_uuid(self, logical_uuid: str) -> Dict[str, List[Path]]:
        """論理シナリオUUIDから関連するすべてのファイルを検索"""
        files = {
            "abstract": [],
            "logical": [],
            "parameters": [],
            "execution": [],
            "python": [],
            "videos": [],
            "rerun": []
        }

        # 論理シナリオファイル
        logical_file = self.scenarios_dir / f"logical_{logical_uuid}.json"
        if logical_file.exists():
            files["logical"].append(logical_file)

            # 親の抽象シナリオを取得
            with open(logical_file, encoding='utf-8') as f:
                logical = json.load(f)
                abstract_uuid = logical.get('parent_abstract_uuid')

            if abstract_uuid:
                # 他の論理シナリオが存在するか確認
                other_logicals = self._find_logical_by_abstract(abstract_uuid)
                if len(other_logicals) == 1 and logical_uuid in other_logicals:
                    # これが唯一の論理シナリオなら抽象も削除
                    abstract_file = self.scenarios_dir / f"abstract_{abstract_uuid}.json"
                    if abstract_file.exists():
                        files["abstract"].append(abstract_file)

        # パラメータファイル
        params_file = self.scenarios_dir / f"logical_{logical_uuid}_parameters.json"
        if params_file.exists():
            files["parameters"].append(params_file)

        # 実行トレース
        files["execution"].extend(
            self.scenarios_dir.glob(f"execution_{logical_uuid}_*.json")
        )

        # Pythonスクリプト
        python_file = self.python_dir / f"{logical_uuid}.py"
        if python_file.exists():
            files["python"].append(python_file)

        # 動画とRRDファイル
        files["videos"].extend(self.videos_dir.glob(f"{logical_uuid}_*.mp4"))
        files["rerun"].extend(self.rerun_dir.glob(f"{logical_uuid}_*.rrd"))

        return files

    def find_old_files(self, days: int) -> Dict[str, List[Path]]:
        """指定日数より古いファイルを検索"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        files = {
            "abstract": [],
            "logical": [],
            "parameters": [],
            "execution": [],
            "python": [],
            "videos": [],
            "rerun": []
        }

        # 抽象シナリオをチェック
        for abstract_file in self.scenarios_dir.glob("abstract_*.json"):
            with open(abstract_file, encoding='utf-8') as f:
                data = json.load(f)
                created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                if created_at < cutoff_date:
                    abstract_uuid = data['uuid']
                    old_files = self.find_files_by_abstract_uuid(abstract_uuid)
                    for key in files:
                        files[key].extend(old_files[key])

        return files

    def _find_logical_by_abstract(self, abstract_uuid: str) -> Set[str]:
        """抽象シナリオUUIDから論理シナリオUUIDのセットを取得"""
        logical_uuids = set()
        for logical_file in self.scenarios_dir.glob("logical_*.json"):
            with open(logical_file, encoding='utf-8') as f:
                data = json.load(f)
                if data.get('parent_abstract_uuid') == abstract_uuid:
                    logical_uuids.add(data['uuid'])
        return logical_uuids

    def delete_files(self, files: Dict[str, List[Path]], dry_run: bool = True) -> None:
        """ファイルを削除"""
        total_size = 0
        total_count = 0

        print("\n=== 削除対象ファイル ===\n")

        for category, file_list in files.items():
            if not file_list:
                continue

            print(f"【{category}】")
            category_size = 0
            for file_path in file_list:
                if file_path.exists():
                    size = file_path.stat().st_size
                    category_size += size
                    total_count += 1
                    print(f"  - {file_path} ({self._format_size(size)})")

            if category_size > 0:
                print(f"  小計: {self._format_size(category_size)}")
            print()

            total_size += category_size

        print(f"=== 合計: {total_count}ファイル, {self._format_size(total_size)} ===\n")

        if dry_run:
            print("ℹ️  ドライランモード: ファイルは削除されません")
            print("   実際に削除するには --force オプションを使用してください")
        else:
            # 削除実行
            for category, file_list in files.items():
                for file_path in file_list:
                    if file_path.exists():
                        file_path.unlink()
                        print(f"✓ 削除: {file_path}")

            print(f"\n✓ {total_count}ファイルを削除しました")

    def _format_size(self, size: int) -> str:
        """ファイルサイズをフォーマット"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"


def main():
    parser = argparse.ArgumentParser(
        description="シナリオとログデータのクリーンアップツール",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 削除対象の選択
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="すべてのシナリオとログを削除"
    )
    group.add_argument(
        "--abstract-uuid",
        type=str,
        help="指定した抽象シナリオとその子孫を削除"
    )
    group.add_argument(
        "--logical-uuid",
        type=str,
        help="指定した論理シナリオとその関連ファイルを削除"
    )
    group.add_argument(
        "--older-than-days",
        type=int,
        metavar="DAYS",
        help="指定日数より古いシナリオを削除"
    )

    # オプション
    parser.add_argument(
        "--force",
        action="store_true",
        help="実際に削除を実行（指定しない場合はドライラン）"
    )

    args = parser.parse_args()

    cleanup = ScenarioCleanup()

    # 削除対象ファイルを検索
    if args.all:
        print("すべてのシナリオとログを検索中...")
        files = cleanup.find_all_files()

    elif args.abstract_uuid:
        print(f"抽象シナリオ {args.abstract_uuid} の関連ファイルを検索中...")
        files = cleanup.find_files_by_abstract_uuid(args.abstract_uuid)

    elif args.logical_uuid:
        print(f"論理シナリオ {args.logical_uuid} の関連ファイルを検索中...")
        files = cleanup.find_files_by_logical_uuid(args.logical_uuid)

    elif args.older_than_days:
        print(f"{args.older_than_days}日より古いシナリオを検索中...")
        files = cleanup.find_old_files(args.older_than_days)

    # ファイルが見つからない場合
    total_files = sum(len(file_list) for file_list in files.values())
    if total_files == 0:
        print("削除対象のファイルが見つかりませんでした")
        return

    # 削除実行
    dry_run = not args.force
    cleanup.delete_files(files, dry_run=dry_run)


if __name__ == "__main__":
    main()
