"""シナリオ階層構造のデータモデル（dataclass版）

階層構造:
  AbstractScenario (抽象シナリオ) + PEGASUS 6 Layer
    ↓ 1:N
  LogicalScenario (論理シナリオ) + パラメータ空間
    ↓ 1:N
  ParameterSet (パラメータセット)
    ↓ 1:1
  ExecutionTrace (実行トレース)

PEGASUS 6 Layer統合:
  - Layer 1: Road-level（道路レベル）
  - Layer 2: Traffic Infrastructure（交通インフラ）
  - Layer 3: Temporary Manipulation（一時的な変更）
  - Layer 4: Moving Objects（移動物体）
  - Layer 5: Environment Conditions（環境条件）
  - Layer 6: Digital Information（デジタル情報）
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pathlib import Path

# PEGASUS Layersをインポート
from .pegasus_layers import (
    PegasusScenario,
    RoadLevel,
    TrafficInfrastructure,
    TemporaryManipulation,
    MovingObject,
    EnvironmentConditions,
    DigitalInformation,
)


# ========================================
# 分布の型定義
# ========================================

@dataclass(frozen=True)
class ConstantValue:
    """固定値"""
    value: float
    type: Literal["constant"] = "constant"

    def sample(self, seed: Optional[int] = None) -> float:
        """値をサンプリング（常に固定値を返す）"""
        return self.value


@dataclass(frozen=True)
class UniformDistribution:
    """一様分布"""
    min: float
    max: float
    unit: str = ""
    type: Literal["uniform"] = "uniform"

    def sample(self, seed: Optional[int] = None) -> float:
        """一様分布からサンプリング"""
        import random
        if seed is not None:
            random.seed(seed)
        return random.uniform(self.min, self.max)


@dataclass(frozen=True)
class NormalDistribution:
    """正規分布"""
    mean: float
    std: float
    unit: str = ""
    type: Literal["normal"] = "normal"

    def sample(self, seed: Optional[int] = None) -> float:
        """正規分布からサンプリング"""
        import random
        if seed is not None:
            random.seed(seed)
        return random.gauss(self.mean, self.std)


@dataclass(frozen=True)
class ChoiceDistribution:
    """選択肢からランダム選択"""
    choices: tuple[Any, ...]  # immutableにするためtuple
    type: Literal["choice"] = "choice"

    def sample(self, seed: Optional[int] = None) -> Any:
        """選択肢からランダムにサンプリング"""
        import random
        if seed is not None:
            random.seed(seed)
        return random.choice(self.choices)

    def __init__(self, choices: List[Any]):
        # リストをタプルに変換してimmutableにする
        object.__setattr__(self, 'choices', tuple(choices))
        object.__setattr__(self, 'type', 'choice')


# 分布の型（Union型）
Distribution = Union[ConstantValue, UniformDistribution, NormalDistribution, ChoiceDistribution]


# ========================================
# パラメータ空間の定義
# ========================================

@dataclass
class ParameterDefinition:
    """単一パラメータの定義"""
    name: str
    distribution: Distribution
    description: str = ""

    def sample(self, seed: Optional[int] = None) -> float | Any:
        """パラメータ値をサンプリング"""
        return self.distribution.sample(seed)


@dataclass
class ParameterGroup:
    """パラメータのグループ（例: ego_vehicle, camera, scenario）"""
    name: str
    parameters: Dict[str, ParameterDefinition]

    def sample_all(self, seed: Optional[int] = None) -> Dict[str, float | Any]:
        """グループ内のすべてのパラメータをサンプリング"""
        import random
        if seed is not None:
            random.seed(seed)

        sampled = {}
        for param_name, param_def in self.parameters.items():
            # 各パラメータに異なるシードを与える
            param_seed = None if seed is None else (seed + hash(param_name)) % (2**32)
            sampled[param_name] = param_def.sample(param_seed)
        return sampled


@dataclass
class ParameterSpace:
    """パラメータ空間（複数のグループを含む）"""
    groups: Dict[str, ParameterGroup]

    def sample_all(self, seed: Optional[int] = None) -> Dict[str, Dict[str, float | Any]]:
        """すべてのグループのパラメータをサンプリング"""
        import random
        if seed is not None:
            random.seed(seed)

        sampled = {}
        for group_name, group in self.groups.items():
            # 各グループに異なるシードを与える
            group_seed = None if seed is None else (seed + hash(group_name)) % (2**32)
            sampled[group_name] = group.sample_all(group_seed)
        return sampled


# ========================================
# CARLA設定
# ========================================

@dataclass
class CarlaConfig:
    """CARLA実行環境の設定"""
    host: str = "localhost"
    port: int = 2000
    map: str = "Town10HD_Opt"
    vehicle_type: str = "vehicle.taxi.ford"
    synchronous_mode: bool = True
    fixed_delta_seconds: float = 0.05  # 20Hz
    timeout: float = 10.0


# ========================================
# アクターとマニューバー
# ========================================

class ActorType(str, Enum):
    """アクタータイプ"""
    VEHICLE = "vehicle"
    PEDESTRIAN = "pedestrian"
    SENSOR = "sensor"


@dataclass
class Actor:
    """シナリオ内のアクター"""
    id: str
    type: ActorType
    role: str
    is_autonomous_stack: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Maneuver:
    """アクターが実行する操作"""
    actor_id: str
    action: str
    duration: str  # "5s", "10s" など
    conditions: List[str] = field(default_factory=list)


# ========================================
# 環境設定
# ========================================

class LocationType(str, Enum):
    """ロケーションタイプ"""
    URBAN = "urban"
    HIGHWAY = "highway"
    RURAL = "rural"
    PARKING = "parking"
    INTERSECTION = "urban_intersection"


@dataclass
class Environment:
    """シナリオの環境設定"""
    location_type: LocationType
    features: List[str] = field(default_factory=list)
    weather: Optional[str] = None
    time_of_day: Optional[str] = None


# ========================================
# 抽象シナリオ
# ========================================

@dataclass
class AbstractScenario:
    """抽象シナリオ（自然言語から生成された高レベル記述）+ PEGASUS 6 Layer

    どんな場所でどんな物体が登場するかを記述。
    OpenDRIVEやCARLAマップに依存しない。
    PEGASUS 6 Layerで構造化された情報を含む。
    """
    uuid: str
    name: str
    description: str
    original_prompt: str
    environment: Environment
    actors: List[Actor]
    maneuvers: List[Maneuver]
    scenario_type: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # PEGASUS 6 Layer統合（オプション）
    pegasus_layer1_road: Optional[RoadLevel] = None
    pegasus_layer2_infrastructure: Optional[TrafficInfrastructure] = None
    pegasus_layer3_manipulation: List[TemporaryManipulation] = field(default_factory=list)
    pegasus_layer4_objects: List[MovingObject] = field(default_factory=list)
    pegasus_layer5_environment: Optional[EnvironmentConditions] = None
    pegasus_layer6_digital: Optional[DigitalInformation] = None
    pegasus_criticality_level: Optional[int] = None  # 1-5 (5が最も危険)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "uuid": self.uuid,
            "name": self.name,
            "description": self.description,
            "original_prompt": self.original_prompt,
            "environment": {
                "location_type": self.environment.location_type.value,
                "features": self.environment.features,
                "weather": self.environment.weather,
                "time_of_day": self.environment.time_of_day,
            },
            "actors": [
                {
                    "id": actor.id,
                    "type": actor.type.value,
                    "role": actor.role,
                    "is_autonomous_stack": actor.is_autonomous_stack,
                    "metadata": actor.metadata,
                }
                for actor in self.actors
            ],
            "maneuvers": [
                {
                    "actor_id": m.actor_id,
                    "action": m.action,
                    "duration": m.duration,
                    "conditions": m.conditions,
                }
                for m in self.maneuvers
            ],
            "scenario_type": self.scenario_type,
            "created_at": self.created_at.isoformat() + "Z",
            "metadata": self.metadata,
        }


# ========================================
# 論理シナリオ
# ========================================

@dataclass
class LogicalScenario:
    """論理シナリオ（パラメータ空間を定義）

    抽象シナリオの具体化に必要なパラメータの定義と分布を記述。
    1つの抽象シナリオから複数の論理シナリオを派生可能。
    """
    uuid: str
    parent_abstract_uuid: str
    name: str
    description: str
    parameter_space: ParameterSpace
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def sample_parameters(self, seed: Optional[int] = None) -> Dict[str, Dict[str, float | Any]]:
        """パラメータ空間からサンプリング"""
        return self.parameter_space.sample_all(seed)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（JSON保存用）"""
        def distribution_to_dict(dist: Distribution) -> Dict[str, Any]:
            if isinstance(dist, ConstantValue):
                return {"type": "constant", "value": dist.value}
            elif isinstance(dist, UniformDistribution):
                return {"type": "uniform", "min": dist.min, "max": dist.max, "unit": dist.unit}
            elif isinstance(dist, NormalDistribution):
                return {"type": "normal", "mean": dist.mean, "std": dist.std, "unit": dist.unit}
            elif isinstance(dist, ChoiceDistribution):
                return {"type": "choice", "choices": list(dist.choices)}
            else:
                raise ValueError(f"Unknown distribution type: {type(dist)}")

        return {
            "uuid": self.uuid,
            "parent_abstract_uuid": self.parent_abstract_uuid,
            "name": self.name,
            "description": self.description,
            "parameter_space": {
                group_name: {
                    "name": group.name,
                    "parameters": {
                        param_name: {
                            "name": param_def.name,
                            "distribution": distribution_to_dict(param_def.distribution),
                            "description": param_def.description,
                        }
                        for param_name, param_def in group.parameters.items()
                    }
                }
                for group_name, group in self.parameter_space.groups.items()
            },
            "created_at": self.created_at.isoformat() + "Z",
            "metadata": self.metadata,
        }


