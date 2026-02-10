"""
agent_controller - CARLA Traffic Manager Wrapper Package

高レベルAPIを提供し、CARLA Traffic Managerをラップして
テストケースでよくあるシナリオを簡単に記述できるようにします。

主要機能:
- CARLAクライアント接続の自動管理（リトライ、生存確認、再接続）
- 車両の自動生存管理（スポーン追跡、自動破棄）
- トリガー関数ベースのシナリオ記述（world.tick()とフレーム管理が不要）
- 豊富なトリガー条件（タイムステップ、位置、距離、速度など）
- レーンチェンジ、カットイン、タイミング突入などの高レベル振る舞い
- STAMP状態遷移ロギング
- ユーザー指示の追跡と記録
- 安全性メトリクス（TTC、急ブレーキ、急加速など）の自動計算
- 意味論的カバレッジ計算
- コンテキストマネージャによる自動クリーンアップ

推奨される使い方（トリガー関数ベース）:
    >>> from agent_controller import AgentController
    >>> from opendrive_utils import LaneCoord
    >>> with AgentController(scenario_uuid="my-scenario") as controller:
    ...     # 車両をスポーン（自動登録）
    ...     lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
    ...     vehicle, ego_id = controller.spawn_vehicle_from_lane(
    ...         "vehicle.tesla.model3", lane_coord, speed_percentage=80.0
    ...     )
    ...     # トリガー関数でシナリオを定義（フレーム管理不要！）
    ...     controller.register_callback(
    ...         controller.when_timestep_equals(100),
    ...         lambda: controller.lane_change(ego_id, direction="left")
    ...     )
    ...     controller.run_simulation(total_frames=500)
    # 自動的にworld.tick()、車両破棄、ログ保存、クリーンアップが実行される
"""

# メインAPI（推奨）
from .controller import AgentController
from .vehicle_config import (
    VehicleConfig,
    AGGRESSIVE_DRIVER,
    CAUTIOUS_DRIVER,
    RECKLESS_DRIVER,
    NORMAL_DRIVER,
)
from .metrics import SafetyMetrics, MetricsConfig, MetricsEvent

# 低レベルAPI（上級ユーザー向け）
from .traffic_manager_wrapper import TrafficManagerWrapper
from .behaviors import (
    LaneChangeBehavior,
    CutInBehavior,
    TimedApproachBehavior,
    FollowBehavior,
    StopBehavior,
    BehaviorResult,
)
from .stamp_logger import STAMPLogger, ControlAction, StateTransition, StateType
from .command_tracker import CommandTracker, CommandStatus

__all__ = [
    # メインAPI
    "AgentController",
    "VehicleConfig",
    # プリセット
    "AGGRESSIVE_DRIVER",
    "CAUTIOUS_DRIVER",
    "RECKLESS_DRIVER",
    "NORMAL_DRIVER",
    # メトリクス
    "SafetyMetrics",
    "MetricsConfig",
    "MetricsEvent",
    # 低レベルAPI
    "TrafficManagerWrapper",
    "LaneChangeBehavior",
    "CutInBehavior",
    "TimedApproachBehavior",
    "FollowBehavior",
    "StopBehavior",
    "BehaviorResult",
    "STAMPLogger",
    "ControlAction",
    "StateTransition",
    "StateType",
    "CommandTracker",
    "CommandStatus",
]

__version__ = "0.1.0"
