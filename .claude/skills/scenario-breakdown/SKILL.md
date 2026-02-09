---
name: scenario-breakdown
description: This skill should be used when the user asks to "break down scenario", "expand scenario matrix", "generate scenario variations", "create multiple scenarios from one", "シナリオをブレークダウン", "マトリクス展開". Generates multiple abstract and logical scenarios from a single natural language description using PEGASUS 6 Layer matrix expansion.
  - "scenario breakdown"
  - "複数シナリオ生成"
  - "シナリオマトリクス"
  - "PEGASUS組み合わせ"
  - "シナリオバリエーション"
  - "網羅的シナリオ生成"
---

# Scenario Breakdown Skill

**役割**: 1つの自然言語シナリオ要件からPEGASUS 6 Layerのマトリクスを生成し、複数の抽象・論理シナリオを網羅的に生成する。

## 概要

このスキルは、ISO 34501/34502に準拠したPEGASUS 6 Layer概念を用いて、1つのシナリオ要件から複数のバリエーションを体系的に生成します。

```
自然言語要件
  ↓
【Phase 0】PEGASUS分析 & マトリクス生成
  ├─ Layer 1: 道路タイプ/トポロジー
  ├─ Layer 2: インフラ
  ├─ Layer 4: マニューバー
  └─ Layer 5: 環境条件
  ↓
  組み合わせマトリクス（N個の組み合わせ）
  ↓
【Phase 1】抽象シナリオ生成（バッチ）
  各組み合わせ → 抽象シナリオ（PEGASUS情報含む）
  ↓
【Phase 2】論理シナリオ生成（バッチ）
  各抽象シナリオ → サブエージェント起動 → 論理シナリオ
  ↓
【Phase 3】Python実装生成（バッチ）
  各論理シナリオ → サブエージェント起動 → Pythonスクリプト
  ↓
【Phase 4】レポート生成
  全体サマリー & シナリオ一覧
```

## トリガー条件

以下のキーワードが含まれる場合、このスキルを使用してください：

- **"シナリオをブレークダウン"**
- **"複数シナリオ生成"**
- **"シナリオマトリクス"**
- **"PEGASUS組み合わせ"**
- **"網羅的にシナリオを生成"**
- **"バリエーション展開"**

### 使用例

```
ユーザー: 「高速道路で前方車両に追従するシナリオを複数バリエーション生成して」

→ このスキルを起動し、以下を生成：
  - 晴天×昼間×直線道路
  - 雨天×夜間×カーブ道路
  - 霧×夕方×合流地点
  ...
```

## ワークフロー詳細

### Phase 0: PEGASUS分析 & マトリクス生成

#### Step 0.1: 自然言語要件の分析

まず、ユーザーの要件を理解し、以下を抽出します：

- **シナリオの種類**: 追従、車線変更、交差点通過、合流など
- **主要なアクター**: ego vehicle、他車両、歩行者など
- **環境の制約**: 高速道路、市街地など

#### Step 0.2: PEGASUS Layer 1～5の項目リストアップ

**`pegasus-analyzer`スキルを使用して**、各レイヤーの項目を独立にリストアップします。

**重要**: `pegasus-analyzer`スキルを明示的に呼び出してください。

**Layer 1: Road-level（道路レベル）**
- `road_type`: highway, urban, rural, parking
- `topology`: straight, curve, intersection, merge, split
- `num_lanes`: 1～4
- `lane_width`: 3.0～3.7m

**例（高速道路追従シナリオ）**:
```python
layer1_options = [
    {"road_type": "highway", "topology": "straight", "num_lanes": 3},
    {"road_type": "highway", "topology": "curve", "num_lanes": 2},
    {"road_type": "highway", "topology": "merge", "num_lanes": 3}
]
```

**Layer 2: Traffic Infrastructure（交通インフラ）**
- 信号機の有無
- 交通標識の種類
- 路面標示

**例**:
```python
layer2_options = [
    {"traffic_lights": [], "traffic_signs": [{"sign_type": "speed_limit", "value": "100"}]},
    {"traffic_lights": [], "traffic_signs": [{"sign_type": "speed_limit", "value": "80"}]},
    # 高速道路なので信号機なし
]
```

**Layer 4: Moving Objects（移動物体）**
- マニューバーのバリエーション
- 初期速度範囲
- 車間距離範囲

**例**:
```python
layer4_options = [
    {"lead_maneuver": "constant_speed", "initial_distance": 50.0},
    {"lead_maneuver": "deceleration", "initial_distance": 30.0},
    {"lead_maneuver": "acceleration", "initial_distance": 70.0}
]
```

