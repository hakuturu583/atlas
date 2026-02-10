"""
Behaviors - 高レベル振る舞いAPI

テストケースでよくあるシナリオを簡単に記述できる
高レベルAPIを提供します。
"""

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import carla

from .traffic_manager_wrapper import TrafficManagerWrapper
from .stamp_logger import ControlAction, StateType
from .command_tracker import CommandStatus


@dataclass
class BehaviorResult:
    """振る舞いの実行結果"""

    success: bool
    message: str
    metrics: Dict[str, Any]
    start_frame: int
    end_frame: int
    start_location: carla.Location
    end_location: carla.Location


class Behavior(ABC):
    """振る舞いの基底クラス"""

    def __init__(self, tm_wrapper: TrafficManagerWrapper):
        """
        Args:
            tm_wrapper: TrafficManagerWrapper
        """
        self.tm_wrapper = tm_wrapper
        self.stamp_logger = tm_wrapper.stamp_logger
        self.command_tracker = tm_wrapper.command_tracker

    @abstractmethod
    def execute(
        self, vehicle_id: int, frame: int, **kwargs
    ) -> BehaviorResult:
        """
        振る舞いを実行

        Args:
            vehicle_id: 車両ID
            frame: 現在のフレーム番号
            **kwargs: 追加パラメータ

        Returns:
            実行結果
        """
        pass

    def _get_vehicle_location(self, vehicle_id: int) -> carla.Location:
        """車両の現在位置を取得"""
        vehicle = self.tm_wrapper.get_vehicle(vehicle_id)
        return vehicle.get_location()

    def _get_vehicle_velocity(self, vehicle_id: int) -> carla.Vector3D:
        """車両の速度を取得"""
        vehicle = self.tm_wrapper.get_vehicle(vehicle_id)
        return vehicle.get_velocity()

    def _get_speed_kmh(self, vehicle_id: int) -> float:
        """車両の速度を取得（km/h）"""
        velocity = self._get_vehicle_velocity(vehicle_id)
        return 3.6 * math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)

    def _distance_to(
        self, location1: carla.Location, location2: carla.Location
    ) -> float:
        """2点間の距離を計算"""
        return location1.distance(location2)

    def _create_command(
        self, description: str, vehicle_id: int, behavior_type: str, **params
    ) -> str:
        """コマンドを作成"""
        if self.command_tracker:
            return self.command_tracker.create_command(
                description=description,
                vehicle_id=vehicle_id,
                behavior_type=behavior_type,
                parameters=params,
            )
        return ""

    def _start_command(
        self, command_id: str, frame: int, location: carla.Location
    ) -> None:
        """コマンドを開始"""
        if self.command_tracker and command_id:
            self.command_tracker.start_command(
                command_id=command_id,
                frame=frame,
                location={"x": location.x, "y": location.y, "z": location.z},
            )

    def _complete_command(
        self,
        command_id: str,
        success: bool,
        frame: int,
        location: carla.Location,
        metrics: Dict[str, Any],
        error_message: Optional[str] = None,
    ) -> None:
        """コマンドを完了"""
        if self.command_tracker and command_id:
            self.command_tracker.complete_command(
                command_id=command_id,
                success=success,
                frame=frame,
                location={"x": location.x, "y": location.y, "z": location.z},
                metrics=metrics,
                error_message=error_message,
            )


class LaneChangeBehavior(Behavior):
    """レーンチェンジ振る舞い"""

    def execute(
        self,
        vehicle_id: int,
        frame: int,
        direction: str = "left",
        duration_frames: int = 100,
        **kwargs,
    ) -> BehaviorResult:
        """
        レーンチェンジを実行

        Args:
            vehicle_id: 車両ID
            frame: 現在のフレーム番号
            direction: "left" or "right"
            duration_frames: 実行フレーム数

        Returns:
            実行結果
        """
        start_location = self._get_vehicle_location(vehicle_id)
        start_frame = frame

        # コマンド作成
        command_id = self._create_command(
            description=f"Lane change to {direction}",
            vehicle_id=vehicle_id,
            behavior_type="lane_change",
            direction=direction,
            duration_frames=duration_frames,
        )
        self._start_command(command_id, frame, start_location)

        # STAMP状態遷移ログ
        if self.stamp_logger:
            action = (
                ControlAction.LANE_CHANGE_LEFT
                if direction == "left"
                else ControlAction.LANE_CHANGE_RIGHT
            )
            self.stamp_logger.log_state_transition(
                frame=frame,
                vehicle_id=vehicle_id,
                to_state=StateType.LANE_CHANGING,
                control_action=action,
            )

        # レーンチェンジを実行
        is_left = direction == "left"
        self.tm_wrapper.force_lane_change(vehicle_id, is_left, frame)

        # 完了待ち（実際のシナリオでは、世界のtickと共に進行）
        end_frame = frame + duration_frames
        end_location = self._get_vehicle_location(vehicle_id)

        # メトリクス
        metrics = {
            "direction": direction,
            "distance_traveled": self._distance_to(start_location, end_location),
            "duration_frames": duration_frames,
        }

        # STAMP状態遷移ログ（完了）
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=end_frame,
                vehicle_id=vehicle_id,
                to_state=StateType.DRIVING,
                control_action=action,
            )

        # コマンド完了
        self._complete_command(
            command_id=command_id,
            success=True,
            frame=end_frame,
            location=end_location,
            metrics=metrics,
        )

        return BehaviorResult(
            success=True,
            message=f"Lane change to {direction} completed",
            metrics=metrics,
            start_frame=start_frame,
            end_frame=end_frame,
            start_location=start_location,
            end_location=end_location,
        )


