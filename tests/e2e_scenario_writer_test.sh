#!/bin/bash
# E2Eテスト: シナリオライターの完全なワークフロー

set -e  # エラー時に終了

echo "=== Scenario Writer E2E Test ==="
echo ""

# テスト用UUID
TEST_UUID="test-scenario-$(date +%s)"

echo "Test UUID: $TEST_UUID"
echo ""

# 1. 抽象シナリオ生成テスト
echo "Step 1: Testing abstract scenario generation..."
python3 -c "
from app.services.scenario_writer import scenario_writer

abstract = scenario_writer.generate_abstract_scenario('高速道路で前方車両を追従する')
print(f'✓ Abstract scenario generated')
print(f'  Actors: {len(abstract.actors)}')
print(f'  Maneuvers: {len(abstract.maneuvers)}')
"

# 2. 論理シナリオ生成テスト
echo ""
echo "Step 2: Testing logical scenario generation..."
python3 -c "
from app.services.scenario_writer import scenario_writer
from app.models.scenario_trace import AbstractScenario, Actor, Maneuver

abstract = AbstractScenario(
    description='テストシナリオ',
    actors=[
        Actor(id='ego', role='自動運転', type='vehicle', is_autonomous_stack=True),
        Actor(id='lead', role='前方車両', type='vehicle', is_autonomous_stack=False)
    ],
    maneuvers=[
        Maneuver(actor='ego', action='追従', duration='10s')
    ]
)

logical = scenario_writer.generate_logical_scenario(abstract)
print(f'✓ Logical scenario generated')
print(f'  Map requirements: {logical.map_requirements}')
print(f'  Events: {len(logical.events)}')
"

# 3. 具体シナリオ生成テスト
echo ""
echo "Step 3: Testing concrete scenario generation..."
python3 -c "
from app.services.scenario_writer import scenario_writer
from app.models.scenario_trace import LogicalScenario

logical = LogicalScenario(
    map_requirements={'road_type': 'highway', 'lanes': 3},
    initial_conditions={'ego': {'location': 'lane_2'}},
    events=[{'time': 0.0, 'type': 'start'}]
)

concrete, json_str = scenario_writer.generate_concrete_scenario(logical, 'Town04')
print(f'✓ Concrete scenario generated')
print(f'  Map: {concrete.carla_map}')
print(f'  Spawn points: {len(concrete.spawn_points)}')
print(f'  JSON config: {len(json_str)} bytes')
"

# 4. トレース保存テスト
echo ""
echo "Step 4: Testing trace save/load..."
python3 -c "
from app.services.scenario_writer import scenario_writer
from app.models.scenario_trace import ScenarioTrace

trace = ScenarioTrace(
    id='$TEST_UUID',
    name='E2Eテストシナリオ',
    description='E2Eテスト用のシナリオ',
    trace={'test': True}
)

file_path = scenario_writer.save_trace(trace)
print(f'✓ Trace saved to: {file_path}')

loaded = scenario_writer.load_trace('$TEST_UUID')
assert loaded.id == '$TEST_UUID'
print(f'✓ Trace loaded successfully')
"

# 5. 保存されたファイルの確認
echo ""
echo "Step 5: Verifying saved files..."
if [ -f "data/scenarios/${TEST_UUID}.json" ]; then
    FILE_SIZE=$(stat -f%z "data/scenarios/${TEST_UUID}.json" 2>/dev/null || stat -c%s "data/scenarios/${TEST_UUID}.json")
    echo "✓ Trace file exists (${FILE_SIZE} bytes)"

    # JSONの妥当性チェック
    if command -v jq &> /dev/null; then
        jq . "data/scenarios/${TEST_UUID}.json" > /dev/null
        echo "✓ Trace file is valid JSON"
    fi
else
    echo "✗ Trace file not found"
    exit 1
fi

# 6. エラー解析テスト
echo ""
echo "Step 6: Testing error analysis..."
python3 -c "
from app.services.scenario_writer import scenario_writer

test_cases = [
    ('undefined reference to cv::', 'add_opencv_library'),
    ('connection refused', 'check_carla_running'),
    ('error: no matching function', 'check_carla_reference'),
]

for logs, expected_fix in test_cases:
    error_info = scenario_writer._analyze_build_error(logs)
    assert error_info['fix'] == expected_fix
    print(f'✓ Correctly identified: {expected_fix}')
"

# 7. クリーンアップ
echo ""
echo "Step 7: Cleanup..."
rm -f "data/scenarios/${TEST_UUID}.json"
echo "✓ Test files cleaned up"

echo ""
echo "=== All E2E tests passed! ==="
