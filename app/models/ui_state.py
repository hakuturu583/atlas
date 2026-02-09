"""UI state management models."""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class ViewType(str, Enum):
    """Available view types in the UI."""
    HOME = "home"
    SCENARIO_LIST = "scenario_list"
    SCENARIO_EDITOR = "scenario_editor"
    SCENARIO_ANALYSIS = "scenario_analysis"
    RERUN_VIEWER = "rerun_viewer"
    FIFTYONE_VIEWER = "fiftyone_viewer"
    SIMULATION = "simulation"


class UIState(BaseModel):
    """Current UI state."""
    current_view: ViewType = Field(default=ViewType.HOME)
    selected_scenario_id: Optional[str] = None
    rerun_file_path: Optional[str] = None
    sidebar_expanded: bool = True
    terminal_visible: bool = True

    class Config:
        use_enum_values = True


class ViewTransition(BaseModel):
    """Request to transition to a different view."""
    target_view: ViewType
    scenario_id: Optional[str] = None
    rerun_file: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)
