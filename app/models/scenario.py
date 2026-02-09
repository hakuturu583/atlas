"""Scenario data models."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class Scenario(BaseModel):
    """CARLA scenario definition."""
    id: str
    name: str
    description: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # シナリオ定義
    carla_config: dict[str, Any] = Field(default_factory=dict)
    vehicles: list[dict[str, Any]] = Field(default_factory=list)
    pedestrians: list[dict[str, Any]] = Field(default_factory=list)
    weather: dict[str, Any] = Field(default_factory=dict)

    # 実行結果
    last_run_at: Optional[datetime] = None
    rerun_file: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)

    # Sandbox関連
    sandbox_uuid: Optional[str] = None  # Sandboxコンテナ識別UUID
    container_status: Optional[str] = None  # "running", "stopped", "not_created"
    workspace_path: Optional[str] = None  # workspace/{uuid}のパス

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ScenarioListItem(BaseModel):
    """Simplified scenario info for list views."""
    id: str
    name: str
    description: str
    updated_at: datetime
    has_results: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
