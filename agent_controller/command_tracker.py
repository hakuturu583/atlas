"""
Command Tracker

ユーザーから入力された指示を追跡し、
指示の完遂状態を記録します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class CommandStatus(Enum):
    """指示の実行状態"""

    PENDING = "pending"  # 実行待ち
    IN_PROGRESS = "in_progress"  # 実行中
    COMPLETED = "completed"  # 完了
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # キャンセル


@dataclass
class CommandRecord:
    """指示レコード"""

    command_id: str
    description: str  # ユーザーの指示内容
    status: CommandStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    # 実行情報
    vehicle_id: Optional[int] = None
    behavior_type: Optional[str] = None  # "lane_change", "cut_in", etc.
    parameters: Dict[str, Any] = field(default_factory=dict)

    # 結果
    success: bool = False
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    # 証跡
    frame_start: Optional[int] = None
    frame_end: Optional[int] = None
    location_start: Optional[Dict[str, float]] = None
    location_end: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "command_id": self.command_id,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "vehicle_id": self.vehicle_id,
            "behavior_type": self.behavior_type,
            "parameters": self.parameters,
            "success": self.success,
            "error_message": self.error_message,
            "metrics": self.metrics,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "location_start": self.location_start,
            "location_end": self.location_end,
        }


class CommandTracker:
    """
    ユーザー指示追跡システム

    ユーザーからの指示を追跡し、その完遂状態を記録します。
    """

    def __init__(
        self,
        scenario_uuid: str,
        output_dir: Path = Path("data/logs/commands"),
    ):
        """
        Args:
            scenario_uuid: シナリオUUID
            output_dir: ログ出力ディレクトリ
        """
        self.scenario_uuid = scenario_uuid
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.commands: Dict[str, CommandRecord] = {}
        self.start_time = datetime.now()
        self._command_counter = 0
        self._is_finalized = False

    def create_command(
        self,
        description: str,
        vehicle_id: Optional[int] = None,
        behavior_type: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        新しい指示を作成

        Args:
            description: 指示の説明
            vehicle_id: 対象車両ID
            behavior_type: 振る舞いタイプ
            parameters: パラメータ

        Returns:
            指示ID
        """
        self._command_counter += 1
        command_id = f"cmd_{self._command_counter:04d}"

        command = CommandRecord(
            command_id=command_id,
            description=description,
            status=CommandStatus.PENDING,
            created_at=datetime.now().timestamp(),
            vehicle_id=vehicle_id,
            behavior_type=behavior_type,
            parameters=parameters or {},
        )

        self.commands[command_id] = command
        return command_id

    def start_command(
        self,
        command_id: str,
        frame: Optional[int] = None,
        location: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        指示の実行を開始

        Args:
            command_id: 指示ID
            frame: 開始フレーム
            location: 開始位置 {x, y, z}
        """
        if command_id not in self.commands:
            raise ValueError(f"Command {command_id} not found")

        command = self.commands[command_id]
        command.status = CommandStatus.IN_PROGRESS
        command.started_at = datetime.now().timestamp()
        command.frame_start = frame
        command.location_start = location

    def complete_command(
        self,
        command_id: str,
        success: bool = True,
        frame: Optional[int] = None,
        location: Optional[Dict[str, float]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        指示を完了

        Args:
            command_id: 指示ID
            success: 成功したか
            frame: 終了フレーム
            location: 終了位置 {x, y, z}
            metrics: 実行メトリクス
            error_message: エラーメッセージ（失敗時）
        """
        if command_id not in self.commands:
            raise ValueError(f"Command {command_id} not found")

        command = self.commands[command_id]
        command.status = CommandStatus.COMPLETED if success else CommandStatus.FAILED
        command.completed_at = datetime.now().timestamp()
        command.success = success
        command.frame_end = frame
        command.location_end = location
        command.error_message = error_message

        if metrics:
            command.metrics.update(metrics)

        # 実行時間を計算
        if command.started_at and command.completed_at:
            command.metrics["duration_seconds"] = (
                command.completed_at - command.started_at
            )

        if command.frame_start and command.frame_end:
            command.metrics["duration_frames"] = command.frame_end - command.frame_start

    def cancel_command(self, command_id: str, reason: Optional[str] = None) -> None:
        """
        指示をキャンセル

        Args:
            command_id: 指示ID
            reason: キャンセル理由
        """
        if command_id not in self.commands:
            raise ValueError(f"Command {command_id} not found")

        command = self.commands[command_id]
        command.status = CommandStatus.CANCELLED
        command.completed_at = datetime.now().timestamp()
        command.error_message = reason

    def update_metrics(
        self, command_id: str, metrics: Dict[str, Any]
    ) -> None:
        """
        指示のメトリクスを更新

        Args:
            command_id: 指示ID
            metrics: 追加メトリクス
        """
        if command_id not in self.commands:
            raise ValueError(f"Command {command_id} not found")

        self.commands[command_id].metrics.update(metrics)

    def get_command(self, command_id: str) -> Optional[CommandRecord]:
        """指示を取得"""
        return self.commands.get(command_id)

    def get_pending_commands(self) -> List[CommandRecord]:
        """実行待ちの指示を取得"""
        return [
            cmd for cmd in self.commands.values() if cmd.status == CommandStatus.PENDING
        ]

    def get_in_progress_commands(self) -> List[CommandRecord]:
        """実行中の指示を取得"""
        return [
            cmd
            for cmd in self.commands.values()
            if cmd.status == CommandStatus.IN_PROGRESS
        ]

    def get_completed_commands(self) -> List[CommandRecord]:
        """完了した指示を取得"""
        return [
            cmd
            for cmd in self.commands.values()
            if cmd.status == CommandStatus.COMPLETED
        ]

    def get_failed_commands(self) -> List[CommandRecord]:
        """失敗した指示を取得"""
        return [
            cmd for cmd in self.commands.values() if cmd.status == CommandStatus.FAILED
        ]

    def finalize(self) -> Path:
        """
        ログをファイナライズして保存

        Returns:
            保存されたログファイルのパス
        """
        if self._is_finalized:
            return self._get_log_path()

        completed = self.get_completed_commands()
        failed = self.get_failed_commands()

        log_data = {
            "scenario_uuid": self.scenario_uuid,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "commands": [cmd.to_dict() for cmd in self.commands.values()],
            "summary": {
                "total_commands": len(self.commands),
                "completed": len(completed),
                "failed": len(failed),
                "success_rate": (
                    len(completed) / len(self.commands) if self.commands else 0.0
                ),
            },
        }

        log_path = self._get_log_path()
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2)

        self._is_finalized = True
        return log_path

    def _get_log_path(self) -> Path:
        """ログファイルパスを取得"""
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"commands_{self.scenario_uuid}_{timestamp}.json"

    def print_summary(self) -> None:
        """サマリーを出力"""
        completed = self.get_completed_commands()
        failed = self.get_failed_commands()
        in_progress = self.get_in_progress_commands()

        print("\n=== Command Tracker Summary ===")
        print(f"Scenario: {self.scenario_uuid}")
        print(f"Total Commands: {len(self.commands)}")
        print(f"  ✓ Completed: {len(completed)}")
        print(f"  ✗ Failed: {len(failed)}")
        print(f"  ⋯ In Progress: {len(in_progress)}")

        if self.commands:
            success_rate = len(completed) / len(self.commands) * 100
            print(f"Success Rate: {success_rate:.1f}%")

        if failed:
            print("\nFailed Commands:")
            for cmd in failed:
                print(f"  - {cmd.command_id}: {cmd.description}")
                if cmd.error_message:
                    print(f"    Error: {cmd.error_message}")
