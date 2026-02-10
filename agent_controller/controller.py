"""
Agent Controller - 統合制御クラス

すべての車両制御機能を単一のクラスから呼び出せる統合APIを提供します。
"""

from typing import Optional, Dict, Any
import carla

from .traffic_manager_wrapper import TrafficManagerWrapper
from .behaviors import (
    LaneChangeBehavior,
    CutInBehavior,
    TimedApproachBehavior,
    FollowBehavior,
    StopBehavior,
    BehaviorResult,
)
from .stamp_logger import STAMPLogger, ControlAction, StateType
from .command_tracker import CommandTracker, CommandStatus


class AgentController:
    """
    統合車両制御クラス

    CARLA Traffic Managerをラップし、高レベルAPIとロギング機能を提供する
    単一のインターフェースです。

    使用例:
        >>> controller = AgentController(client, scenario_uuid="my-scenario")
        >>> vehicle_id = controller.register_vehicle(vehicle)
        >>> controller.lane_change(vehicle_id, frame=100, direction="left")
        >>> controller.finalize()
    """

    def __init__(
        self,
        client: carla.Client,
        scenario_uuid: str,
        tm_port: int = 8000,
        enable_logging: bool = True,
    ):
        """
        AgentControllerを初期化

        Args:
            client: CARLAクライアント
            scenario_uuid: シナリオUUID
            tm_port: Traffic Managerのポート
            enable_logging: ロギングを有効化するか
        """
        self.client = client
        self.scenario_uuid = scenario_uuid
        self.enable_logging = enable_logging

        # ロガー初期化
        if enable_logging:
            self.stamp_logger = STAMPLogger(scenario_uuid=scenario_uuid)
            self.command_tracker = CommandTracker(scenario_uuid=scenario_uuid)
        else:
            self.stamp_logger = None
            self.command_tracker = None

        # Traffic Manager Wrapper初期化
        self.tm_wrapper = TrafficManagerWrapper(
            client=client,
            port=tm_port,
            stamp_logger=self.stamp_logger,
            command_tracker=self.command_tracker,
        )

        # Behavior初期化（遅延インスタンス化）
        self._lane_change_behavior = None
        self._cut_in_behavior = None
        self._timed_approach_behavior = None
        self._follow_behavior = None
        self._stop_behavior = None

    # ========================================
    # 車両登録・管理
    # ========================================

    def register_vehicle(
        self,
        vehicle: carla.Vehicle,
        auto_lane_change: bool = True,
        distance_to_leading: float = 2.5,
        speed_percentage: float = 100.0,
        ignore_lights: bool = False,
        ignore_vehicles: bool = False,
        ignore_signs: bool = False,
    ) -> int:
        """
        車両をTraffic Managerに登録

        Args:
            vehicle: 車両アクター
            auto_lane_change: 自動レーンチェンジを有効化
            distance_to_leading: 前方車両との距離（m）
            speed_percentage: 制限速度に対する速度パーセンテージ
            ignore_lights: 信号無視
            ignore_vehicles: 他車両無視
            ignore_signs: 標識無視

        Returns:
            車両ID
        """
        return self.tm_wrapper.register_vehicle(
            vehicle=vehicle,
            auto_lane_change=auto_lane_change,
            distance_to_leading=distance_to_leading,
            speed_percentage=speed_percentage,
            ignore_lights=ignore_lights,
            ignore_vehicles=ignore_vehicles,
            ignore_signs=ignore_signs,
        )

    def get_vehicle(self, vehicle_id: int) -> carla.Vehicle:
        """車両アクターを取得"""
        return self.tm_wrapper.get_vehicle(vehicle_id)

    def get_vehicle_config(self, vehicle_id: int) -> Dict[str, Any]:
        """車両設定を取得"""
        return self.tm_wrapper.get_vehicle_config(vehicle_id)

    def get_all_vehicles(self) -> list[int]:
        """登録されているすべての車両IDを取得"""
        return self.tm_wrapper.get_all_vehicles()

    # ========================================
    # 高レベル振る舞いAPI
    # ========================================

    def lane_change(
        self,
        vehicle_id: int,
        frame: int,
        direction: str = "left",
        duration_frames: int = 100,
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
        if self._lane_change_behavior is None:
            self._lane_change_behavior = LaneChangeBehavior(self.tm_wrapper)

        return self._lane_change_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            direction=direction,
            duration_frames=duration_frames,
        )

    def cut_in(
        self,
        vehicle_id: int,
        frame: int,
        target_vehicle_id: int,
        gap_distance: float = 5.0,
        speed_boost: float = 120.0,
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
        if self._cut_in_behavior is None:
            self._cut_in_behavior = CutInBehavior(self.tm_wrapper)

        return self._cut_in_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            target_vehicle_id=target_vehicle_id,
            gap_distance=gap_distance,
            speed_boost=speed_boost,
        )

    def timed_approach(
        self,
        vehicle_id: int,
        frame: int,
        target_location: carla.Location,
        target_time: float,
        speed_adjustment: float = 1.0,
        ignore_traffic: bool = False,
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
        if self._timed_approach_behavior is None:
            self._timed_approach_behavior = TimedApproachBehavior(self.tm_wrapper)

        return self._timed_approach_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            target_location=target_location,
            target_time=target_time,
            speed_adjustment=speed_adjustment,
            ignore_traffic=ignore_traffic,
        )

    def follow(
        self,
        vehicle_id: int,
        frame: int,
        target_vehicle_id: int,
        distance: float = 5.0,
        duration_frames: int = 200,
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
        if self._follow_behavior is None:
            self._follow_behavior = FollowBehavior(self.tm_wrapper)

        return self._follow_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            target_vehicle_id=target_vehicle_id,
            distance=distance,
            duration_frames=duration_frames,
        )

    def stop(
        self,
        vehicle_id: int,
        frame: int,
        duration_frames: int = 50,
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
        if self._stop_behavior is None:
            self._stop_behavior = StopBehavior(self.tm_wrapper)

        return self._stop_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            duration_frames=duration_frames,
        )

    # ========================================
    # 低レベルTraffic Manager設定
    # ========================================

    def set_auto_lane_change(
        self, vehicle_id: int, enable: bool, frame: Optional[int] = None
    ) -> None:
        """自動レーンチェンジの設定"""
        self.tm_wrapper.set_auto_lane_change(vehicle_id, enable, frame)

    def force_lane_change(
        self, vehicle_id: int, direction: bool, frame: Optional[int] = None
    ) -> None:
        """強制的にレーンチェンジを実行（True=左, False=右）"""
        self.tm_wrapper.force_lane_change(vehicle_id, direction, frame)

    def set_distance_to_leading(
        self, vehicle_id: int, distance: float, frame: Optional[int] = None
    ) -> None:
        """前方車両との距離を設定"""
        self.tm_wrapper.set_distance_to_leading(vehicle_id, distance, frame)

    def set_speed_percentage(
        self, vehicle_id: int, percentage: float, frame: Optional[int] = None
    ) -> None:
        """制限速度に対する速度パーセンテージを設定"""
        self.tm_wrapper.set_speed_percentage(vehicle_id, percentage, frame)

    def ignore_lights(
        self, vehicle_id: int, ignore: bool, frame: Optional[int] = None
    ) -> None:
        """信号無視の設定"""
        self.tm_wrapper.ignore_lights(vehicle_id, ignore, frame)

    def ignore_vehicles(
        self, vehicle_id: int, ignore: bool, frame: Optional[int] = None
    ) -> None:
        """他車両無視の設定"""
        self.tm_wrapper.ignore_vehicles(vehicle_id, ignore, frame)

    # ========================================
    # ロギング
    # ========================================

    def log_state_transition(
        self,
        frame: int,
        vehicle_id: int,
        to_state: StateType,
        control_action: Optional[ControlAction] = None,
        location: Optional[Dict[str, float]] = None,
        rotation: Optional[Dict[str, float]] = None,
        velocity: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """状態遷移を記録（手動ロギング用）"""
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=frame,
                vehicle_id=vehicle_id,
                to_state=to_state,
                control_action=control_action,
                location=location,
                rotation=rotation,
                velocity=velocity,
                metadata=metadata,
            )

    def log_control_action(
        self,
        frame: int,
        vehicle_id: int,
        action: ControlAction,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
    ) -> None:
        """制御アクションを記録（手動ロギング用）"""
        if self.stamp_logger:
            self.stamp_logger.log_control_action(
                frame=frame,
                vehicle_id=vehicle_id,
                action=action,
                parameters=parameters,
                result=result,
            )

    def get_vehicle_state(self, vehicle_id: int) -> StateType:
        """車両の現在の状態を取得"""
        if self.stamp_logger:
            return self.stamp_logger.get_vehicle_state(vehicle_id)
        return StateType.IDLE

    # ========================================
    # クリーンアップ
    # ========================================

    def finalize(self) -> tuple[Optional[str], Optional[str]]:
        """
        ログをファイナライズして保存

        Returns:
            (STAMP log path, Command log path)
        """
        stamp_log_path = None
        command_log_path = None

        if self.stamp_logger:
            stamp_log_path = str(self.stamp_logger.finalize())
            self.stamp_logger.print_summary()

        if self.command_tracker:
            command_log_path = str(self.command_tracker.finalize())
            self.command_tracker.print_summary()

        return stamp_log_path, command_log_path

    def cleanup(self) -> None:
        """クリーンアップ（車両のautopilot解除）"""
        self.tm_wrapper.cleanup()

    # ========================================
    # コンテキストマネージャ
    # ========================================

    def __enter__(self):
        """コンテキストマネージャのエントリ"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャの終了（自動クリーンアップ）"""
        self.finalize()
        self.cleanup()
        return False
