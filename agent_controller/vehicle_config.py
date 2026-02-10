"""
Vehicle Configuration

車両のTraffic Manager設定をまとめたデータクラスです。
"""

from dataclasses import dataclass, field


@dataclass
class VehicleConfig:
    """
    車両のTraffic Manager設定

    Attributes:
        auto_lane_change: 自動レーンチェンジを有効化
        distance_to_leading: 前方車両との距離（m）
        speed_percentage: 制限速度に対する速度パーセンテージ
        ignore_lights: 信号無視
        ignore_vehicles: 他車両無視
        ignore_signs: 標識無視

    使用例:
        >>> config = VehicleConfig(
        ...     auto_lane_change=False,
        ...     distance_to_leading=5.0,
        ...     speed_percentage=80.0,
        ... )
        >>> vehicle, vehicle_id = controller.spawn_vehicle_from_lane(
        ...     "vehicle.tesla.model3",
        ...     lane_coord,
        ...     config=config
        ... )
    """

    auto_lane_change: bool = True
    distance_to_leading: float = 2.5
    speed_percentage: float = 100.0
    ignore_lights: bool = False
    ignore_vehicles: bool = False
    ignore_signs: bool = False

    def to_dict(self) -> dict:
        """
        辞書形式に変換

        Returns:
            設定の辞書
        """
        return {
            "auto_lane_change": self.auto_lane_change,
            "distance_to_leading": self.distance_to_leading,
            "speed_percentage": self.speed_percentage,
            "ignore_lights": self.ignore_lights,
            "ignore_vehicles": self.ignore_vehicles,
            "ignore_signs": self.ignore_signs,
        }


# プリセット設定

AGGRESSIVE_DRIVER = VehicleConfig(
    auto_lane_change=True,
    distance_to_leading=1.5,
    speed_percentage=120.0,
    ignore_lights=False,
    ignore_vehicles=False,
    ignore_signs=False,
)
"""アグレッシブなドライバー（車間距離が短く、速度が速い）"""

CAUTIOUS_DRIVER = VehicleConfig(
    auto_lane_change=False,
    distance_to_leading=5.0,
    speed_percentage=80.0,
    ignore_lights=False,
    ignore_vehicles=False,
    ignore_signs=False,
)
"""慎重なドライバー（車間距離が長く、速度が遅い）"""

RECKLESS_DRIVER = VehicleConfig(
    auto_lane_change=True,
    distance_to_leading=1.0,
    speed_percentage=150.0,
    ignore_lights=True,
    ignore_vehicles=True,
    ignore_signs=True,
)
"""無謀なドライバー（すべての交通ルールを無視）"""

NORMAL_DRIVER = VehicleConfig(
    auto_lane_change=True,
    distance_to_leading=2.5,
    speed_percentage=100.0,
    ignore_lights=False,
    ignore_vehicles=False,
    ignore_signs=False,
)
"""通常のドライバー（デフォルト設定）"""
