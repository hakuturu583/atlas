"""シナリオ階層構造を構築するためのビルダー

dataclassベースのシナリオモデルを簡単に構築するためのヘルパー関数とビルダーパターン。
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .scenario_hierarchy import (
    AbstractScenario,
    Actor,
    ActorType,
    CarlaConfig,
    ChoiceDistribution,
    ConstantValue,
    Environment,
    ExecutionTrace,
    ExecutionStatus,
    LogicalScenario,
    LocationType,
    Maneuver,
    NormalDistribution,
    ParameterDefinition,
    ParameterGroup,
    ParameterSet,
    ParameterSpace,
    UniformDistribution,
)


# ========================================
# ビルダークラス
# ========================================

class AbstractScenarioBuilder:
    """抽象シナリオのビルダー"""

    def __init__(self, name: str, description: str, original_prompt: str):
        self.uuid = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.original_prompt = original_prompt
        self.actors: List[Actor] = []
        self.maneuvers: List[Maneuver] = []
        self.environment: Optional[Environment] = None
        self.scenario_type: str = "generic"
        self.metadata: Dict[str, Any] = {}

    def with_environment(
        self,
        location_type: LocationType | str,
        features: Optional[List[str]] = None,
        weather: Optional[str] = None,
        time_of_day: Optional[str] = None
    ) -> "AbstractScenarioBuilder":
        """環境設定を追加"""
        if isinstance(location_type, str):
            location_type = LocationType(location_type)
        self.environment = Environment(
            location_type=location_type,
            features=features or [],
            weather=weather,
            time_of_day=time_of_day
        )
        return self

    def add_actor(
        self,
        actor_id: str,
        actor_type: ActorType | str,
        role: str,
        is_autonomous_stack: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "AbstractScenarioBuilder":
        """アクターを追加"""
        if isinstance(actor_type, str):
            actor_type = ActorType(actor_type)
        self.actors.append(Actor(
            id=actor_id,
            type=actor_type,
            role=role,
            is_autonomous_stack=is_autonomous_stack,
            metadata=metadata or {}
        ))
        return self

    def add_maneuver(
        self,
        actor_id: str,
        action: str,
        duration: str,
        conditions: Optional[List[str]] = None
    ) -> "AbstractScenarioBuilder":
        """マニューバーを追加"""
        self.maneuvers.append(Maneuver(
            actor_id=actor_id,
            action=action,
            duration=duration,
            conditions=conditions or []
        ))
        return self

    def with_scenario_type(self, scenario_type: str) -> "AbstractScenarioBuilder":
        """シナリオタイプを設定"""
        self.scenario_type = scenario_type
        return self

    def with_metadata(self, **kwargs) -> "AbstractScenarioBuilder":
        """メタデータを追加"""
        self.metadata.update(kwargs)
        return self

    def build(self) -> AbstractScenario:
        """抽象シナリオを構築"""
        if self.environment is None:
            raise ValueError("Environment must be set")
        if not self.actors:
            raise ValueError("At least one actor must be added")

        return AbstractScenario(
            uuid=self.uuid,
            name=self.name,
            description=self.description,
            original_prompt=self.original_prompt,
            environment=self.environment,
            actors=self.actors,
            maneuvers=self.maneuvers,
            scenario_type=self.scenario_type,
            metadata=self.metadata
        )


class LogicalScenarioBuilder:
    """論理シナリオのビルダー"""

    def __init__(self, parent_abstract_uuid: str, name: str, description: str):
        self.uuid = str(uuid.uuid4())
        self.parent_abstract_uuid = parent_abstract_uuid
        self.name = name
        self.description = description
        self.groups: Dict[str, ParameterGroup] = {}
        self.metadata: Dict[str, Any] = {}

    def add_parameter_group(
        self,
        group_name: str,
        parameters: Dict[str, ParameterDefinition]
    ) -> "LogicalScenarioBuilder":
        """パラメータグループを追加"""
        self.groups[group_name] = ParameterGroup(
            name=group_name,
            parameters=parameters
        )
        return self

    def with_metadata(self, **kwargs) -> "LogicalScenarioBuilder":
        """メタデータを追加"""
        self.metadata.update(kwargs)
        return self

    def build(self) -> LogicalScenario:
        """論理シナリオを構築"""
        if not self.groups:
            raise ValueError("At least one parameter group must be added")

        return LogicalScenario(
            uuid=self.uuid,
            parent_abstract_uuid=self.parent_abstract_uuid,
            name=self.name,
            description=self.description,
            parameter_space=ParameterSpace(groups=self.groups),
            metadata=self.metadata
        )


# ========================================
# ヘルパー関数
# ========================================

def create_uniform_param(
    name: str,
    min_val: float,
    max_val: float,
    unit: str = "",
    description: str = ""
) -> ParameterDefinition:
    """一様分布パラメータを作成"""
    return ParameterDefinition(
        name=name,
        distribution=UniformDistribution(min=min_val, max=max_val, unit=unit),
        description=description
    )


def create_normal_param(
    name: str,
    mean: float,
    std: float,
    unit: str = "",
    description: str = ""
) -> ParameterDefinition:
    """正規分布パラメータを作成"""
    return ParameterDefinition(
        name=name,
        distribution=NormalDistribution(mean=mean, std=std, unit=unit),
        description=description
    )


def create_constant_param(
    name: str,
    value: float,
    description: str = ""
) -> ParameterDefinition:
    """固定値パラメータを作成"""
    return ParameterDefinition(
        name=name,
        distribution=ConstantValue(value=value),
        description=description
    )


def create_choice_param(
    name: str,
    choices: List[Any],
    description: str = ""
) -> ParameterDefinition:
    """選択肢パラメータを作成"""
    return ParameterDefinition(
        name=name,
        distribution=ChoiceDistribution(choices),
        description=description
    )


def sample_parameter_set(
    logical_scenario: LogicalScenario,
    carla_config: Optional[CarlaConfig] = None,
    seed: Optional[int] = None
) -> ParameterSet:
    """論理シナリオからパラメータセットをサンプリング"""
    sampled_values = logical_scenario.sample_parameters(seed)

    return ParameterSet(
        uuid=str(uuid.uuid4()),
        parent_logical_uuid=logical_scenario.uuid,
        sampled_values=sampled_values,
        carla_config=carla_config or CarlaConfig(),
        seed=seed
    )


# ========================================
# 使用例（ドキュメント用）
# ========================================

def example_traffic_light_scenario():
    """交差点信号機シナリオの構築例"""

    # 1. 抽象シナリオを構築
    abstract = (
        AbstractScenarioBuilder(
            name="交差点信号機シナリオ",
            description="市街地の交差点で信号機に従って停止・発進する",
            original_prompt="信号機が赤から青に変わったら車両が発進するシナリオ"
        )
        .with_environment(
            location_type=LocationType.INTERSECTION,
            features=["traffic_light", "road", "buildings"]
        )
        .add_actor(
            actor_id="ego_vehicle",
            actor_type=ActorType.VEHICLE,
            role="自動運転車両",
            is_autonomous_stack=True
        )
        .with_scenario_type("traffic_light_compliance")
        .build()
    )

    # 2. 論理シナリオを構築
    logical = (
        LogicalScenarioBuilder(
            parent_abstract_uuid=abstract.uuid,
            name="交差点信号機シナリオ",
            description="パラメータ空間の定義"
        )
        .add_parameter_group(
            "ego_vehicle",
            {
                "initial_speed": create_uniform_param(
                    "initial_speed",
                    min_val=20.0,
                    max_val=40.0,
                    unit="km/h",
                    description="初期速度"
                ),
                "distance_to_light": create_uniform_param(
                    "distance_to_light",
                    min_val=30.0,
                    max_val=70.0,
                    unit="m",
                    description="信号機までの距離"
                )
            }
        )
        .add_parameter_group(
            "traffic_light",
            {
                "red_duration": create_uniform_param(
                    "red_duration",
                    min_val=3.0,
                    max_val=7.0,
                    unit="s",
                    description="赤信号の継続時間"
                )
            }
        )
        .add_parameter_group(
            "camera",
            {
                "offset_x": create_constant_param("offset_x", -6.0),
                "offset_z": create_constant_param("offset_z", 3.0),
                "pitch": create_constant_param("pitch", -20.0)
            }
        )
        .build()
    )

    # 3. パラメータセットをサンプリング
    param_set = sample_parameter_set(
        logical,
        carla_config=CarlaConfig(map="Town10HD_Opt"),
        seed=42
    )

    print(f"Abstract UUID: {abstract.uuid}")
    print(f"Logical UUID: {logical.uuid}")
    print(f"Parameter UUID: {param_set.uuid}")
    print(f"Sampled values: {param_set.sampled_values}")

    return abstract, logical, param_set


if __name__ == "__main__":
    # 使用例を実行
    example_traffic_light_scenario()