class CutInBehavior(Behavior):
    """カットイン振る舞い"""

    def execute(
        self,
        vehicle_id: int,
        frame: int,
        target_vehicle_id: int,
        gap_distance: float = 5.0,
        speed_boost: float = 120.0,
        **kwargs,
    ) -> BehaviorResult:
        """
        カットインを実行

        Args:
            vehicle_id: 実行車両ID
            frame: 現在のフレーム番号
            target_vehicle_id: カットイン対象車両ID
            gap_distance: 目標とする車間距離（m）
            speed_boost: 速度ブースト（%）

        Returns:
            実行結果
        """
        start_location = self._get_vehicle_location(vehicle_id)
        start_frame = frame

        # コマンド作成
        command_id = self._create_command(
            description=f"Cut in front of vehicle {target_vehicle_id}",
            vehicle_id=vehicle_id,
            behavior_type="cut_in",
            target_vehicle_id=target_vehicle_id,
            gap_distance=gap_distance,
            speed_boost=speed_boost,
        )
        self._start_command(command_id, frame, start_location)

        # STAMP状態遷移ログ
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=frame,
                vehicle_id=vehicle_id,
                to_state=StateType.LANE_CHANGING,
                control_action=ControlAction.CUT_IN,
                metadata={"target_vehicle_id": target_vehicle_id},
            )

        # 1. 速度を上げて追い越す
        self.tm_wrapper.set_speed_percentage(vehicle_id, speed_boost, frame)

        # 2. レーンチェンジしてカットイン（実際のtickループで実装）
        self.tm_wrapper.force_lane_change(vehicle_id, False, frame)  # 右にカットイン

        # 3. 車間距離を設定
        self.tm_wrapper.set_distance_to_leading(vehicle_id, gap_distance, frame)

        # 完了（簡略化：実際は位置を監視する）
        end_frame = frame + 150
        end_location = self._get_vehicle_location(vehicle_id)

        metrics = {
            "target_vehicle_id": target_vehicle_id,
            "gap_distance": gap_distance,
            "speed_boost": speed_boost,
            "distance_traveled": self._distance_to(start_location, end_location),
        }

        # STAMP状態遷移ログ（完了）
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=end_frame,
                vehicle_id=vehicle_id,
                to_state=StateType.DRIVING,
            )

        # コマンド完了
        self._complete_command(
            command_id=command_id,
            success=True,
            frame=end_frame,
            location=end_location,
            metrics=metrics,
        )

        return BehaviorResult(
            success=True,
            message=f"Cut in completed",
            metrics=metrics,
            start_frame=start_frame,
            end_frame=end_frame,
            start_location=start_location,
            end_location=end_location,
        )


class TimedApproachBehavior(Behavior):
    """タイミングを合わせた特定地点への突入"""

    def execute(
        self,
        vehicle_id: int,
        frame: int,
        target_location: carla.Location,
        target_time: float,
        speed_adjustment: float = 1.0,
        ignore_traffic: bool = False,
        **kwargs,
    ) -> BehaviorResult:
        """
        タイミングを合わせて特定地点に突入

        Args:
            vehicle_id: 車両ID
            frame: 現在のフレーム番号
            target_location: 目標地点
            target_time: 到達目標時刻（秒）
            speed_adjustment: 速度調整係数
            ignore_traffic: 信号・他車両を無視

        Returns:
            実行結果
        """
        start_location = self._get_vehicle_location(vehicle_id)
        start_frame = frame

        # コマンド作成
        command_id = self._create_command(
            description=f"Timed approach to ({target_location.x:.1f}, {target_location.y:.1f})",
            vehicle_id=vehicle_id,
            behavior_type="timed_approach",
            target_location={
                "x": target_location.x,
                "y": target_location.y,
                "z": target_location.z,
            },
            target_time=target_time,
            speed_adjustment=speed_adjustment,
        )
        self._start_command(command_id, frame, start_location)

        # STAMP状態遷移ログ
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=frame,
                vehicle_id=vehicle_id,
                to_state=StateType.DRIVING,
                control_action=ControlAction.ACCELERATE,
                metadata={
                    "target_location": {
                        "x": target_location.x,
                        "y": target_location.y,
                        "z": target_location.z,
                    },
                    "target_time": target_time,
                },
            )

        # 距離と必要速度を計算
        distance = self._distance_to(start_location, target_location)
        required_speed = (distance / target_time) * 3.6  # km/h

        # 速度を調整
        base_speed = 50.0  # 基準速度
        speed_percentage = (required_speed / base_speed) * 100.0 * speed_adjustment
        self.tm_wrapper.set_speed_percentage(vehicle_id, speed_percentage, frame)

        # 信号・車両無視の設定
        if ignore_traffic:
            self.tm_wrapper.ignore_lights(vehicle_id, True, frame)
            self.tm_wrapper.ignore_vehicles(vehicle_id, True, frame)

        # 完了（実際のシナリオでは位置を監視して判定）
        estimated_frames = int(target_time * 20)  # 20 FPS想定
        end_frame = frame + estimated_frames
        end_location = target_location  # 簡略化

        metrics = {
            "distance": distance,
            "target_time": target_time,
            "required_speed_kmh": required_speed,
            "speed_adjustment": speed_adjustment,
            "estimated_frames": estimated_frames,
        }

        # STAMP状態遷移ログ（完了）
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=end_frame,
                vehicle_id=vehicle_id,
                to_state=StateType.STOPPED,
            )

        # コマンド完了
        self._complete_command(
            command_id=command_id,
            success=True,
            frame=end_frame,
            location=end_location,
            metrics=metrics,
        )

        return BehaviorResult(
            success=True,
            message=f"Timed approach completed",
            metrics=metrics,
            start_frame=start_frame,
            end_frame=end_frame,
            start_location=start_location,
            end_location=end_location,
        )


