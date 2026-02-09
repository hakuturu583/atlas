#!/usr/bin/env python3
"""CARLA起動・停止CLIツール

CarlaUnreal.shを実行してCARLAサーバーを起動・停止します。
"""

import asyncio
import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.carla_manager import get_carla_manager


def format_status(status: dict) -> str:
    """状態情報を整形"""
    if status["running"]:
        lines = [
            "=== CARLA Status ===",
            f"Status: Running",
            f"PID: {status['pid']}",
            f"Host: {status['host']}",
            f"Port: {status['port']}",
        ]
        if "memory_mb" in status:
            lines.append(f"Memory: {status['memory_mb']:.1f} MB")
        if "cpu_percent" in status:
            lines.append(f"CPU: {status['cpu_percent']:.1f}%")
        return "\n".join(lines)
    else:
        return "=== CARLA Status ===\nStatus: Not running"


async def launch_command(args):
    """CARLA起動コマンド"""
    manager = get_carla_manager()

    print("Starting CARLA...")
    result = await manager.launch_carla(port=args.port, map_name=args.map)

    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"  Host: {result['host']}")
        print(f"  Port: {result['port']}")
        print(f"  PID: {result['pid']}")
        print(f"  Command: {result['command']}")
        return 0
    else:
        print(f"✗ {result['message']}")
        if "error" in result:
            print(f"  Error: {result['error']}")
        return 1


def stop_command(args):
    """CARLA停止コマンド"""
    manager = get_carla_manager()

    print("Stopping CARLA...")
    result = manager.stop_carla()

    if result["success"]:
        print(f"✓ {result['message']}")
        return 0
    else:
        print(f"✗ {result['message']}")
        if "error" in result:
            print(f"  Error: {result['error']}")
        return 1


def status_command(args):
    """CARLA状態確認コマンド"""
    manager = get_carla_manager()
    status = manager.get_status()

    print(format_status(status))

    if args.verbose:
        print("\n=== Settings ===")
        settings = status["settings"]
        print(f"CARLA Path: {settings['carla_path']}")
        print(f"Executable: {settings['executable_name']}")
        print(f"Default Port: {settings['default_port']}")
        print(f"Default Map: {settings['default_map']}")
        print(f"Quality: {settings['quality_level']}")
        print(f"Additional Args: {settings['additional_args']}")
        print(f"Timeout: {settings['timeout']}s")
        print(f"Auto Start: {settings['auto_start']}")

    return 0


def config_command(args):
    """CARLA設定更新コマンド"""
    manager = get_carla_manager()

    updates = {}
    if args.carla_path:
        updates["carla_path"] = args.carla_path
    if args.executable:
        updates["executable_name"] = args.executable
    if args.port:
        updates["default_port"] = args.port
    if args.map:
        updates["default_map"] = args.map
    if args.quality:
        updates["quality_level"] = args.quality
    if args.additional_args:
        updates["additional_args"] = args.additional_args
    if args.timeout:
        updates["timeout"] = args.timeout
    if args.auto_start is not None:
        updates["auto_start"] = args.auto_start

    if not updates:
        print("No updates specified. Use --help to see available options.")
        return 1

    # 現在の設定を取得してマージ
    current_settings = manager.get_settings().model_dump()
    current_settings.update(updates)

    # 設定を更新
    new_settings = manager.update_settings(current_settings)

    print("✓ Settings updated:")
    for key, value in updates.items():
        print(f"  {key}: {value}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="CARLA Server Launcher - CarlaUnreal.shを実行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # CARLA起動
  %(prog)s launch

  # カスタムポートで起動
  %(prog)s launch --port 2001

  # 特定のマップで起動
  %(prog)s launch --map Town04

  # CARLA停止
  %(prog)s stop

  # 状態確認
  %(prog)s status

  # 詳細な状態確認
  %(prog)s status -v

  # 設定変更
  %(prog)s config --carla-path /opt/carla-simulator
  %(prog)s config --port 2001 --map Town10HD
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # launch コマンド
    launch_parser = subparsers.add_parser("launch", help="Start CARLA server")
    launch_parser.add_argument(
        "--port", "-p",
        type=int,
        help="CARLA RPC port (default: from settings)"
    )
    launch_parser.add_argument(
        "--map", "-m",
        type=str,
        help="Map name to load (default: from settings)"
    )

    # stop コマンド
    stop_parser = subparsers.add_parser("stop", help="Stop CARLA server")

    # status コマンド
    status_parser = subparsers.add_parser("status", help="Show CARLA status")
    status_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed information including settings"
    )

    # config コマンド
    config_parser = subparsers.add_parser("config", help="Update CARLA settings")
    config_parser.add_argument(
        "--carla-path",
        type=str,
        help="CARLA installation directory path"
    )
    config_parser.add_argument(
        "--executable",
        type=str,
        help="CARLA executable name (e.g., CarlaUnreal.sh)"
    )
    config_parser.add_argument(
        "--port",
        type=int,
        help="Default CARLA RPC port"
    )
    config_parser.add_argument(
        "--map",
        type=str,
        help="Default map name"
    )
    config_parser.add_argument(
        "--quality",
        type=str,
        choices=["Low", "Medium", "Epic"],
        help="Graphics quality level"
    )
    config_parser.add_argument(
        "--additional-args",
        type=str,
        help="Additional launch arguments"
    )
    config_parser.add_argument(
        "--timeout",
        type=int,
        help="Launch timeout in seconds"
    )
    config_parser.add_argument(
        "--auto-start",
        type=lambda x: x.lower() == "true",
        help="Auto start on system startup (true/false)"
    )

    args = parser.parse_args()

    if args.command == "launch":
        return asyncio.run(launch_command(args))
    elif args.command == "stop":
        return stop_command(args)
    elif args.command == "status":
        return status_command(args)
    elif args.command == "config":
        return config_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