**Layer 5: Environment Conditions（環境条件）**
- `weather`: clear, rain, snow, fog
- `time_of_day`: morning, afternoon, evening, night
- `road_surface`: dry, wet, frozen

**例**:
```python
layer5_options = [
    {"weather": "clear", "time_of_day": "afternoon", "road_surface": "dry"},
    {"weather": "rain", "time_of_day": "night", "road_surface": "wet"},
    {"weather": "fog", "time_of_day": "morning", "road_surface": "dry"}
]
```

**Layer 6: Digital Information（デジタル情報）**
- センサー構成は基本的に固定
- V2X有無のバリエーション（オプション）

#### Step 0.3: 組み合わせマトリクス生成

各レイヤーの項目を組み合わせて、マトリクスを生成します。

**重要な考慮事項**:

1. **組み合わせ爆発を防ぐ**
   - 全組み合わせを生成すると膨大な数になるため、**代表的な組み合わせ**を選択
   - 例: Layer 1（3種類）× Layer 5（3種類）= 9組み合わせ
   - Layer 4は各組み合わせ内でパラメータ空間として扱う

2. **無効な組み合わせを除外**
   - 例: `road_type=parking` × `topology=merge` は不適切
   - 例: `road_type=highway` × `traffic_lights` は通常存在しない

3. **Criticality Levelの付与**
   - 各組み合わせに対してCriticality（1-5）を自動評価
   - 例: 雨天×夜間×カーブ = Criticality 4（高リスク）

**マトリクス例**:

```
| ID | Layer1_Road | Layer1_Topology | Layer5_Weather | Layer5_Time | Criticality |
|----|-------------|-----------------|----------------|-------------|-------------|
| 1  | highway     | straight        | clear          | afternoon   | 2           |
| 2  | highway     | straight        | rain           | night       | 4           |
| 3  | highway     | curve           | clear          | afternoon   | 3           |
| 4  | highway     | curve           | fog            | morning     | 4           |
| 5  | highway     | merge           | clear          | afternoon   | 3           |
| 6  | highway     | merge           | rain           | evening     | 5           |
```

**出力フォーマット**:

マトリクスをMarkdownテーブルとして表示し、ユーザーに確認を求めます。

```markdown
## 生成されたシナリオマトリクス

合計 **6個** の組み合わせを生成しました。

| ID | 道路タイプ | トポロジー | 天候 | 時間帯 | 路面 | Criticality |
|----|----------|-----------|------|--------|------|-------------|
| 1  | 高速道路  | 直線      | 晴天 | 昼     | 乾燥 | ⭐⭐ (2)    |
| 2  | 高速道路  | 直線      | 雨天 | 夜     | 湿潤 | ⭐⭐⭐⭐ (4) |
| ...

このマトリクスで抽象シナリオを生成しますか？ (yes/no)
```

### Phase 1: 抽象シナリオ生成（バッチ）

#### Step 1.1: 各組み合わせに対する抽象シナリオ生成

マトリクスの各行に対して、抽象シナリオを生成します。

**重要**: `app.models.scenario_hierarchy.AbstractScenario`を使用してください。

