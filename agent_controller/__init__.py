"""
agent_controller - CARLA Traffic Manager Wrapper Package

高レベルAPIを提供し、CARLA Traffic Managerをラップして
テストケースでよくあるシナリオを簡単に記述できるようにします。

主要機能:
- CARLAクライアント接続の自動管理（リトライ、生存確認、再接続）
- コールバックベースのシナリオ記述（world.tick()とフレーム管理が不要）
- レーンチェンジ、カットイン、タイミング突入などの高レベル振る舞い
- STAMP状態遷移ロギング
- ユーザー指示の追跡と記録
- コンテキストマネージャによる自動クリーンアップ

推奨される使い方（コールバックベース）:
    >>> from agent_controller import AgentController
    >>> with AgentController(scenario_uuid="my-scenario") as controller:
    ...     ego_id = controller.register_vehicle(vehicle)
    ...     # コールバックでシナリオを定義（フレーム管理不要！）
    ...     controller.register_callback(100, lambda: controller.lane_change(ego_id, direction="left"))
    ...     controller.run_simulation(total_frames=500)
    # 自動的にworld.tick()、ログ保存、クリーンアップが実行される
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
