"""Scenario management service."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from app.models.scenario import Scenario, ScenarioListItem


class ScenarioManager:
    """Manages CARLA scenarios."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/scenarios")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._scenarios: dict[str, Scenario] = {}
        self._load_scenarios()

    def _load_scenarios(self):
        """Load all scenarios from disk."""
        # 新しいシナリオ形式（logical_*, abstract_*）はスキップ
        # 古い形式のシナリオファイルのみを読み込む
        for scenario_file in self.data_dir.glob("*.json"):
            # 新しい形式のファイルをスキップ
            if any(pattern in scenario_file.name for pattern in [
                "logical_", "abstract_", "_parameters", "execution_"
            ]):
                continue

            try:
                with open(scenario_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    scenario = Scenario(**data)
                    self._scenarios[scenario.id] = scenario
            except Exception as e:
                # 読み込みエラーは警告のみ（新形式のファイルがある場合）
                pass

    def _save_scenario(self, scenario: Scenario):
        """Save a scenario to disk."""
        scenario_file = self.data_dir / f"{scenario.id}.json"
        with open(scenario_file, "w", encoding="utf-8") as f:
            json.dump(scenario.model_dump(), f, indent=2, default=str)

    def list_scenarios(self) -> list[ScenarioListItem]:
        """List all scenarios."""
        return [
            ScenarioListItem(
                id=s.id,
                name=s.name,
                description=s.description,
                updated_at=s.updated_at,
                has_results=s.rerun_file is not None
            )
            for s in self._scenarios.values()
        ]

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)

    def create_scenario(self, scenario: Scenario) -> Scenario:
        """Create a new scenario."""
        scenario.created_at = datetime.now()
        scenario.updated_at = datetime.now()
        self._scenarios[scenario.id] = scenario
        self._save_scenario(scenario)
        return scenario

    def update_scenario(self, scenario_id: str, **updates) -> Optional[Scenario]:
        """Update a scenario."""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return None

        for key, value in updates.items():
            if hasattr(scenario, key):
                setattr(scenario, key, value)

        scenario.updated_at = datetime.now()
        self._save_scenario(scenario)
        return scenario

    def delete_scenario(self, scenario_id: str) -> bool:
        """Delete a scenario."""
        if scenario_id not in self._scenarios:
            return False

        scenario_file = self.data_dir / f"{scenario_id}.json"
        if scenario_file.exists():
            scenario_file.unlink()

        del self._scenarios[scenario_id]
        return True


# グローバルインスタンス
scenario_manager = ScenarioManager()