# ========================================
# パラメータセット
# ========================================

@dataclass
class ParameterSet:
    """サンプリングされたパラメータセット

    論理シナリオのパラメータ空間から1回サンプリングした具体値。
    1つの論理シナリオから複数のパラメータセットを生成可能。
    """
    uuid: str
    parent_logical_uuid: str
    sampled_values: Dict[str, Dict[str, float | Any]]
    carla_config: CarlaConfig
    seed: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "uuid": self.uuid,
            "parent_logical_uuid": self.parent_logical_uuid,
            "sampled_values": self.sampled_values,
            "carla_config": {
                "host": self.carla_config.host,
                "port": self.carla_config.port,
                "map": self.carla_config.map,
                "vehicle_type": self.carla_config.vehicle_type,
                "synchronous_mode": self.carla_config.synchronous_mode,
                "fixed_delta_seconds": self.carla_config.fixed_delta_seconds,
                "timeout": self.carla_config.timeout,
            },
            "seed": self.seed,
            "created_at": self.created_at.isoformat() + "Z",
            "metadata": self.metadata,
        }


# ========================================
# 実行トレース
# ========================================

class ExecutionStatus(str, Enum):
    """実行ステータス"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ExecutionTrace:
    """シナリオ実行のトレース情報

    1つのパラメータセットに対する実行結果を記録。
    """
    uuid: str
    parent_parameter_uuid: str
    parent_logical_uuid: str
    python_file: Path
    command: str
    status: ExecutionStatus
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # 出力ファイル
    rrd_file: Optional[Path] = None
    video_file: Optional[Path] = None

    # Embedding（オプション）
    embedding_file: Optional[Path] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "uuid": self.uuid,
            "parent_parameter_uuid": self.parent_parameter_uuid,
            "parent_logical_uuid": self.parent_logical_uuid,
            "python_file": str(self.python_file) if self.python_file else None,
            "command": self.command,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "started_at": self.started_at.isoformat() + "Z" if self.started_at else None,
            "completed_at": self.completed_at.isoformat() + "Z" if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "rrd_file": str(self.rrd_file) if self.rrd_file else None,
            "video_file": str(self.video_file) if self.video_file else None,
            "embedding_file": str(self.embedding_file) if self.embedding_file else None,
            "metadata": self.metadata,
        }


# ========================================
# 完全な階層構造
# ========================================

@dataclass
class ScenarioHierarchy:
    """シナリオの完全な階層構造

    Abstract -> Logical -> Parameters -> Execution の関係を保持。
    """
    abstract: AbstractScenario
    logical: LogicalScenario
    parameter_set: ParameterSet
    execution: Optional[ExecutionTrace] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "abstract": self.abstract.to_dict(),
            "logical": self.logical.to_dict(),
            "parameter_set": self.parameter_set.to_dict(),
            "execution": self.execution.to_dict() if self.execution else None,
        }
