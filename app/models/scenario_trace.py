"""シナリオトレースのデータモデル

抽象シナリオ → 論理シナリオ → 具体シナリオの階層構造を表現し、
実装・ビルド・実行の履歴を記録するためのPydanticモデル。
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class Actor(BaseModel):
    """シナリオ内のアクター（車両、歩行者など）"""
    id: str = Field(description="アクターの一意なID")
    role: str = Field(description="アクターの役割（例: '前方車両', '自動運転スタック予定'）")
    type: str = Field(description="アクタータイプ（'vehicle' または 'pedestrian'）")
    is_autonomous_stack: bool = Field(
        default=False,
        description="将来自動運転スタックを統合する予定のNPCかどうか"
    )


class Maneuver(BaseModel):
    """アクターが実行する操作・動作"""
    actor: str = Field(description="操作を実行するアクターのID")
    action: str = Field(description="動作の説明（例: '加速', '合流', '一定速度で走行'）")
    duration: str = Field(description="動作の継続時間（例: '5s', '10s'）")
    conditions: Optional[list[str]] = Field(
        default=None,
        description="動作の条件（例: ['距離を20m維持']）"
    )


class AbstractScenario(BaseModel):
    """抽象シナリオ（自然言語から生成された高レベル記述）"""
    description: str = Field(description="シナリオの概要")
    actors: list[Actor] = Field(description="シナリオに登場するアクター")
    maneuvers: list[Maneuver] = Field(description="アクターが実行する操作")


class LogicalScenario(BaseModel):
    """論理シナリオ（OpenDRIVE非依存の中間表現）"""
    map_requirements: dict[str, Any] = Field(
        description="地図の要件（道路タイプ、レーン数など）"
    )
    initial_conditions: dict[str, Any] = Field(
        description="初期状態（symbolic locationと速度）"
    )
    events: list[dict[str, Any]] = Field(
        description="イベント列（時刻とアクション）"
    )


class ConcreteScenario(BaseModel):
    """具体シナリオ（CARLAの具体的なマップとパラメータ）"""
    carla_map: str = Field(description="CARLAマップ名（例: 'Town04'）")
    spawn_points: dict[str, Any] = Field(
        description="各アクターのスポーン位置（x, y, z, yaw）"
    )
    camera_config: dict[str, Any] = Field(
        description="スペクターカメラの設定（offset_x, offset_y, offset_z）"
    )
    duration_steps: int = Field(
        default=200,
        description="シナリオの継続ステップ数（20Hz想定）"
    )


class BuildError(BaseModel):
    """ビルドエラーの記録"""
    attempt: int = Field(description="試行回数")
    error: str = Field(description="エラーメッセージ")
    fix: str = Field(description="適用した修正内容")


class ImplementationInfo(BaseModel):
    """実装・ビルド・実行の情報"""
    cpp_file: str = Field(description="C++実装ファイルのパス")
    build_attempts: int = Field(description="ビルド試行回数")
    build_errors: list[BuildError] = Field(
        default_factory=list,
        description="ビルドエラーの履歴"
    )
    final_status: str = Field(description="最終ステータス（'success' または 'failure'）")


class ScenarioTrace(BaseModel):
    """シナリオの完全なトレース情報

    抽象シナリオから実装・実行までの全履歴を記録する。
    """
    id: str = Field(description="シナリオUUID")
    name: str = Field(description="シナリオ名")
    description: str = Field(description="シナリオの概要")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="作成日時"
    )

    trace: dict = Field(
        default_factory=dict,
        description="トレース情報（original_prompt, abstract_scenario, logical_scenario, concrete_scenario, implementation）"
    )

    # 実行結果
    sandbox_uuid: Optional[str] = Field(
        default=None,
        description="Sandboxで実行されたUUID"
    )
    rerun_file: Optional[str] = Field(
        default=None,
        description=".rrdファイルのパス"
    )
    video_file: Optional[str] = Field(
        default=None,
        description=".mp4ファイルのパス"
    )
    config_file: Optional[str] = Field(
        default=None,
        description="JSONパラメータファイルのパス"
    )
