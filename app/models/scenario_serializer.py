"""シナリオ階層構造のシリアライザ/デシリアライザ

dataclassベースのシナリオモデルとJSON形式の相互変換を提供。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .scenario_hierarchy import (
    AbstractScenario,
    Actor,
    ActorType,
    CarlaConfig,
    ChoiceDistribution,
    ConstantValue,
    Distribution,
    Environment,
    ExecutionStatus,
    ExecutionTrace,
    LocationType,
    LogicalScenario,
    Maneuver,
    NormalDistribution,
    ParameterDefinition,
    ParameterGroup,
    ParameterSet,
    ParameterSpace,
    ScenarioHierarchy,
    UniformDistribution,
)


# ========================================
# Distribution シリアライズ/デシリアライズ
# ========================================

def serialize_distribution(dist: Distribution) -> Dict[str, Any]:
    """分布を辞書形式に変換"""
    if isinstance(dist, ConstantValue):
        return {"type": "constant", "value": dist.value}
    elif isinstance(dist, UniformDistribution):
        return {
            "type": "uniform",
            "min": dist.min,
            "max": dist.max,
            "unit": dist.unit
        }
    elif isinstance(dist, NormalDistribution):
        return {
            "type": "normal",
            "mean": dist.mean,
            "std": dist.std,
            "unit": dist.unit
        }
    elif isinstance(dist, ChoiceDistribution):
        return {"type": "choice", "choices": list(dist.choices)}
    else:
        raise ValueError(f"Unknown distribution type: {type(dist)}")


def deserialize_distribution(data: Dict[str, Any]) -> Distribution:
    """辞書形式から分布を復元"""
    dist_type = data["type"]

    if dist_type == "constant":
        return ConstantValue(value=data["value"])
    elif dist_type == "uniform":
        return UniformDistribution(
            min=data["min"],
            max=data["max"],
            unit=data.get("unit", "")
        )
    elif dist_type == "normal":
        return NormalDistribution(
            mean=data["mean"],
            std=data["std"],
            unit=data.get("unit", "")
        )
    elif dist_type == "choice":
        return ChoiceDistribution(choices=data["choices"])
    else:
        raise ValueError(f"Unknown distribution type: {dist_type}")


# ========================================
# AbstractScenario シリアライズ/デシリアライズ
# ========================================

def serialize_abstract_scenario(scenario: AbstractScenario) -> Dict[str, Any]:
    """抽象シナリオをJSON形式に変換"""
    return scenario.to_dict()


def deserialize_abstract_scenario(data: Dict[str, Any]) -> AbstractScenario:
    """JSON形式から抽象シナリオを復元"""
    return AbstractScenario(
        uuid=data["uuid"],
        name=data["name"],
        description=data["description"],
        original_prompt=data["original_prompt"],
        environment=Environment(
            location_type=LocationType(data["environment"]["location_type"]),
            features=data["environment"].get("features", []),
            weather=data["environment"].get("weather"),
            time_of_day=data["environment"].get("time_of_day")
        ),
        actors=[
            Actor(
                id=actor["id"],
                type=ActorType(actor["type"]),
                role=actor["role"],
                is_autonomous_stack=actor.get("is_autonomous_stack", False),
                metadata=actor.get("metadata", {})
            )
            for actor in data["actors"]
        ],
        maneuvers=[
            Maneuver(
                actor_id=m["actor_id"],
                action=m["action"],
                duration=m["duration"],
                conditions=m.get("conditions", [])
            )
            for m in data.get("maneuvers", [])
        ],
        scenario_type=data["scenario_type"],
        created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        metadata=data.get("metadata", {})
    )


# ========================================
# LogicalScenario シリアライズ/デシリアライズ
# ========================================

def serialize_logical_scenario(scenario: LogicalScenario) -> Dict[str, Any]:
    """論理シナリオをJSON形式に変換"""
    return scenario.to_dict()


def deserialize_logical_scenario(data: Dict[str, Any]) -> LogicalScenario:
    """JSON形式から論理シナリオを復元"""
    groups = {}
    for group_name, group_data in data["parameter_space"].items():
        parameters = {}
        for param_name, param_data in group_data["parameters"].items():
            parameters[param_name] = ParameterDefinition(
                name=param_data["name"],
                distribution=deserialize_distribution(param_data["distribution"]),
                description=param_data.get("description", "")
            )

        groups[group_name] = ParameterGroup(
            name=group_data["name"],
            parameters=parameters
        )

    return LogicalScenario(
        uuid=data["uuid"],
        parent_abstract_uuid=data["parent_abstract_uuid"],
        name=data["name"],
        description=data["description"],
        parameter_space=ParameterSpace(groups=groups),
        created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        metadata=data.get("metadata", {})
    )


# ========================================
# ParameterSet シリアライズ/デシリアライズ
# ========================================

def serialize_parameter_set(param_set: ParameterSet) -> Dict[str, Any]:
    """パラメータセットをJSON形式に変換"""
    return param_set.to_dict()


def deserialize_parameter_set(data: Dict[str, Any]) -> ParameterSet:
    """JSON形式からパラメータセットを復元"""
    return ParameterSet(
        uuid=data["uuid"],
        parent_logical_uuid=data["parent_logical_uuid"],
        sampled_values=data["sampled_values"],
        carla_config=CarlaConfig(**data["carla_config"]),
        seed=data.get("seed"),
        created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        metadata=data.get("metadata", {})
    )


# ========================================
# ExecutionTrace シリアライズ/デシリアライズ
# ========================================

def serialize_execution_trace(trace: ExecutionTrace) -> Dict[str, Any]:
    """実行トレースをJSON形式に変換"""
    return trace.to_dict()


def deserialize_execution_trace(data: Dict[str, Any]) -> ExecutionTrace:
    """JSON形式から実行トレースを復元"""
    return ExecutionTrace(
        uuid=data["uuid"],
        parent_parameter_uuid=data["parent_parameter_uuid"],
        parent_logical_uuid=data["parent_logical_uuid"],
        python_file=Path(data["python_file"]) if data.get("python_file") else None,
        command=data["command"],
        status=ExecutionStatus(data["status"]),
        exit_code=data.get("exit_code"),
        stdout=data.get("stdout"),
        stderr=data.get("stderr"),
        started_at=datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
        if data.get("started_at") else None,
        completed_at=datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00"))
        if data.get("completed_at") else None,
        duration_seconds=data.get("duration_seconds"),
        rrd_file=Path(data["rrd_file"]) if data.get("rrd_file") else None,
        video_file=Path(data["video_file"]) if data.get("video_file") else None,
        embedding_file=Path(data["embedding_file"]) if data.get("embedding_file") else None,
        metadata=data.get("metadata", {})
    )


# ========================================
# ファイルI/O
# ========================================

def save_abstract_scenario(scenario: AbstractScenario, file_path: Path) -> None:
    """抽象シナリオをJSONファイルに保存"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(serialize_abstract_scenario(scenario), f, indent=2, ensure_ascii=False)