```python
from app.models.scenario_hierarchy import AbstractScenario
from app.models.pegasus_layers import RoadLevel, EnvironmentConditions, MovingObject
from app.models.scenario_builder import ScenarioBuilder
from app.models.scenario_serializer import ScenarioSerializer

# マトリクスID 1の場合
builder = ScenarioBuilder()

abstract = builder.create_abstract_scenario(
    name=f"高速道路追従シナリオ - Matrix ID: 1",
    description="高速道路直線路で前方車両に追従するシナリオ（晴天・昼間）",
    original_prompt="高速道路で前方車両に追従するシナリオを複数バリエーション生成",
    environment={
        "location_type": "highway",
        "features": ["road", "vehicles", "lane_markings"]
    },
    actors=[
        {
            "id": "ego_vehicle",
            "type": "vehicle",
            "role": "自動運転車両（追従する側）",
            "description": "速度を調整して前方車両との車間距離を維持"
        },
        {
            "id": "lead_vehicle",
            "type": "vehicle",
            "role": "前方車両",
            "description": "一定速度で走行"
        }
    ],
    maneuvers=[
        {
            "actor_id": "ego_vehicle",
            "maneuver_type": "follow_lane",
            "description": "車線を維持しながら前方車両に追従"
        },
        {
            "actor_id": "lead_vehicle",
            "maneuver_type": "constant_speed",
            "description": "一定速度で直進"
        }
    ],
    scenario_type="vehicle_following",
    tags=["highway", "following", "cruise_control"],
    # PEGASUS Layer 1
    pegasus_layer1_road=RoadLevel(
        road_type=RoadType.HIGHWAY,
        topology=RoadTopology.STRAIGHT,
        num_lanes=3,
        lane_width=3.5
    ),
    # PEGASUS Layer 2
    pegasus_layer2_infrastructure=TrafficInfrastructure(
        traffic_signs=[
            TrafficSign(
                id="speed_limit_100",
                sign_type=TrafficSignType.SPEED_LIMIT,
                value="100"
            )
        ]
    ),
    # PEGASUS Layer 4
    pegasus_layer4_objects=[
        MovingObject(
            id="ego_vehicle",
            object_type=ObjectType.VEHICLE,
            initial_state=InitialState(
                position=(0.0, 0.0, 0.5),
                velocity=27.8  # 100 km/h
            ),
            maneuver=ManeuverType.FOLLOW_LANE,
            is_autonomous=True
        ),
        MovingObject(
            id="lead_vehicle",
            object_type=ObjectType.VEHICLE,
            initial_state=InitialState(
                position=(50.0, 0.0, 0.5),
                velocity=27.8
            ),
            maneuver=ManeuverType.FOLLOW_LANE
        )
    ],
    # PEGASUS Layer 5
    pegasus_layer5_environment=EnvironmentConditions(
        weather=WeatherCondition.CLEAR,
        time_of_day=TimeOfDay.AFTERNOON,
        road_surface=RoadSurface.DRY,
        visibility=10000.0,
        temperature=20.0
    ),
    # PEGASUS Layer 6
    pegasus_layer6_digital=DigitalInformation(
        v2x_enabled=False,
        sensors=[
            SensorConfiguration(
                sensor_type="camera",
                range=100.0,
                fov=90.0
            ),
            SensorConfiguration(
                sensor_type="radar",
                range=200.0,
                fov=120.0
            )
        ]
    ),
    # Criticality
    pegasus_criticality_level=2
)

# JSONとして保存
serializer = ScenarioSerializer()
abstract_uuid = abstract.uuid
serializer.save_abstract_scenario(abstract, f"data/scenarios/abstract_{abstract_uuid}.json")
```

#### Step 1.2: 全抽象シナリオの保存とサマリー

生成された抽象シナリオのUUIDをリストに保存し、サマリーを表示します。

```markdown
## Phase 1完了: 抽象シナリオ生成

合計 **6個** の抽象シナリオを生成しました。

| Matrix ID | Abstract UUID | 名前 | Criticality |
|-----------|---------------|------|-------------|
| 1 | abc123... | 高速道路追従 - Matrix ID: 1 | 2 |
| 2 | def456... | 高速道路追従 - Matrix ID: 2 | 4 |
| ...

次に、各抽象シナリオから論理シナリオを生成します。
```

### Phase 2: 論理シナリオ生成（バッチ）

#### Step 2.1: サブエージェントの起動

**重要**: 各抽象シナリオに対して、**scenario-writerスキルのサブエージェント**を起動して論理シナリオを生成します。

**現在の`scenario-writer`スキルの構造**:
- Phase 1: 抽象シナリオ生成（スキップ、既に生成済み）
- Phase 2: 論理シナリオ生成 ← **ここを利用**
- Phase 3: Python実装生成
- Phase 4: 実行

**サブエージェント呼び出し方法**:

`Task`ツールで`general-purpose`エージェントを起動し、各抽象シナリオに対して論理シナリオを生成します。

```markdown
【サブエージェント起動: Matrix ID 1】

タスク: 抽象シナリオ `abc123...` から論理シナリオを生成してください。

抽象シナリオは以下のファイルに保存されています:
`data/scenarios/abstract_abc123....json`

以下の手順で論理シナリオを生成してください:

1. 抽象シナリオJSONを読み込む
2. PEGASUS Layer情報を参照する
3. パラメータ空間を定義する（例: ego速度 80-120 km/h, 車間距離 30-70m）
4. `LogicalScenario`データクラスを使用して論理シナリオを作成
5. JSONとして保存: `data/scenarios/logical_{uuid}.json`

**重要制約**:
- Python実装は**生成しない**（論理シナリオのみ）
- 実行は**行わない**
- 論理シナリオJSONの保存のみ

論理シナリオUUIDを返してください。
```

**並列実行の検討**:

複数の抽象シナリオがある場合、サブエージェントを並列起動して効率化できます。

