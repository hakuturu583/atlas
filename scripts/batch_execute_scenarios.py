#!/usr/bin/env python3
"""
バッチシナリオ実行スクリプト

複数の論理シナリオUUIDを受け取り、順次C++実装生成→ビルド→実行を行います。
scenario-breakdownスキルで生成されたシナリオ群を効率的に実行するために使用します。
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_logical_scenario(logical_uuid: str) -> Optional[dict]:
    """論理シナリオJSONを読み込む"""
    logical_file = Path(f"data/scenarios/logical_{logical_uuid}.json")

    if not logical_file.exists():
        print(f"❌ エラー: 論理シナリオが見つかりません: {logical_uuid}")
        return None

    with open(logical_file) as f:
        return json.load(f)


def execute_scenario(logical_uuid: str, dry_run: bool = False) -> bool:
    """
    論理シナリオのPython実装を実行

    Args:
        logical_uuid: 論理シナリオUUID
        dry_run: True の場合、実行せずにログのみ表示

    Returns:
        成功した場合 True
    """
    print(f"\n{'='*60}")
    print(f"🚀 シナリオ実行: {logical_uuid}")
    print(f"{'='*60}\n")

    # 論理シナリオを読み込み
    logical_data = load_logical_scenario(logical_uuid)
    if not logical_data:
        return False

    print(f"✓ 論理シナリオ読み込み: {logical_data.get('name', 'Unknown')}")

    # Pythonスクリプトの存在確認
    python_file = Path(f"scenarios/{logical_uuid}.py")
    if not python_file.exists():
        print(f"❌ エラー: Pythonスクリプトが見つかりません: {python_file}")
        print(f"   scenario-writerスキルでPython実装を生成してください")
        return False

    print(f"✓ Pythonスクリプト検出: {python_file}")

    if dry_run:
        print("  [DRY RUN] 実際の実行はスキップします")
        return True

    # Python実装を実行
    import subprocess

    try:
        print("\n実行中...")
        result = subprocess.run(
            ["uv", "run", "python", str(python_file)],
            capture_output=True,
            text=True,
            timeout=300  # 5分タイムアウト
        )

        if result.returncode == 0:
            print("✓ 実行成功")
            print(result.stdout)
            return True
        else:
            print(f"❌ 実行失敗 (exit code: {result.returncode})")
            print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("❌ タイムアウト（5分経過）")
        return False
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        return False


def filter_by_criticality(
    logical_uuids: List[str],
    min_criticality: int
) -> List[str]:
    """
    Criticalityレベルでフィルタリング

    Args:
        logical_uuids: 論理シナリオUUIDリスト
        min_criticality: 最小Criticalityレベル (1-5)

    Returns:
        フィルタリング後のUUIDリスト
    """
    filtered = []

    for logical_uuid in logical_uuids:
        logical_data = load_logical_scenario(logical_uuid)
        if not logical_data:
            continue

        # 抽象シナリオからCriticalityを取得
        abstract_uuid = logical_data.get('parent_abstract_uuid')
        if not abstract_uuid:
            continue

        abstract_file = Path(f"data/scenarios/abstract_{abstract_uuid}.json")
        if not abstract_file.exists():
            continue

        with open(abstract_file) as f:
            abstract_data = json.load(f)

        criticality = abstract_data.get('pegasus_criticality_level', 1)

        if criticality >= min_criticality:
            filtered.append(logical_uuid)
            print(f"✓ {logical_uuid} (Criticality: {criticality})")
        else:
            print(f"  スキップ: {logical_uuid} (Criticality: {criticality} < {min_criticality})")

    return filtered


def main():
    parser = argparse.ArgumentParser(
        description="複数の論理シナリオをバッチ実行"
    )
    parser.add_argument(
        '--logical-uuids',
        required=True,
        help='論理シナリオUUIDのカンマ区切りリスト'
    )
    parser.add_argument(
        '--min-criticality',
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5],
        help='最小Criticalityレベル（1-5）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='ドライラン（実際の実行はスキップ）'
    )
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='エラーが発生しても続行'
    )

    args = parser.parse_args()

    # UUIDリストをパース
    logical_uuids = [uuid.strip() for uuid in args.logical_uuids.split(',')]

    print(f"\n{'='*60}")
    print(f"📋 バッチシナリオ実行")
    print(f"{'='*60}\n")
    print(f"シナリオ数: {len(logical_uuids)}")
    print(f"最小Criticality: {args.min_criticality}")
    print(f"ドライラン: {'はい' if args.dry_run else 'いいえ'}")
    print(f"エラー時続行: {'はい' if args.continue_on_error else 'いいえ'}")

    # Criticalityでフィルタリング
    if args.min_criticality > 1:
        print(f"\n🔍 Criticalityフィルタリング中...")
        logical_uuids = filter_by_criticality(logical_uuids, args.min_criticality)
        print(f"✓ フィルタリング後: {len(logical_uuids)} シナリオ")

    # バッチ実行
    success_count = 0
    failure_count = 0
    start_time = datetime.now()

    for i, logical_uuid in enumerate(logical_uuids, 1):
        print(f"\n進行状況: [{i}/{len(logical_uuids)}]")

        success = execute_scenario(logical_uuid, dry_run=args.dry_run)

        if success:
            success_count += 1
        else:
            failure_count += 1
            if not args.continue_on_error:
                print(f"\n❌ エラーにより中断します")
                break

    # サマリー
    end_time = datetime.now()
    elapsed = end_time - start_time

    print(f"\n{'='*60}")
    print(f"📊 バッチ実行完了")
    print(f"{'='*60}\n")
    print(f"成功: {success_count}")
    print(f"失敗: {failure_count}")
    print(f"合計: {success_count + failure_count}")
    print(f"実行時間: {elapsed}")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
