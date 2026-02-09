#!/usr/bin/env python3
"""
完全クリーンアップスクリプト

シナリオ関連のすべてのファイルとログを削除します：
- シナリオJSON（abstract, logical, parameters）
- Pythonスクリプト
- 動画ファイル（.mp4）
- RRDファイル（.rrd）
- Embeddingファイル（.json, .npy）
- ログファイル
- FiftyOneデータセット
- Sandboxワークスペース（オプション）
"""

import argparse
import shutil
from pathlib import Path
from typing import Dict, List


def get_file_size(file_path: Path) -> int:
    """ファイルサイズを取得（バイト）"""
    try:
        return file_path.stat().st_size
    except:
        return 0


def format_size(size_bytes: int) -> str:
    """バイトを人間が読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def collect_files(base_dir: Path, include_sandbox: bool = False) -> Dict[str, List[Path]]:
    """削除対象ファイルを収集"""
    files = {
        "scenarios": [],
        "python": [],
        "videos": [],
        "rerun": [],
        "embeddings": [],
        "logs": [],
        "params": [],
    }

    scenarios_dir = base_dir / "data" / "scenarios"
    python_dir = base_dir / "scenarios"
    videos_dir = base_dir / "data" / "videos"
    rerun_dir = base_dir / "data" / "rerun"
    embeddings_dir = base_dir / "data" / "embeddings"
    logs_dir = base_dir / "logs"

    # シナリオJSON（abstract, logical）
    if scenarios_dir.exists():
        files["scenarios"].extend(scenarios_dir.glob("abstract_*.json"))
        files["scenarios"].extend(scenarios_dir.glob("logical_*.json"))
        files["scenarios"].extend(scenarios_dir.glob("execution_*.json"))

    # パラメータJSON
    if scenarios_dir.exists():
        files["params"].extend(scenarios_dir.glob("params_*.json"))
        files["params"].extend(scenarios_dir.glob("logical_*_parameters.json"))

    # Pythonスクリプト
    if python_dir.exists():
        files["python"].extend(python_dir.glob("*.py"))
        # examples/以下は除外
        files["python"] = [f for f in files["python"] if "examples" not in str(f)]

    # 動画ファイル
    if videos_dir.exists():
        files["videos"].extend(videos_dir.glob("*.mp4"))

    # RRDファイル
    if rerun_dir.exists():
        files["rerun"].extend(rerun_dir.glob("*.rrd"))

    # Embeddingファイル
    if embeddings_dir.exists():
        files["embeddings"].extend(embeddings_dir.glob("*.json"))
        files["embeddings"].extend(embeddings_dir.glob("*.npy"))

    # ログファイル
    if logs_dir.exists():
        files["logs"].extend(logs_dir.glob("*.log"))

    # Sandboxワークスペース（オプション）
    if include_sandbox:
        sandbox_workspace = base_dir / "sandbox" / "workspace"
        if sandbox_workspace.exists():
            # UUIDディレクトリを削除
            for uuid_dir in sandbox_workspace.iterdir():
                if uuid_dir.is_dir() and uuid_dir.name != ".gitkeep":
                    files.setdefault("sandbox", []).append(uuid_dir)

    return files


def delete_files(files: Dict[str, List[Path]], dry_run: bool = True) -> None:
    """ファイルを削除"""
    total_files = sum(len(file_list) for file_list in files.values())
    total_size = 0

    print("\n=== 削除対象ファイル ===\n")

    for category, file_list in files.items():
        if not file_list:
            continue

        category_size = sum(get_file_size(f) for f in file_list)
        total_size += category_size

        print(f"【{category}】")
        for file_path in file_list:
            size_str = format_size(get_file_size(file_path))
            print(f"  - {file_path} ({size_str})")
        print(f"  小計: {format_size(category_size)}\n")

    print(f"=== 合計: {total_files}ファイル, {format_size(total_size)} ===\n")

    if dry_run:
        print("ℹ️  ドライランモード: ファイルは削除されません")
        print("   実際に削除するには --force オプションを使用してください")
        return

    # 実際に削除
    deleted_count = 0
    for file_list in files.values():
        for file_path in file_list:
            try:
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
                print(f"✓ 削除: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"✗ エラー: {file_path} - {e}")

    print(f"\n✓ {deleted_count}ファイルを削除しました")


def delete_fiftyone_dataset(dataset_name: str = "carla-scenarios", dry_run: bool = True) -> None:
    """FiftyOneデータセットを削除"""
    try:
        import fiftyone as fo

        if fo.dataset_exists(dataset_name):
            print(f"\n【FiftyOne Dataset】")
            print(f"  - {dataset_name}")

            if not dry_run:
                fo.delete_dataset(dataset_name)
                print(f"✓ FiftyOneデータセット削除: {dataset_name}")
            else:
                print(f"  （削除予定）")
        else:
            print(f"\n【FiftyOne Dataset】")
            print(f"  - データセット '{dataset_name}' は存在しません")

    except ImportError:
        print("\n⚠️  FiftyOneがインストールされていません（スキップ）")
    except Exception as e:
        print(f"\n✗ FiftyOneデータセット削除エラー: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="シナリオ関連のすべてのファイルとログを削除"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="実際に削除を実行（デフォルトはドライラン）"
    )
    parser.add_argument(
        "--include-sandbox",
        action="store_true",
        help="Sandboxワークスペースも削除"
    )
    parser.add_argument(
        "--fiftyone-dataset",
        default="carla-scenarios",
        help="削除するFiftyOneデータセット名（デフォルト: carla-scenarios）"
    )
    parser.add_argument(
        "--no-fiftyone",
        action="store_true",
        help="FiftyOneデータセットを削除しない"
    )

    args = parser.parse_args()

    base_dir = Path.cwd()

    print("=" * 60)
    if args.force:
        print("🗑️  完全クリーンアップ（実行モード）")
    else:
        print("🔍 完全クリーンアップ（ドライラン）")
    print("=" * 60)

    # ファイル収集
    print("\nファイルを検索中...")
    files = collect_files(base_dir, include_sandbox=args.include_sandbox)

    # ファイル削除
    delete_files(files, dry_run=not args.force)

    # FiftyOneデータセット削除
    if not args.no_fiftyone:
        delete_fiftyone_dataset(args.fiftyone_dataset, dry_run=not args.force)

    if not args.force:
        print("\n💡 実際に削除するには:")
        print("   uv run python scripts/cleanup_all.py --force")


if __name__ == "__main__":
    main()
