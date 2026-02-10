"""
agent_controller - CARLA Traffic Manager Wrapper Package

高レベルAPIを提供し、CARLA Traffic Managerをラップして
テストケースでよくあるシナリオを簡単に記述できるようにします。

主要機能:
- CARLAクライアント接続の自動管理（リトライ、生存確認、再接続）
- レーンチェンジ、カットイン、タイミング突入などの高レベル振る舞い
- STAMP状態遷移ロギング
- ユーザー指示の追跡と記録
- コンテキストマネージャによる自動クリーンアップ

推奨される使い方:
    >>> from agent_controller import AgentController
    >>> with AgentController(scenario_uuid="my-scenario") as controller:
    ...     world = controller.world
    ...     vehicle_id = controller.register_vehicle(vehicle)
    ...     controller.lane_change(vehicle_id, frame=100, direction="left")
    # 自動的にログ保存、クリーンアップが実行される
"""

# メインAPI（推奨）
from .controller import AgentController

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
