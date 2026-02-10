"""
STAMP (Systems-Theoretic Accident Model and Processes) Logger

STAMP理論に基づいた状態遷移ロガー。
エージェントの制御動作と状態変化を記録します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class ControlAction(Enum):
    """制御アクション（STAMP理論のControl Actions）"""

    # 基本動作
    ACCELERATE = "accelerate"
    DECELERATE = "decelerate"
    BRAKE = "brake"
    STEER_LEFT = "steer_left"
    STEER_RIGHT = "steer_right"
    MAINTAIN_SPEED = "maintain_speed"

    # 高レベル動作
    LANE_CHANGE_LEFT = "lane_change_left"
    LANE_CHANGE_RIGHT = "lane_change_right"
    CUT_IN = "cut_in"
    OVERTAKE = "overtake"
    MERGE = "merge"
    FOLLOW = "follow"
    STOP = "stop"

    # Traffic Manager指示
    TM_AUTO_LANE_CHANGE = "tm_auto_lane_change"
    TM_FORCE_LANE_CHANGE = "tm_force_lane_change"
    TM_IGNORE_LIGHTS = "tm_ignore_lights"
    TM_IGNORE_VEHICLES = "tm_ignore_vehicles"
    TM_DISTANCE_TO_LEADING = "tm_distance_to_leading"
    TM_VEHICLE_PERCENTAGE_SPEED = "tm_vehicle_percentage_speed"


class StateType(Enum):
    """状態タイプ"""

    # 動作状態
    IDLE = "idle"
    DRIVING = "driving"
    STOPPING = "stopping"
    STOPPED = "stopped"
    TURNING = "turning"
    LANE_CHANGING = "lane_changing"
    FOLLOWING = "following"

    # 安全状態
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"
    COLLISION = "collision"

    # タスク状態
    TASK_STARTED = "task_started"
    TASK_IN_PROGRESS = "task_in_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


@dataclass
class StateTransition:
    """状態遷移レコード"""

    timestamp: float
    frame: int
    vehicle_id: int

    # 状態遷移
    from_state: StateType
    to_state: StateType

    # 制御アクション
    control_action: Optional[ControlAction] = None

    # 位置情報
    location: Optional[Dict[str, float]] = None  # {x, y, z}
    rotation: Optional[Dict[str, float]] = None  # {pitch, yaw, roll}
    velocity: Optional[Dict[str, float]] = None  # {x, y, z}

    # 追加情報
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "timestamp": self.timestamp,
            "frame": self.frame,
            "vehicle_id": self.vehicle_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "control_action": self.control_action.value if self.control_action else None,
            "location": self.location,
            "rotation": self.rotation,
            "velocity": self.velocity,
            "metadata": self.metadata,
        }


@dataclass
class ControlActionRecord:
    """制御アクション記録"""

    timestamp: float
    frame: int
    vehicle_id: int
    action: ControlAction
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None  # "success", "failed", "in_progress"

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "timestamp": self.timestamp,
            "frame": self.frame,
            "vehicle_id": self.vehicle_id,
            "action": self.action.value,
            "parameters": self.parameters,
            "result": self.result,
        }


class STAMPLogger:
    """
    STAMP理論に基づいた状態遷移ロガー

    制御アクションと状態遷移を記録し、
    システムの振る舞いを分析可能にします。
    """

    def __init__(
        self,
        scenario_uuid: str,
        output_dir: Path = Path("data/logs/stamp"),
    ):
        """
        Args:
            scenario_uuid: シナリオUUID
            output_dir: ログ出力ディレクトリ
        """
        self.scenario_uuid = scenario_uuid
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.state_transitions: List[StateTransition] = []
        self.control_actions: List[ControlActionRecord] = []
        self.vehicle_states: Dict[int, StateType] = {}  # vehicle_id -> current_state

        self.start_time = datetime.now()
        self._is_finalized = False

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
        """
        状態遷移を記録

        Args:
            frame: フレーム番号
            vehicle_id: 車両ID
            to_state: 遷移先の状態
            control_action: 状態変化を引き起こした制御アクション
            location: 位置 {x, y, z}
            rotation: 回転 {pitch, yaw, roll}
            velocity: 速度 {x, y, z}
            metadata: 追加情報
        """
        from_state = self.vehicle_states.get(vehicle_id, StateType.IDLE)

        transition = StateTransition(
            timestamp=datetime.now().timestamp(),
            frame=frame,
            vehicle_id=vehicle_id,
            from_state=from_state,
            to_state=to_state,
            control_action=control_action,
            location=location,
            rotation=rotation,
            velocity=velocity,
            metadata=metadata or {},
        )

        self.state_transitions.append(transition)
        self.vehicle_states[vehicle_id] = to_state

    def log_control_action(
        self,
        frame: int,
        vehicle_id: int,
        action: ControlAction,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
    ) -> None:
        """
        制御アクションを記録

        Args:
            frame: フレーム番号
            vehicle_id: 車両ID
            action: 制御アクション
            parameters: アクションのパラメータ
            result: 実行結果 ("success", "failed", "in_progress")
        """
        record = ControlActionRecord(
            timestamp=datetime.now().timestamp(),
            frame=frame,
            vehicle_id=vehicle_id,
            action=action,
            parameters=parameters or {},
            result=result,
        )

        self.control_actions.append(record)

    def get_vehicle_state(self, vehicle_id: int) -> StateType:
        """車両の現在の状態を取得"""
        return self.vehicle_states.get(vehicle_id, StateType.IDLE)

    def finalize(self) -> Path:
        """
        ログをファイナライズして保存

        Returns:
            保存されたログファイルのパス
        """
        if self._is_finalized:
            return self._get_log_path()

        log_data = {
            "scenario_uuid": self.scenario_uuid,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "state_transitions": [t.to_dict() for t in self.state_transitions],
            "control_actions": [a.to_dict() for a in self.control_actions],
            "summary": {
                "total_transitions": len(self.state_transitions),
                "total_actions": len(self.control_actions),
                "vehicles": list(self.vehicle_states.keys()),
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
        return self.output_dir / f"stamp_{self.scenario_uuid}_{timestamp}.json"

    def print_summary(self) -> None:
        """サマリーを出力"""
        print("\n=== STAMP Log Summary ===")
        print(f"Scenario: {self.scenario_uuid}")
        print(f"Duration: {(datetime.now() - self.start_time).total_seconds():.2f}s")
        print(f"State Transitions: {len(self.state_transitions)}")
        print(f"Control Actions: {len(self.control_actions)}")
        print(f"Vehicles: {len(self.vehicle_states)}")

        if self.vehicle_states:
            print("\nFinal Vehicle States:")
            for vehicle_id, state in self.vehicle_states.items():
                print(f"  Vehicle {vehicle_id}: {state.value}")