```python
# 疑似コード
tasks = []
for abstract_uuid in abstract_uuids:
    task = Task(
        subagent_type="general-purpose",
        prompt=f"抽象シナリオ {abstract_uuid} から論理シナリオを生成",
        description=f"Generate logical scenario for {abstract_uuid}"
    )
    tasks.append(task)

# 並列実行
results = execute_tasks_in_parallel(tasks)
```

#### Step 2.2: 論理シナリオの検証

各サブエージェントが返した論理シナリオUUIDを検証します。

```python
import json
from pathlib import Path

for logical_uuid in logical_uuids:
    logical_file = Path(f"data/scenarios/logical_{logical_uuid}.json")

    if not logical_file.exists():
        print(f"❌ エラー: 論理シナリオが見つかりません: {logical_uuid}")
        continue

    with open(logical_file) as f:
        logical_data = json.load(f)

    # 検証
    assert logical_data['parent_abstract_uuid'] == abstract_uuid
    assert 'parameter_space' in logical_data
    print(f"✓ 論理シナリオ検証完了: {logical_uuid}")
```

### Phase 3: Python実装生成（バッチ）

#### Step 3.1: サブエージェントの起動（Python実装）

各論理シナリオに対して、**scenario-writerスキルのサブエージェント**を起動してPython実装を生成します。

**サブエージェント呼び出し方法**:

```markdown
【サブエージェント起動: Python実装生成】

タスク: 論理シナリオ `def456...` からPython実装を生成してください。

論理シナリオは以下のファイルに保存されています:
`data/scenarios/logical_def456....json`

以下の手順でPython実装を生成してください:

1. 論理シナリオJSONを読み込む
2. パラメータ空間からサンプリング（1セット）
3. CARLAシナリオのPythonスクリプトを生成
4. `scenarios/{logical_uuid}.py`として保存

**実装要件**:
- carla Pythonライブラリを使用
- 同期モードで実行
- スペクターカメラを設定
- 動画とRRDファイルを出力
- ファイル名: `{logical_uuid}_{parameter_uuid}.mp4`, `{logical_uuid}_{parameter_uuid}.rrd`

**重要制約**:
- 実行は**行わない**（Pythonスクリプトの生成のみ）

Pythonスクリプトのパスを返してください。
```

#### Step 3.2: Python実装の検証

各サブエージェントが生成したPythonスクリプトを検証します。

```python
from pathlib import Path

for logical_uuid in logical_uuids:
    python_file = Path(f"scenarios/{logical_uuid}.py")

    if not python_file.exists():
        print(f"❌ エラー: Pythonスクリプトが見つかりません: {logical_uuid}")
        continue

    # 基本的な構文チェック
    try:
        with open(python_file) as f:
            compile(f.read(), python_file, 'exec')
        print(f"✓ Pythonスクリプト検証完了: {logical_uuid}")
    except SyntaxError as e:
        print(f"❌ 構文エラー: {logical_uuid} - {e}")
```

### Phase 4: レポート生成

#### Step 4.1: 全体サマリー

生成されたシナリオの全体像を表示します。

```markdown
# シナリオブレークダウン完了レポート

## 要約

- **自然言語要件**: 「高速道路で前方車両に追従するシナリオを複数バリエーション生成」
- **生成されたマトリクス数**: 6個
- **抽象シナリオ数**: 6個
- **論理シナリオ数**: 6個
- **Python実装数**: 6個

## マトリクス一覧

| Matrix ID | 道路 | トポロジー | 天候 | 時間 | Criticality | Abstract UUID | Logical UUID | Python Script |
|-----------|------|-----------|------|------|-------------|---------------|--------------|---------------|
| 1 | highway | straight | clear | afternoon | 2 | abc123... | def456... | scenarios/def456.py |
| 2 | highway | straight | rain | night | 4 | ghi789... | jkl012... | scenarios/jkl012.py |
| ...

## 次のステップ

### オプション1: 個別実行

各Pythonスクリプトを個別に実行:

```bash
# 例: Matrix ID 1のシナリオを実行
uv run python scenarios/def456....py
```

### オプション2: バッチ実行

全シナリオをバッチ実行:

```bash
uv run python scripts/batch_execute_scenarios.py --logical-uuids def456,jkl012,...
```

### オプション3: 高リスクシナリオのみ実行

Criticality 4以上のシナリオのみ実行:

```bash
make batch-execute-high-risk UUIDS=def456,jkl012,...
```
```

#### Step 4.2: シナリオファイルの保存場所

生成されたファイルの保存場所を明示します。

