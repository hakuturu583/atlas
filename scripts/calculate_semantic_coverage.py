"""
意味論的カバレッジ計算スクリプト

状態遷移行列を作成し、カバレッジを計算します。

使い方:
    # 単一のメトリクスログを分析
    python scripts/calculate_semantic_coverage.py --metrics-log data/logs/metrics/scenario_uuid_metrics.json

    # 抽象シナリオに関連するすべてのログを集計
    python scripts/calculate_semantic_coverage.py --abstract-uuid <abstract_uuid>

    # 論理シナリオに関連するすべてのログを集計
    python scripts/calculate_semantic_coverage.py --logical-uuid <logical_uuid>
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np


# イベントタイプの定義
EVENT_TYPES = [
    "sudden_braking",
    "sudden_acceleration",
    "high_jerk",
    "low_ttc",
    "min_distance_violation",
]


class SemanticCoverageCalculator:
    """意味論的カバレッジ計算クラス"""

    def __init__(self):
        """初期化"""
        self.event_types = EVENT_TYPES
        self.n_events = len(self.event_types)

        # カバレッジ行列（2N x 2N）
        # 縦軸（To）: 遷移後の状態
        #   - 行 0 ~ N-1: Safe状態
        #   - 行 N ~ 2N-1: Unsafe状態
        # 横軸（From）: 遷移前の状態
        #   - 列 0 ~ N-1: Safe状態
        #   - 列 N ~ 2N-1: Unsafe状態
        #
        # 有効セル:
        #   - Safe => Unsafe: [N+i, i] (i = 0 to N-1) → N個
        #   - Unsafe => Safe: [i, N+i] (i = 0 to N-1) → N個
        #   - 合計: 2N個
        self.coverage_matrix = np.zeros((2 * self.n_events, 2 * self.n_events), dtype=int)

        # 各イベントタイプのインデックス
        self.event_index = {event: i for i, event in enumerate(self.event_types)}

    def load_metrics_log(self, log_path: Path) -> dict:
        """メトリクスログを読み込む"""
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def process_log(self, log_path: Path):
        """単一のログファイルを処理"""
        print(f"Processing: {log_path}")
        data = self.load_metrics_log(log_path)

        events = data.get("events", [])
        for event in events:
            event_type = event["event_type"]
            transition = event["transition"]

            if event_type not in self.event_index:
                continue

            idx = self.event_index[event_type]
            N = self.n_events

            # Safe => Unsafe: 行[N+idx]（Unsafe）、列[idx]（Safe）
            if transition == "safe_to_unsafe":
                self.coverage_matrix[N + idx, idx] += 1

            # Unsafe => Safe: 行[idx]（Safe）、列[N+idx]（Unsafe）
            elif transition == "unsafe_to_safe":
                self.coverage_matrix[idx, N + idx] += 1

    def calculate_coverage(self) -> Tuple[int, int, float]:
        """
        カバレッジを計算

        Returns:
            (カバーされたセル数, 有効セル数, カバレッジ率)
        """
        N = self.n_events

        # 有効セル = 2N個
        # - Safe => Unsafe: N個
        # - Unsafe => Safe: N個
        valid_cells = 2 * N

        # カバーされたセル数をカウント
        covered_cells = 0

        for i in range(N):
            # Safe => Unsafe: [N+i, i]
            if self.coverage_matrix[N + i, i] > 0:
                covered_cells += 1

            # Unsafe => Safe: [i, N+i]
            if self.coverage_matrix[i, N + i] > 0:
                covered_cells += 1

        # カバレッジ率
        coverage_rate = covered_cells / valid_cells if valid_cells > 0 else 0.0

        return covered_cells, valid_cells, coverage_rate

    def print_matrix(self):
        """カバレッジ行列を表示"""
        print("\n" + "=" * 80)
        print("  状態遷移カバレッジ行列")
        print("=" * 80)

        # ヘッダー
        print("\n各イベントタイプについて、Safe => Unsafe と Unsafe => Safe を別セルとして集計\n")

        # イベントタイプ名の短縮版
        short_names = {
            "sudden_braking": "急ブレーキ",
            "sudden_acceleration": "急加速",
            "high_jerk": "高ジャーク",
            "low_ttc": "低TTC",
            "min_distance_violation": "最小車間距離",
        }

        N = self.n_events

        # 表のヘッダー
        print(f"{'イベントタイプ':<20} | Safe=>Unsafe | Unsafe=>Safe")
        print("-" * 60)

        # 各イベントタイプの遷移を表示
        for i, event_type in enumerate(self.event_types):
            short_name = short_names.get(event_type, event_type)

            # Safe => Unsafe: [N+i, i]
            safe_to_unsafe = self.coverage_matrix[N + i, i]
            s2u_status = "✓" if safe_to_unsafe > 0 else "✗"

            # Unsafe => Safe: [i, N+i]
            unsafe_to_safe = self.coverage_matrix[i, N + i]
            u2s_status = "✓" if unsafe_to_safe > 0 else "✗"

            print(
                f"{short_name:<20} | {s2u_status} {safe_to_unsafe:>10} | {u2s_status} {unsafe_to_safe:>10}"
            )

        print("=" * 80 + "\n")

    def print_summary(self):
        """サマリーを表示"""
        covered, valid, rate = self.calculate_coverage()

        print("\n" + "=" * 80)
        print("  意味論的カバレッジサマリー")
        print("=" * 80)

        print(f"\nカバーされたセル: {covered} / {valid}")
        print(f"カバレッジ率: {rate * 100:.1f}%")

        N = self.n_events

        print("\n各イベントタイプの状態遷移:")
        for i, event_type in enumerate(self.event_types):
            # Safe => Unsafe: [N+i, i]
            safe_to_unsafe = self.coverage_matrix[N + i, i]

            # Unsafe => Safe: [i, N+i]
            unsafe_to_safe = self.coverage_matrix[i, N + i]

            total = safe_to_unsafe + unsafe_to_safe

            if total > 0:
                print(
                    f"  ✓ {event_type}: Safe=>Unsafe {safe_to_unsafe}回, Unsafe=>Safe {unsafe_to_safe}回"
                )
            else:
                print(f"  ✗ {event_type}: 遷移なし")

        print("=" * 80 + "\n")


def find_metrics_logs_by_abstract_uuid(abstract_uuid: str) -> List[Path]:
    """
    抽象シナリオUUIDから関連するメトリクスログを検索

    Args:
        abstract_uuid: 抽象シナリオUUID

    Returns:
        メトリクスログのパスリスト
    """
    try:
        from scripts.scenario_manager import ScenarioManager
    except ImportError:
        print("✗ scenario_manager.pyが見つかりません")
        return []

    manager = ScenarioManager()

    # 抽象シナリオから論理シナリオを取得
    logical_scenarios = manager.list_logical_scenarios(abstract_uuid)

    metrics_logs = []
    for logical in logical_scenarios:
        logical_uuid = logical["uuid"]
        # 論理シナリオから具体シナリオ（パラメータ）を取得
        logs = find_metrics_logs_by_logical_uuid(logical_uuid)
        metrics_logs.extend(logs)

    return metrics_logs


def find_metrics_logs_by_logical_uuid(logical_uuid: str) -> List[Path]:
    """
    論理シナリオUUIDから関連するメトリクスログを検索

    Args:
        logical_uuid: 論理シナリオUUID

    Returns:
        メトリクスログのパスリスト
    """
    try:
        from scripts.scenario_manager import ScenarioManager
    except ImportError:
        print("✗ scenario_manager.pyが見つかりません")
        return []

    manager = ScenarioManager()

    # 論理シナリオからパラメータを取得
    parameters = manager.list_parameters(logical_uuid)

    metrics_logs = []
    metrics_dir = Path("data/logs/metrics")

    if not metrics_dir.exists():
        return []

    # 各パラメータに対応するメトリクスログを検索
    # ファイル名形式: <scenario_uuid>_metrics.json
    # scenario_uuid = f"{logical_uuid}_{params_uuid}" (想定)
    # または scenario_uuid = logical_uuid のみ

    for params in parameters:
        # logical_uuid を含むメトリクスログを検索
        for log_file in metrics_dir.glob(f"*{logical_uuid}*_metrics.json"):
            if log_file not in metrics_logs:
                metrics_logs.append(log_file)

    return metrics_logs


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="意味論的カバレッジ計算スクリプト"
    )
    parser.add_argument(
        "--metrics-log",
        type=str,
        help="メトリクスログファイルのパス",
    )
    parser.add_argument(
        "--abstract-uuid",
        type=str,
        help="抽象シナリオUUID（関連する全ログを集計）",
    )
    parser.add_argument(
        "--logical-uuid",
        type=str,
        help="論理シナリオUUID（関連する全ログを集計）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="カバレッジ結果をJSONファイルに出力",
    )

    args = parser.parse_args()

    # 引数の検証
    if not any([args.metrics_log, args.abstract_uuid, args.logical_uuid]):
        parser.error(
            "いずれかの引数を指定してください: --metrics-log, --abstract-uuid, --logical-uuid"
        )

    calculator = SemanticCoverageCalculator()

    # ログファイルの収集
    log_files: List[Path] = []

    if args.metrics_log:
        log_files.append(Path(args.metrics_log))
    elif args.abstract_uuid:
        print(f"抽象シナリオ {args.abstract_uuid} に関連するログを検索中...")
        log_files = find_metrics_logs_by_abstract_uuid(args.abstract_uuid)
        if not log_files:
            print(f"✗ 関連するメトリクスログが見つかりませんでした")
            return 1
        print(f"✓ {len(log_files)} 個のメトリクスログを発見")
    elif args.logical_uuid:
        print(f"論理シナリオ {args.logical_uuid} に関連するログを検索中...")
        log_files = find_metrics_logs_by_logical_uuid(args.logical_uuid)
        if not log_files:
            print(f"✗ 関連するメトリクスログが見つかりませんでした")
            return 1
        print(f"✓ {len(log_files)} 個のメトリクスログを発見")

    # ログファイルを処理
    for log_file in log_files:
        if not log_file.exists():
            print(f"⚠ ファイルが存在しません: {log_file}")
            continue
        calculator.process_log(log_file)

    # カバレッジ行列を表示
    calculator.print_matrix()

    # サマリーを表示
    calculator.print_summary()

    # JSONファイルに出力
    if args.output:
        output_path = Path(args.output)
        covered, valid, rate = calculator.calculate_coverage()

        result = {
            "covered_cells": covered,
            "valid_cells": valid,
            "coverage_rate": rate,
            "coverage_matrix": calculator.coverage_matrix.tolist(),
            "event_types": calculator.event_types,
            "processed_logs": [str(f) for f in log_files],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"カバレッジ結果を保存: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
