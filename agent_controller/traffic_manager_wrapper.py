"""
Traffic Manager Wrapper

CARLA Traffic Managerをラップし、
高レベルAPIとロギング機能を提供します。
"""

from typing import Optional, Dict, Any, List
import carla

from .stamp_logger import STAMPLogger, ControlAction, StateType
from .command_tracker import CommandTracker


class TrafficManagerWrapper:
    """
    CARLA Traffic Managerのラッパークラス

    Traffic Managerの基本機能をラップし、
    STAMPロギングと指示追跡を統合します。
    """

    def __init__(
        self,
        client: carla.Client,
        port: int = 8000,
        stamp_logger: Optional[STAMPLogger] = None,
        command_tracker: Optional[CommandTracker] = None,
    ):
        """
        Args:
            client: CARLAクライアント
            port: Traffic Managerのポート
            stamp_logger: STAMPロガー（オプション）
            command_tracker: コマンドトラッカー（オプション）
        """
        self.client = client
        self.tm = client.get_trafficmanager(port)
        self.tm.set_synchronous_mode(True)

        self.stamp_logger = stamp_logger
        self.command_tracker = command_tracker

        # 車両管理
        self.vehicles: Dict[int, carla.Vehicle] = {}
        self.vehicle_configs: Dict[int, Dict[str, Any]] = {}

        # デフォルト設定
        self.tm.set_global_distance_to_leading_vehicle(2.5)
        self.tm.set_respawn_dormant_vehicles(False)

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
        vehicle_id = vehicle.id
        self.vehicles[vehicle_id] = vehicle

        # Traffic Manager設定
        self.tm.auto_lane_change(vehicle, auto_lane_change)
        self.tm.distance_to_leading_vehicle(vehicle, distance_to_leading)
        self.tm.vehicle_percentage_speed_difference(vehicle, 100.0 - speed_percentage)
        self.tm.ignore_lights_percentage(vehicle, 100.0 if ignore_lights else 0.0)
        self.tm.ignore_vehicles_percentage(vehicle, 100.0 if ignore_vehicles else 0.0)
        self.tm.ignore_signs_percentage(vehicle, 100.0 if ignore_signs else 0.0)

        # 設定を保存
        self.vehicle_configs[vehicle_id] = {
            "auto_lane_change": auto_lane_change,
            "distance_to_leading": distance_to_leading,
            "speed_percentage": speed_percentage,
            "ignore_lights": ignore_lights,
            "ignore_vehicles": ignore_vehicles,
            "ignore_signs": ignore_signs,
        }

        # Traffic Manager制御を有効化
        vehicle.set_autopilot(True, self.tm.get_port())

        # STAMPログ記録
        if self.stamp_logger:
            self.stamp_logger.log_control_action(
                frame=0,
                vehicle_id=vehicle_id,
                action=ControlAction.TM_AUTO_LANE_CHANGE,
                parameters=self.vehicle_configs[vehicle_id],
                result="success",
            )

        return vehicle_id

    def set_auto_lane_change(
        self, vehicle_id: int, enable: bool, frame: Optional[int] = None
    ) -> None:
        """
        自動レーンチェンジの設定

        Args:
            vehicle_id: 車両ID
            enable: 有効化するか
            frame: 現在のフレーム番号
        """
        if vehicle_id not in self.vehicles:
            raise ValueError(f"Vehicle {vehicle_id} not registered")

        vehicle = self.vehicles[vehicle_id]
        self.tm.auto_lane_change(vehicle, enable)
        self.vehicle_configs[vehicle_id]["auto_lane_change"] = enable

        # STAMPログ記録
        if self.stamp_logger and frame is not None:
            self.stamp_logger.log_control_action(
                frame=frame,
                vehicle_id=vehicle_id,
                action=ControlAction.TM_AUTO_LANE_CHANGE,
                parameters={"enable": enable},
                result="success",
            )

    def force_lane_change(
        self, vehicle_id: int, direction: bool, frame: Optional[int] = None
    ) -> None:
        """
        強制的にレーンチェンジを実行

        Args:
            vehicle_id: 車両ID
            direction: True=左, False=右
            frame: 現在のフレーム番号
        """
        if vehicle_id not in self.vehicles:
            raise ValueError(f"Vehicle {vehicle_id} not registered")

        vehicle = self.vehicles[vehicle_id]
        self.tm.force_lane_change(vehicle, direction)

        # STAMPログ記録
        if self.stamp_logger and frame is not None:
            action = (
                ControlAction.LANE_CHANGE_LEFT
                if direction
                else ControlAction.LANE_CHANGE_RIGHT
            )
            self.stamp_logger.log_control_action(
                frame=frame,
                vehicle_id=vehicle_id,
                action=action,
                parameters={"direction": "left" if direction else "right"},
                result="in_progress",
            )
            self.stamp_logger.log_state_transition(
                frame=frame,
                vehicle_id=vehicle_id,
                to_state=StateType.LANE_CHANGING,
                control_action=action,
            )

    def set_distance_to_leading(
        self, vehicle_id: int, distance: float, frame: Optional[int] = None
    ) -> None:
        """
        前方車両との距離を設定

        Args:
            vehicle_id: 車両ID
            distance: 距離（m）
            frame: 現在のフレーム番号
        """
        if vehicle_id not in self.vehicles:
            raise ValueError(f"Vehicle {vehicle_id} not registered")

        vehicle = self.vehicles[vehicle_id]
        self.tm.distance_to_leading_vehicle(vehicle, distance)
        self.vehicle_configs[vehicle_id]["distance_to_leading"] = distance

        # STAMPログ記録
        if self.stamp_logger and frame is not None:
            self.stamp_logger.log_control_action(
                frame=frame,
                vehicle_id=vehicle_id,
                action=ControlAction.TM_DISTANCE_TO_LEADING,
                parameters={"distance": distance},
                result="success",
            )

    def set_speed_percentage(
        self, vehicle_id: int, percentage: float, frame: Optional[int] = None
    ) -> None:
        """
        制限速度に対する速度パーセンテージを設定

        Args:
            vehicle_id: 車両ID
            percentage: 速度パーセンテージ（100.0=制限速度通り）
            frame: 現在のフレーム番号
        """
        if vehicle_id not in self.vehicles:
            raise ValueError(f"Vehicle {vehicle_id} not registered")

        vehicle = self.vehicles[vehicle_id]
        # Traffic Managerは差分で指定する
        difference = 100.0 - percentage
        self.tm.vehicle_percentage_speed_difference(vehicle, difference)
        self.vehicle_configs[vehicle_id]["speed_percentage"] = percentage

        # STAMPログ記録
        if self.stamp_logger and frame is not None:
            self.stamp_logger.log_control_action(
                frame=frame,
                vehicle_id=vehicle_id,
                action=ControlAction.TM_VEHICLE_PERCENTAGE_SPEED,
                parameters={"percentage": percentage},
                result="success",
            )

    def ignore_lights(
        self, vehicle_id: int, ignore: bool, frame: Optional[int] = None
    ) -> None:
        """
        信号無視の設定

        Args:
            vehicle_id: 車両ID
            ignore: 無視するか
            frame: 現在のフレーム番号
        """
        if vehicle_id not in self.vehicles:
            raise ValueError(f"Vehicle {vehicle_id} not registered")

        vehicle = self.vehicles[vehicle_id]
        self.tm.ignore_lights_percentage(vehicle, 100.0 if ignore else 0.0)
        self.vehicle_configs[vehicle_id]["ignore_lights"] = ignore

        # STAMPログ記録
        if self.stamp_logger and frame is not None:
            self.stamp_logger.log_control_action(
                frame=frame,
                vehicle_id=vehicle_id,
                action=ControlAction.TM_IGNORE_LIGHTS,
                parameters={"ignore": ignore},
                result="success",
            )

    def ignore_vehicles(
        self, vehicle_id: int, ignore: bool, frame: Optional[int] = None
    ) -> None:
        """
        他車両無視の設定

        Args:
            vehicle_id: 車両ID
            ignore: 無視するか
            frame: 現在のフレーム番号
        """
        if vehicle_id not in self.vehicles:
            raise ValueError(f"Vehicle {vehicle_id} not registered")

        vehicle = self.vehicles[vehicle_id]
        self.tm.ignore_vehicles_percentage(vehicle, 100.0 if ignore else 0.0)
        self.vehicle_configs[vehicle_id]["ignore_vehicles"] = ignore

        # STAMPログ記録
        if self.stamp_logger and frame is not None:
            self.stamp_logger.log_control_action(
                frame=frame,
                vehicle_id=vehicle_id,
                action=ControlAction.TM_IGNORE_VEHICLES,
                parameters={"ignore": ignore},
                result="success",
            )

    def get_vehicle(self, vehicle_id: int) -> carla.Vehicle:
        """車両アクターを取得"""
        if vehicle_id not in self.vehicles:
            raise ValueError(f"Vehicle {vehicle_id} not registered")
        return self.vehicles[vehicle_id]

    def get_vehicle_config(self, vehicle_id: int) -> Dict[str, Any]:
        """車両設定を取得"""
        if vehicle_id not in self.vehicle_configs:
            raise ValueError(f"Vehicle {vehicle_id} not registered")
        return self.vehicle_configs[vehicle_id].copy()

    def get_all_vehicles(self) -> List[int]:
        """登録されているすべての車両IDを取得"""
        return list(self.vehicles.keys())

    def cleanup(self) -> None:
        """クリーンアップ"""
        for vehicle in self.vehicles.values():
            if vehicle.is_alive:
                vehicle.set_autopilot(False)
        self.vehicles.clear()
        self.vehicle_configs.clear()