def load_abstract_scenario(file_path: Path) -> AbstractScenario:
    """JSONファイルから抽象シナリオを読み込み"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return deserialize_abstract_scenario(data)


def save_logical_scenario(scenario: LogicalScenario, file_path: Path) -> None:
    """論理シナリオをJSONファイルに保存"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(serialize_logical_scenario(scenario), f, indent=2, ensure_ascii=False)


def load_logical_scenario(file_path: Path) -> LogicalScenario:
    """JSONファイルから論理シナリオを読み込み"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return deserialize_logical_scenario(data)


def save_parameter_set(param_set: ParameterSet, file_path: Path) -> None:
    """パラメータセットをJSONファイルに保存"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(serialize_parameter_set(param_set), f, indent=2, ensure_ascii=False)


def load_parameter_set(file_path: Path) -> ParameterSet:
    """JSONファイルからパラメータセットを読み込み"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return deserialize_parameter_set(data)


def save_execution_trace(trace: ExecutionTrace, file_path: Path) -> None:
    """実行トレースをJSONファイルに保存"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(serialize_execution_trace(trace), f, indent=2, ensure_ascii=False)


def load_execution_trace(file_path: Path) -> ExecutionTrace:
    """JSONファイルから実行トレースを読み込み"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return deserialize_execution_trace(data)


def save_scenario_hierarchy(hierarchy: ScenarioHierarchy, base_dir: Path) -> None:
    """シナリオ階層構造を複数のファイルに保存"""
    base_dir.mkdir(parents=True, exist_ok=True)

    # 抽象シナリオ
    save_abstract_scenario(
        hierarchy.abstract,
        base_dir / f"abstract_{hierarchy.abstract.uuid}.json"
    )

    # 論理シナリオ
    save_logical_scenario(
        hierarchy.logical,
        base_dir / f"logical_{hierarchy.logical.uuid}.json"
    )

    # パラメータセット
    save_parameter_set(
        hierarchy.parameter_set,
        base_dir / f"params_{hierarchy.parameter_set.uuid}.json"
    )

    # 実行トレース（存在する場合）
    if hierarchy.execution:
        save_execution_trace(
            hierarchy.execution,
            base_dir / f"execution_{hierarchy.execution.uuid}.json"
        )
