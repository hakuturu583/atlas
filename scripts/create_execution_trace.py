#!/usr/bin/env python3
"""実行トレースを作成"""
from scenario_manager import ScenarioManager

manager = ScenarioManager()

# 実行トレースを作成
trace_file = manager.create_execution_trace(
    logical_uuid="95a77b84-97d4-4d7e-b57b-2c246906d525",
    parameter_uuid="04f81f6e-7f64-436f-8fa6-e96df001fe5d",
    python_file="scenarios/95a77b84-97d4-4d7e-b57b-2c246906d525.py",
    command="uv run python scenarios/95a77b84-97d4-4d7e-b57b-2c246906d525.py --params data/scenarios/params_04f81f6e-7f64-436f-8fa6-e96df001fe5d.json",
    exit_code=0,
    status="success"
)

print(f"\n✓ 実行トレースファイル: {trace_file}")