```
data/scenarios/
├── abstract_abc123....json    # Matrix ID 1 抽象シナリオ
├── logical_def456....json     # Matrix ID 1 論理シナリオ
├── abstract_ghi789....json    # Matrix ID 2 抽象シナリオ
├── logical_jkl012....json     # Matrix ID 2 論理シナリオ
...

scenarios/
├── def456....py               # Matrix ID 1 Python実装
├── jkl012....py               # Matrix ID 2 Python実装
...

data/videos/                   # 実行後に生成
├── def456..._{param_uuid}.mp4
├── jkl012..._{param_uuid}.mp4
...

data/rerun/                    # 実行後に生成
├── def456..._{param_uuid}.rrd
├── jkl012..._{param_uuid}.rrd
...
```

## エラーハンドリング

### 組み合わせが多すぎる場合

```
⚠️ 警告: 組み合わせ数が100を超えています（現在: 256個）

推奨事項:
1. Layer 1～5の項目数を削減してください
2. 無効な組み合わせを除外してください
3. 代表的な組み合わせのみを選択してください

続行しますか？ (yes/no)
```

### サブエージェントの失敗

```
❌ エラー: Matrix ID 3の論理シナリオ生成に失敗しました

原因: サブエージェントがタイムアウトしました

対処方法:
1. 抽象シナリオを確認してください: data/scenarios/abstract_xyz789....json
2. 手動で論理シナリオを生成してください
3. または、このMatrix IDをスキップして続行してください

スキップして続行しますか？ (yes/no)
```

## ベストプラクティス

### 1. マトリクスサイズの管理

- **推奨**: 10～30個の組み合わせ
- **許容**: 50個まで
- **非推奨**: 100個以上（実行時間が膨大）

### 2. Layer 4の扱い

Layer 4（Moving Objects）のマニューバーは、**マトリクスには含めず**、各論理シナリオの**パラメータ空間**として定義します。

理由: Layer 4の組み合わせまでマトリクスに含めると、組み合わせ爆発が発生するため。

### 3. Criticality Levelの活用

生成後、高Criticalityシナリオ（4-5）を優先的に実行・テストすることで、リスクの高いシナリオを早期に検証できます。

```bash
# Criticality 4以上のシナリオのみを実行
uv run python scripts/batch_execute_scenarios.py --min-criticality 4
```

### 4. 段階的な生成

大規模なマトリクスの場合、段階的に生成することを推奨します：

1. **Step 1**: Layer 1 × Layer 5（道路 × 環境）でマトリクス生成
2. **Step 2**: 抽象シナリオ生成
3. **Step 3**: ユーザー確認
4. **Step 4**: 論理シナリオ生成（必要なもののみ）

## 使用例

### 例1: 高速道路追従シナリオ

```
ユーザー: 「高速道路で前方車両に追従するシナリオを複数バリエーション生成してください」

【Phase 0】
- Layer 1: highway × (straight, curve, merge)
- Layer 5: (clear×afternoon, rain×night, fog×morning)
- マトリクス: 3 × 3 = 9個

【Phase 1】
- 9個の抽象シナリオを生成

【Phase 2】
- 9個の論理シナリオを生成（サブエージェント × 9）

【Phase 3】
- 9個のPython実装を生成（サブエージェント × 9）

【Phase 4】
- レポート表示
```

### 例2: 市街地交差点シナリオ

```
ユーザー: 「市街地の交差点で右折するシナリオをバリエーション展開して」

【Phase 0】
- Layer 1: urban × intersection
- Layer 2: (traffic_light, stop_sign)
- Layer 5: (clear×afternoon, rain×night)
- マトリクス: 1 × 2 × 2 = 4個

【Phase 1】
- 4個の抽象シナリオを生成

【Phase 2】
- 4個の論理シナリオを生成

【Phase 3】
- 4個のPython実装を生成

【Phase 4】
- レポート表示
```

## 関連ツール

- **`pegasus-analyzer`スキル**: PEGASUS 6 Layer分析（Phase 0で使用）
- **`scenario-writer`スキル**: シナリオ生成・実行（Phase 2で使用）
- **`scripts/batch_execute_scenarios.py`**: 複数シナリオのバッチ実行（今後実装）

## 参考資料

- **PEGASUS統合ガイド**: `docs/PEGASUS_INTEGRATION.md`
- **シナリオ階層モデル**: `app/models/scenario_hierarchy.py`
- **PEGASUS Layerモデル**: `app/models/pegasus_layers.py`

---

**このスキルは、体系的なシナリオ生成とテストカバレッジの向上を目的としています。**