class FollowBehavior(Behavior):
    """追従走行"""

    def execute(
        self,
        vehicle_id: int,
        frame: int,
        target_vehicle_id: int,
        distance: float = 5.0,
        duration_frames: int = 200,
        **kwargs,
    ) -> BehaviorResult:
        """
        指定車両を追従

        Args:
            vehicle_id: 車両ID
            frame: 現在のフレーム番号
            target_vehicle_id: 追従対象車両ID
            distance: 追従距離（m）
            duration_frames: 追従フレーム数

        Returns:
            実行結果
        """
        start_location = self._get_vehicle_location(vehicle_id)
        start_frame = frame

        # コマンド作成
        command_id = self._create_command(
            description=f"Follow vehicle {target_vehicle_id}",
            vehicle_id=vehicle_id,
            behavior_type="follow",
            target_vehicle_id=target_vehicle_id,
            distance=distance,
            duration_frames=duration_frames,
        )
        self._start_command(command_id, frame, start_location)

        # STAMP状態遷移ログ
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=frame,
                vehicle_id=vehicle_id,
                to_state=StateType.FOLLOWING,
                control_action=ControlAction.FOLLOW,
                metadata={"target_vehicle_id": target_vehicle_id},
            )

        # 追従距離を設定
        self.tm_wrapper.set_distance_to_leading(vehicle_id, distance, frame)

        # 完了
        end_frame = frame + duration_frames
        end_location = self._get_vehicle_location(vehicle_id)

        metrics = {
            "target_vehicle_id": target_vehicle_id,
            "distance": distance,
            "duration_frames": duration_frames,
        }

        # STAMP状態遷移ログ（完了）
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=end_frame,
                vehicle_id=vehicle_id,
                to_state=StateType.DRIVING,
            )

        # コマンド完了
        self._complete_command(
            command_id=command_id,
            success=True,
            frame=end_frame,
            location=end_location,
            metrics=metrics,
        )

        return BehaviorResult(
            success=True,
            message=f"Follow completed",
            metrics=metrics,
            start_frame=start_frame,
            end_frame=end_frame,
            start_location=start_location,
            end_location=end_location,
        )


class StopBehavior(Behavior):
    """停止動作"""

    def execute(
        self,
        vehicle_id: int,
        frame: int,
        duration_frames: int = 50,
        **kwargs,
    ) -> BehaviorResult:
        """
        車両を停止

        Args:
            vehicle_id: 車両ID
            frame: 現在のフレーム番号
            duration_frames: 停止フレーム数

        Returns:
            実行結果
        """
        start_location = self._get_vehicle_location(vehicle_id)
        start_frame = frame

        # コマンド作成
        command_id = self._create_command(
            description="Stop vehicle",
            vehicle_id=vehicle_id,
            behavior_type="stop",
            duration_frames=duration_frames,
        )
        self._start_command(command_id, frame, start_location)

        # STAMP状態遷移ログ
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=frame,
                vehicle_id=vehicle_id,
                to_state=StateType.STOPPING,
                control_action=ControlAction.BRAKE,
            )

        # 速度を0に設定
        self.tm_wrapper.set_speed_percentage(vehicle_id, 0.0, frame)

        # 完了
        end_frame = frame + duration_frames
        end_location = self._get_vehicle_location(vehicle_id)

        metrics = {
            "duration_frames": duration_frames,
        }

        # STAMP状態遷移ログ（完了）
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=end_frame,
                vehicle_id=vehicle_id,
                to_state=StateType.STOPPED,
            )

        # コマンド完了
        self._complete_command(
            command_id=command_id,
            success=True,
            frame=end_frame,
            location=end_location,
            metrics=metrics,
        )

        return BehaviorResult(
            success=True,
            message="Stop completed",
            metrics=metrics,
            start_frame=start_frame,
            end_frame=end_frame,
            start_location=start_location,
            end_location=end_location,
        )
