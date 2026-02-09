---
name: scenario-writer
description: This skill should be used when the user asks to "create scenario", "generate CARLA scenario", "build new scenario", "シナリオ生成", "シナリオ作成", "新しいシナリオ", or provides natural language scenario requirements. Automates full workflow from requirements analysis through Python implementation and execution using PEGASUS 6 Layer framework.
---

# Scenario Writer Agent

**役割**: ユーザーの自然言語要件からCARLAシミュレーション用のシナリオを生成し、Python実装、実行、デバッグまでを自動化する統合エージェント。

## 🆕 PEGASUS 6 Layer統合

**重要**: シナリオ生成前に、必ず`pegasus-analyzer`スキルを使ってPEGASUS 6 Layerに基づいた要件分析を行うこと。

### ワークフロー

1. **Phase 0: PEGASUS分析** 🆕
   - ユーザー要件を受け取る
   - `pegasus-analyzer`スキルで6 Layerに基づいて分析
   - 構造化された情報を抽出（道路、インフラ、移動物体、環境、デジタル情報）
   - Criticalityレベルを評価

2. **Phase 1: 抽象シナリオ生成**
   - PEGASUS分析結果を基に抽象シナリオを生成
   - 6 Layerの情報をAbstractScenarioに統合

3. **Phase 2: 論理シナリオ生成**
   - パラメータ空間を定義
   - PEGASUS Layer 4, 5の情報からパラメータを抽出

4. **Phase 3-5: 実装・実行・トレース保存**
   - 従来通り

### PEGASUS分析の利用

PEGASUS分析で得られた情報は、以下のように活用されます：

- **Layer 1 (Road)**: CARLAマップ選択、スポーン位置の決定
- **Layer 2 (Infrastructure)**: 信号機、標識の配置（現在は限定的サポート）
- **Layer 3 (Manipulation)**: 特殊条件の実装（将来対応）
- **Layer 4 (Objects)**: 車両・歩行者の初期状態、マニューバー定義
- **Layer 5 (Environment)**: 天候、時間帯、路面状態の設定
- **Layer 6 (Digital)**: センサー設定、V2X通信（将来対応）

## 重要な制約事項

1. **すべての車両はCARLAのNPC**
   - 現時点では外部の自動運転スタックは統合されていない
   - 1台は「将来自動運転スタックを統合予定」のNPCとしてマーク（`is_autonomous_stack: true`）

2. **同期モードで実行（オプション）**
   - 決定性を担保する場合、CARLAを同期モードで動作させる
   - 固定タイムステップ（`fixed_delta_seconds=0.05`）で20Hz実行

3. **カメラ配置（オプション）**
   - 自動運転スタック予定NPCの運転席付近にカメラを配置可能
   - カメラ映像を記録する場合はOpenCVを使用

4. **ファイル命名規則**
   - 各シナリオは論理シナリオのUUIDで識別
   - Pythonファイル: `scenarios/{logical_uuid}.py`
   - パラメータファイル: `data/scenarios/params_{parameter_uuid}.json`
   - 出力ファイル: `{logical_uuid}_{parameter_uuid}.rrd`、`{logical_uuid}_{parameter_uuid}.mp4`
   - **理由**: 1つの論理シナリオを異なるパラメータで複数回実行可能

5. **Python実装**
   - CARLA Python APIを使用
   - ビルド不要、直接実行可能
   - `uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{parameter_uuid}.json`で実行

6. **🚨 CRITICAL: Traffic Managerで車両制御**
   - **すべての車両は必ずCARLA Traffic Managerで制御すること**
   - 単純な`vehicle.set_autopilot(True)`ではなく、明示的にTraffic Managerを取得・設定する
   - Traffic Managerの同期モードを有効化（`traffic_manager.set_synchronous_mode(True)`）
   - 信号機認識を100%守る設定（`ignore_lights_percentage(vehicle, 0)`）

   **実装例**:
   ```python
   # Traffic Managerを取得（ポート: CARLA_PORT + 6000）
   traffic_manager = client.get_trafficmanager(carla_config['port'] + 6000)
   traffic_manager.set_synchronous_mode(True)

   # Traffic Managerで車両を制御
   vehicle.set_autopilot(True, traffic_manager.get_port())

   # Traffic Manager設定
   traffic_manager.ignore_lights_percentage(vehicle, 0)  # 信号を100%守る
   traffic_manager.distance_to_leading_vehicle(vehicle, 2.0)  # 前方車両との距離
   traffic_manager.vehicle_percentage_speed_difference(vehicle, -20)  # 制限速度の20%減
   ```

   **理由**: Traffic Managerを使うことで、信号機認識、レーン追従、他車両との協調動作が確実に機能する

## 🚨 CARLA環境の制約

### 利用可能なマップ

現在のCARLA環境で利用可能なマップ：
- `Town10HD_Opt` （デフォルト推奨）
- `NishishinjukuMap`

**重要**: パラメータで指定するマップは必ず現在CARLAで読み込まれているマップと一致させること。

### 利用可能な車両

Town10HD_Optで利用可能な車両（2026年2月時点）：
- `vehicle.taxi.ford` （推奨）
- `vehicle.dodgecop.charger`
- `vehicle.ue4.chevrolet.impala`
- `vehicle.ue4.mercedes.ccc`
- `vehicle.ue4.ford.mustang`
- `vehicle.ue4.bmw.grantourer`
- `vehicle.dodge.charger`
- `vehicle.nissan.patrol`
- `vehicle.mini.cooper`
- `vehicle.lincoln.mkz`

その他17台の車両が利用可能。詳細は `uv run python scripts/list_vehicles.py` で確認。

### スペクターカメラと動画記録

**必須要件**: 全てのシナリオで以下を実装すること：

1. **スペクターカメラの配置**
   - ego車両の後方上に配置
   - オフセット: `(-5.0, 0.0, 2.5)` メートル
   - Pitch: `-15°` （やや下向き）

2. **動画記録**
   - imageioを使用
   - フォーマット: MP4 (H.264)
   - 解像度: 1280x720
   - フレームレート: 20 FPS
   - 出力: `data/videos/{{logical_uuid}}_{{parameter_uuid}}.mp4`

## ⚠️ 重要: ScenarioManagerの使用

**UUID生成とJSON管理は必ず`scripts/scenario_manager.py`を使用してください**。

このスキルの各Phaseは、以下のPythonスクリプトを使用して自動化されます：

```python
from scripts.scenario_manager import ScenarioManager

manager = ScenarioManager()

# Phase 1: 抽象シナリオ作成
abstract_uuid = manager.create_abstract_scenario(
    name="シナリオ名",
    description="詳細な説明",
    original_prompt="ユーザーの元の要件",
    environment={...},
    actors=[...],
    scenario_type="scenario_type"
)

# Phase 2: 論理シナリオ作成（分布情報のみ）
logical_uuid = manager.create_logical_scenario(
    parent_abstract_uuid=abstract_uuid,
    name="論理シナリオ名",
    description="パラメータ空間の説明",
    parameter_space={
        "actor_id": {
            "param_name": {
                "type": "float",
                "unit": "km/h",
                "distribution": "uniform",
                "min": 20.0,
                "max": 40.0,
                "description": "パラメータの説明"
            }
        }
    }
)

# Phase 3: パラメータサンプリング（具体値を生成）
parameter_uuid = manager.sample_parameters(
    logical_uuid=logical_uuid,
    carla_config={
        "host": "localhost",
        "port": 2000,
        "map": "Town10HD_Opt",
        "vehicle_type": "vehicle.taxi.ford"
    },
    seed=42  # 再現性のため（オプション）
)

# Phase 3: サンプリングされたパラメータを取得
params = manager.get_parameters(logical_uuid, parameter_uuid)
# params["sampled_values"] に具体値が入っている

# Phase 5: 実行トレース作成
manager.create_execution_trace(
    logical_uuid=logical_uuid,
    parameter_uuid=parameter_uuid,
    python_file=f"scenarios/{logical_uuid}.py",
    command="実行コマンド",
    exit_code=0,
    status="success"
)
```

詳細は`docs/DATA_MODEL.md`を参照してください。

---

## ワークフロー

### Phase 0: 自然言語シナリオ記録とPEGASUS分析

**目的**: ユーザーの要件を記録し、PEGASUS 6 Layerで構造化分析

**手順**:

1. **自然言語シナリオの記録**
   - **ScenarioManagerを使用**: `manager.create_natural_scenario()`を呼び出し
   - ユーザーの元の要件をそのまま記録

   ```python
   from scripts.scenario_manager import ScenarioManager

   manager = ScenarioManager()
   natural_uuid = manager.create_natural_scenario(
       prompt="市街地交差点で死角から車両が突然飛び出してくる危険なシナリオ",
       user_metadata={
           "source": "user_input",
           "context": "危険シナリオのテスト"
       }
   )
   ```

2. **PEGASUS 6 Layer分析**
   - 自然言語要件をPEGASUS 6 Layerの観点から分析
   - 各Layerについて以下を抽出:
     - **description**: 自然言語での説明
     - **expected_values**: 期待される値の範囲や選択肢（パラメータ空間のヒント）
     - **carla_mapping**: CARLAでの実装方法

   **PEGASUS 6 Layer**:
   - **Layer 1 (Road)**: 道路タイプ、トポロジー、レーン数
   - **Layer 2 (Infrastructure)**: 信号機、標識、道路標示
   - **Layer 3 (Temporary Manipulation)**: 工事、障害物、視界遮蔽
   - **Layer 4 (Moving Objects)**: 車両、歩行者、マニューバー
   - **Layer 5 (Environment)**: 天候、時間帯、路面状態
   - **Layer 6 (Digital Information)**: センサー、V2X通信

3. **PEGASUS分析結果の記録**
   - **ScenarioManagerを使用**: `manager.create_pegasus_analysis()`を呼び出し

   ```python
   pegasus_uuid = manager.create_pegasus_analysis(
       natural_uuid=natural_uuid,
       analysis={
           "layer_1_road": {
               "description": "市街地T字路/十字路交差点",
               "expected_values": {
                   "road_type": ["urban_intersection", "T_junction"],
                   "lane_count": [2, 3]
               },
               "carla_mapping": {
                   "map": "Town10HD_Opt",
                   "road_features": ["intersection"]
               }
           },
           "layer_4_objects": {
               "description": "2台の車両（自車と飛び出し車両）",
               "expected_values": {
                   "ego_vehicle": {
                       "initial_speed": {"min": 40.0, "max": 50.0, "unit": "km/h"}
                   },
                   "oncoming_vehicle": {
                       "acceleration": {"min": 3.0, "max": 5.0, "unit": "m/s²"}
                   }
               }
           },
           # ... 他のLayer
       },
       criticality={
           "level": "high",
           "factors": ["occlusion", "sudden_maneuver"]
       }
   )
   ```

### Phase 1: 抽象シナリオ生成

**目的**: PEGASUS分析結果を基に構造化された抽象シナリオを生成

**手順**:

1. **不明点の確認**
   - `AskUserQuestion`ツールを使用して不明点を質問（必要に応じて）
   - 質問例:
     - 車両台数は？（デフォルト: 2台）
     - シナリオの継続時間は？（デフォルト: 10秒）

2. **抽象シナリオの生成**
   - **ScenarioManagerを使用**: `manager.create_abstract_scenario()`を呼び出し
   - **PEGASUS分析からの情報抽出**:
     - Layer 1 → environment.location_type
     - Layer 4 → actors
     - Layer 5 → environment (weather, time_of_day)
   - 必要な情報:
     - `name`: シナリオの短い名前
     - `description`: シナリオの詳細な説明
     - `original_prompt`: ユーザーの元の自然言語要件（**トレーサビリティ**）
     - `natural_scenario_uuid`: 自然言語シナリオUUID（**トレーサビリティ**）
     - `pegasus_analysis_uuid`: PEGASUS分析UUID（**トレーサビリティ**）
     - `pegasus_layers`: PEGASUS Layerの要約
     - `environment`: 環境設定（PEGASUS Layer 1, 5から）
     - `actors`: アクターのリスト（PEGASUS Layer 4から）
     - `scenario_type`: シナリオタイプ
     - `criticality`: 危険度レベル（PEGASUS分析から）

3. **Pythonコードで実行**
   ```python
   from scripts.scenario_manager import ScenarioManager

   manager = ScenarioManager()

   # PEGASUS分析から情報を抽出
   abstract_uuid = manager.create_abstract_scenario(
       name="交差点死角飛び出しシナリオ",
       description="市街地交差点で死角から車両が突然飛び出してくる危険なシナリオ",
       original_prompt="市街地交差点で死角から車両が突然飛び出してくる危険なシナリオ",
       natural_scenario_uuid=natural_uuid,  # トレーサビリティ
       pegasus_analysis_uuid=pegasus_uuid,  # トレーサビリティ
       pegasus_layers={
           "layer_1_road": "市街地T字路/十字路交差点",
           "layer_2_infrastructure": "信号機なし、一時停止標識あり",
           "layer_3_temporary": "建物・駐車車両による視界遮蔽",
           "layer_4_objects": "2台の車両（自車と飛び出し車両）",
           "layer_5_environment": "晴天、昼間、乾燥路面",
           "layer_6_digital": "センサーベース認識（カメラ、LiDAR）"
       },
       environment={
           "location_type": "urban_intersection",
           "weather": "clear",
           "time_of_day": "noon",
           "road_condition": "dry",
           "features": ["occlusion", "buildings"]
       },
       actors=[
           {
               "id": "ego_vehicle",
               "type": "vehicle",
               "role": "自動運転予定車両",
               "is_autonomous_stack": True
           },
           {
               "id": "oncoming_vehicle",
               "type": "vehicle",
               "role": "飛び出し車両",
               "is_autonomous_stack": False
           }
       ],
       scenario_type="intersection_occlusion_hazard",
       criticality="high"
   )

   print(f"抽象シナリオUUID: {abstract_uuid}")
   ```

4. **ユーザー確認**
   - 生成された抽象シナリオのUUIDとパスをユーザーに提示
   - ファイルパス: `data/scenarios/abstract_{abstract_uuid}.json`
   - PEGASUS Layerとの対応を表示
   - 承認を得る

**重要**: UUIDは自動生成され、ファイルも自動保存されます。トレーサビリティが完全に保たれます。

### Phase 2: 論理シナリオ生成

**目的**: PEGASUS分析の`expected_values`からパラメータ空間を抽出し、論理シナリオを生成

**🚨 重要**: 論理シナリオには**分布情報のみ**を記録し、具体値は含めないこと（トレーサビリティ確保）

**手順**:

1. **PEGASUS分析からパラメータ空間を抽出**
   - **Layer 4 (Objects)**の`expected_values`からパラメータを抽出:
     - 初速度: `ego_vehicle.initial_speed` → `{"min": 40.0, "max": 50.0}`
     - 加速度: `oncoming_vehicle.acceleration` → `{"min": 3.0, "max": 5.0}`
     - トリガー距離: `expected_values`から推定
   - **Layer 5 (Environment)**からパラメータを抽出:
     - 天候: `weather` → `["ClearNoon", "CloudyNoon"]` → `choice`または`constant`
   - **Layer 6 (Digital)**からカメラ・センサー設定を抽出

2. **パラメータ空間の設計**
   - 各パラメータに以下を定義:
     - `type`: データ型（`float`, `int`, `string`）
     - `unit`: 単位（`km/h`, `m`, `s`など）
     - `distribution`: 分布タイプ（`uniform`, `normal`, `choice`, `constant`）
     - 分布に応じたフィールド（`min/max`, `mean/std`, `choices`, `value`）
     - `description`: パラメータの説明

**PEGASUS → パラメータ空間のマッピング例**:

| PEGASUS Layer | expected_values | parameter_space |
|---------------|-----------------|-----------------|
| Layer 4: `ego_vehicle.initial_speed: {min: 40, max: 50}` | `{"min": 40.0, "max": 50.0, "unit": "km/h"}` | `{"distribution": "uniform", "min": 40.0, "max": 50.0}` |
| Layer 5: `weather: ["ClearNoon", "CloudyNoon"]` | `["ClearNoon", "CloudyNoon"]` | `{"distribution": "choice", "choices": [...]}` |
| Layer 6: `camera.fov: 90` | `90` | `{"distribution": "constant", "value": 90}` |

2. **Pythonコードで実行（🆕 自動導出）**
   ```python
   from scripts.scenario_manager import ScenarioManager
   import json

   manager = ScenarioManager()

   # 🆕 PEGASUS分析からparameter_spaceを自動導出
   pegasus_file = f"data/scenarios/pegasus_{pegasus_uuid}.json"
   with open(pegasus_file) as f:
       pegasus_data = json.load(f)

   parameter_space = manager.derive_parameter_space_from_pegasus(
       pegasus_data['analysis']
   )

   # 論理シナリオを作成（parameter_spaceは自動導出済み）
   logical_uuid = manager.create_logical_scenario(
       parent_abstract_uuid=abstract_uuid,
       name="highway_follow_logical",
       description="PEGASUS分析から自動導出されたパラメータ空間",
       parameter_space=parameter_space
   )

   print(f"論理シナリオUUID: {logical_uuid}")
   print("✅ parameter_spaceはPEGASUS分析から自動導出されました")
   print(f"✅ 導出されたパラメータ数: {sum(len(v) if isinstance(v, dict) else 1 for v in parameter_space.values())}")
   ```

   **重要**: `derive_parameter_space_from_pegasus()`が自動的に以下を行います：
   - Layer 4の`expected_values` → 各アクターのパラメータ
   - Layer 5の`expected_values` → environment パラメータ
   - Layer 6の`expected_values` → camera, simulation パラメータ
   - 範囲値（`min/max`） → `distribution: uniform`
   - 固定値（`value`） → `distribution: constant`
   - 選択肢（`choices/presets`） → `distribution: choice`

3. **ユーザー確認**
   - 生成された論理シナリオのUUIDとパスをユーザーに提示
   - ファイルパス: `data/scenarios/logical_{logical_uuid}.json`
   - パラメータ空間が適切か確認

**サポートする分布タイプ**:
- `constant`: 固定値（`value`フィールド必須）
- `uniform`: 一様分布（`min`, `max`フィールド必須）
- `normal`: 正規分布（`mean`, `std`フィールド必須）
- `choice`: 選択肢（`choices`フィールド必須）

**重要**: `speed: 50.0`のような具体値は入れないこと。代わりに`"distribution": "constant", "value": 50.0`と記述する。

### Phase 3: パラメータサンプリングとPython実装生成

**目的**: 論理シナリオからパラメータをサンプリングし、CARLA Python実装を生成

**手順**:

1. **パラメータのサンプリング**
   - **ScenarioManagerを使用**: `manager.sample_parameters()`を呼び出し
   - 論理シナリオのparameter_spaceから具体値を生成
   - 乱数シード（seed）を指定して再現性を確保（オプション）

   ```python
   from scripts.scenario_manager import ScenarioManager

   manager = ScenarioManager()

   # パラメータをサンプリング（具体値を生成）
   parameter_uuid = manager.sample_parameters(
       logical_uuid=logical_uuid,
       carla_config={
           "host": "localhost",
           "port": 2000,
           "map": "Town10HD_Opt",
           "vehicle_type": "vehicle.taxi.ford"
       },
       seed=42  # 再現性のため（オプション）
   )

   # サンプリングされたパラメータを取得
   params = manager.get_parameters(logical_uuid, parameter_uuid)

   # params["sampled_values"] に具体値が入っている
   # 例: params["sampled_values"]["ego_vehicle"]["initial_speed"] = 45.2
   ```

2. **Python実装の生成**
   - **ファイル名**: 論理シナリオの`uuid`を使用
   - `scenarios/{logical_uuid}.py`として保存
   - ファイル内に`logical_uuid`をコメントで記録
   - コマンドライン引数で`logical_uuid`と`param_uuid`を受け取る
   - 要件:
     - CARLA Python APIを使用
     - **🚨 CRITICAL: `opendrive_utils`ライブラリを必ず使用**（詳細は下記）
     - 同期モード設定（オプション）
     - スペクターカメラ配置と動画記録（imageio使用、**必須**）
     - try-finally でクリーンアップ

3. **Python実装のコマンドライン引数**
   ```python
   import argparse
   from scripts.scenario_manager import ScenarioManager

   def main():
       parser = argparse.ArgumentParser()
       parser.add_argument('--logical-uuid', required=True, help='論理シナリオUUID')
       parser.add_argument('--param-uuid', required=True, help='パラメータUUID')
       args = parser.parse_args()

       # ScenarioManagerからパラメータを取得
       manager = ScenarioManager()
       params = manager.get_parameters(args.logical_uuid, args.param_uuid)

       # sampled_valuesから具体値を取得
       ego_speed = params['sampled_values']['ego_vehicle']['initial_speed']
       carla_config = params['carla_config']
       output_video = params['output']['mp4_file']

       # CARLAシミュレーション実行
       run_simulation(params)
   ```

4. **実行コマンド**
   ```bash
   uv run python scenarios/{logical_uuid}.py --logical-uuid {logical_uuid} --param-uuid {param_uuid}
   ```

---

## 🚨 CRITICAL: opendrive_utilsライブラリの使用

### 🎯 必須要件（絶対に守ること）

**すべてのNPC配置は`opendrive_utils`を使ってOpenDRIVEから決定すること**

これは**必須要件**です。シナリオ実装時には、以下を厳守してください：

1. ✅ **必ず`opendrive_utils`を使用**してスポーン位置を計算
2. ❌ **手動での座標指定を完全に禁止**（`carla.Location(x=100.0, y=200.0, ...)`など）
3. ❌ **`carla.Map.get_spawn_points()`の使用を禁止**
4. ⚙️ **機能が不足している場合は`opendrive_utils`に機能追加してから使用**

### 🔧 機能が不足している場合の対応

`opendrive_utils`に必要な機能がない場合：

1. **機能追加を検討する**
   - `opendrive_utils/`ディレクトリに新しい機能を追加
   - 例: 特定の交差点タイプでのスポーン、特殊なレーン配置など

2. **追加すべき機能の例**
   - 交差点の特定の位置へのスポーン
   - 信号機からの距離を考慮したスポーン
   - カーブ上での適切なスポーン
   - 複数レーンにまたがる配置

3. **🚨 必須: Git Workflowに従う**

   **重要**: opendrive_utilsに機能追加する場合は、必ずブランチを切ってPRを出すこと

   ```bash
   # 1. 機能追加用のブランチを作成
   git checkout -b feature/opendrive-utils-intersection-spawn

   # 2. 機能を実装（下記の実装例を参照）
   # opendrive_utils/spawn_helper.py または advanced_features.py を編集

   # 3. 変更をコミット
   git add opendrive_utils/
   git commit -m "Add intersection entry spawn feature to opendrive_utils

   - Implement get_spawn_at_intersection_entry() method
   - Support spawning at junction entry points
   - Add distance_before parameter for precise positioning

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

   # 4. ブランチをプッシュ
   git push origin feature/opendrive-utils-intersection-spawn

   # 5. PRを作成
   gh pr create --title "Add intersection entry spawn feature" \
                --body "## Summary
   交差点の流入部にスポーンする機能を追加

   ## Changes
   - \`AdvancedFeatures.get_spawn_at_intersection_entry()\`を実装
   - junction_id, incoming_road_id, distance_beforeパラメータをサポート

   ## Test Plan
   - [ ] 交差点でのスポーン動作を確認
   - [ ] 距離パラメータの動作を検証

   🤖 Generated with [Claude Code](https://claude.com/claude-code)"
   ```

   **レビュー＆マージ後に使用**: PRがマージされてから、シナリオスクリプトで新機能を使用してください。

4. **機能追加の実装例**
   ```python
   # opendrive_utils/spawn_helper.py または advanced_features.py に追加
   def get_spawn_at_intersection_entry(
       self,
       junction_id: int,
       incoming_road_id: int,
       distance_before: float = 10.0
   ) -> carla.Transform:
       """交差点の流入部にスポーン

       Args:
           junction_id: 交差点ID
           incoming_road_id: 流入道路ID
           distance_before: 交差点手前の距離（メートル）

       Returns:
           スポーン用Transform
       """
       # 実装...
   ```

5. **追加後に使用**
   ```python
   # シナリオスクリプトで新機能を使用
   from opendrive_utils import AdvancedFeatures

   advanced = AdvancedFeatures(od_map)
   transform = advanced.get_spawn_at_intersection_entry(
       junction_id=5,
       incoming_road_id=10,
       distance_before=15.0
   )
   ```

### ❌ 禁止事項

**以下の方法は絶対に使用しないこと**

#### 1. 手動座標指定（禁止）

```python
# ❌ BAD: 手動で座標を指定（完全に禁止）
ego_spawn_location = carla.Location(x=-50.0, y=10.0, z=0.3)
ego_spawn_rotation = carla.Rotation(pitch=0.0, yaw=0.0, roll=0.0)
ego_transform = carla.Transform(ego_spawn_location, ego_spawn_rotation)
vehicle = world.spawn_actor(blueprint, ego_transform)
```

理由：
- OpenDRIVEの道路構造を無視している
- レーン情報が反映されない
- 他の車両との関係性が不明確
- シナリオの意味的な正確性が失われる

#### 2. Spawn Points使用（禁止）

```python
# ❌ BAD: Spawn Pointsを使用（禁止）
spawn_points = world.get_map().get_spawn_points()
transform = spawn_points[0]  # ランダムな位置
vehicle = world.spawn_actor(blueprint, transform)
```

理由:
- 事前定義されたスポーン位置はランダムで、狙った位置に配置できない
- シナリオの再現性が保証されない
- レーン座標や信号機との位置関係を正確に制御できない

### ✅ 必須: opendrive_utilsの使用

**すべてのスポーン位置は`opendrive_utils`で計算すること**

```python
# ✅ GOOD: opendrive_utilsを使用
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

od_map = OpenDriveMap(world)
spawn_helper = SpawnHelper(od_map)

# レーン座標から精密にスポーン
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)
vehicle = world.spawn_actor(blueprint, transform)
```

### 基本的な使い方

#### 1. 初期化

```python
import carla
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

# CARLA接続
client = carla.Client('localhost', 2000)
world = client.get_world()

# opendrive_utils初期化
od_map = OpenDriveMap(world)
spawn_helper = SpawnHelper(od_map)
```

#### 2. レーン座標からスポーン

```python
# レーン座標を指定
lane_coord = LaneCoord(
    road_id=10,      # 道路ID
    lane_id=-1,      # レーンID（負: 右側、正: 左側）
    s=50.0,          # 道路の始点からの距離（メートル）
    offset=0.0       # レーン中心からのオフセット
)

# Transformを計算
transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)

# 車両をスポーン
blueprint = world.get_blueprint_library().find('vehicle.tesla.model3')
vehicle = world.spawn_actor(blueprint, transform)
```

#### 3. 指定距離前方にスポーン

```python
# 基準位置から30m前方にスポーン
start_lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)

forward_transform = spawn_helper.get_spawn_transform_at_distance(
    start_lane_coord,
    distance=30.0  # 30m前方
)

vehicle2 = world.spawn_actor(blueprint, forward_transform)
```

#### 4. レーン上に複数車両を配置

```python
# レーン上に5台を20m間隔で配置
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)

transforms = spawn_helper.get_spawn_points_along_lane(
    lane_coord,
    num_points=5,
    spacing=20.0  # 20m間隔
)

for transform in transforms:
    vehicle = world.spawn_actor(blueprint, transform)
    vehicles.append(vehicle)
```

### 高度な機能: 信号機・交差点を考慮したスポーン

#### 1. 信号機の手前にスポーン

```python
from opendrive_utils import AdvancedFeatures

advanced = AdvancedFeatures(od_map)

# 信号機を検索
signals = advanced.get_traffic_signals()
if signals:
    signal = signals[0]

    # 信号機の10m手前にスポーン
    transform = advanced.get_spawn_before_signal(
        signal,
        lane_id=-1,           # 右側レーン
        distance_before=10.0  # 10m手前
    )

    vehicle = world.spawn_actor(blueprint, transform)
```

#### 2. 最も近い信号機を検索してスポーン

```python
# 現在のレーン座標から最も近い信号機を検索
lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
nearest_signal = advanced.get_nearest_signal(
    lane_coord,
    max_distance=100.0  # 最大100m先まで検索
)

if nearest_signal:
    # 信号機の手前にスポーン
    transform = advanced.get_spawn_before_signal(
        nearest_signal,
        lane_id=-1,
        distance_before=15.0
    )
    vehicle = world.spawn_actor(blueprint, transform)
```

#### 3. 交差点の流入点にスポーン

```python
# 交差点情報を取得
junctions = advanced.get_junctions()
junction = list(junctions.values())[0]

# 交差点への流入点
entry_transforms = advanced.get_junction_entry_points(
    junction.id,
    incoming_road_id=10
)

for transform in entry_transforms[:3]:  # 最初の3つの流入点
    vehicle = world.spawn_actor(blueprint, transform)
    vehicles.append(vehicle)
```

#### 4. 停止線の手前にスポーン

```python
# 停止線を取得
stop_lines = advanced.get_stop_lines()

for stop_line in stop_lines[:5]:
    # 停止線の2m手前にスポーン
    transform = advanced.get_spawn_at_stop_line(
        stop_line,
        offset_before=2.0  # 2m手前
    )

    vehicle = world.spawn_actor(blueprint, transform)
    vehicles.append(vehicle)
```

### 実装例: 信号機待ちシナリオ

```python
#!/usr/bin/env python3
"""
信号機待ちシナリオ

Logical Scenario UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
"""
import carla
import time
import sys
import json
import argparse
from opendrive_utils import (
    OpenDriveMap,
    SpawnHelper,
    AdvancedFeatures,
    LaneCoord,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--params', required=True)
    args = parser.parse_args()

    with open(args.params) as f:
        params = json.load(f)

    # CARLA接続
    client = carla.Client(params['carla']['host'], params['carla']['port'])
    client.set_timeout(10.0)
    world = client.get_world()

    # opendrive_utils初期化
    od_map = OpenDriveMap(world)
    spawn_helper = SpawnHelper(od_map)
    advanced = AdvancedFeatures(od_map)

    actors = []
    try:
        blueprint_library = world.get_blueprint_library()
        vehicle_bp = blueprint_library.find('vehicle.tesla.model3')

        # 信号機を検索
        signals = advanced.get_traffic_signals()
        if not signals:
            print("信号機が見つかりません", file=sys.stderr)
            return 1

        # パラメータから道路情報を取得
        target_road_id = params['scenario']['road_id']
        target_lane_id = params['scenario']['lane_id']

        # その道路上の信号機を検索
        road_signals = [s for s in signals if s.road_id == target_road_id]
        if not road_signals:
            print(f"Road {target_road_id} に信号機が見つかりません", file=sys.stderr)
            return 1

        signal = road_signals[0]
        print(f"信号機 {signal.id} を使用: Road {signal.road_id}, s={signal.s:.2f}m")

        # Ego車両: 信号機の10m手前にスポーン
        ego_transform = advanced.get_spawn_before_signal(
            signal,
            lane_id=target_lane_id,
            distance_before=10.0
        )
        ego_vehicle = world.spawn_actor(vehicle_bp, ego_transform)
        actors.append(ego_vehicle)
        print(f"✓ Ego車両をスポーン: 信号機の10m手前")

        # NPC車両1: 信号機の30m手前にスポーン
        npc_transform_1 = advanced.get_spawn_before_signal(
            signal,
            lane_id=target_lane_id,
            distance_before=30.0
        )
        npc1 = world.spawn_actor(vehicle_bp, npc_transform_1)
        actors.append(npc1)
        print(f"✓ NPC1をスポーン: 信号機の30m手前")

        # NPC車両2: 信号機の50m手前にスポーン
        npc_transform_2 = advanced.get_spawn_before_signal(
            signal,
            lane_id=target_lane_id,
            distance_before=50.0
        )
        npc2 = world.spawn_actor(vehicle_bp, npc_transform_2)
        actors.append(npc2)
        print(f"✓ NPC2をスポーン: 信号機の50m手前")

        # Traffic Managerで制御
        traffic_manager = client.get_trafficmanager(params['carla']['port'] + 6000)
        traffic_manager.set_synchronous_mode(True)

        for vehicle in actors:
            vehicle.set_autopilot(True, traffic_manager.get_port())
            traffic_manager.ignore_lights_percentage(vehicle, 0)  # 信号を100%守る

        # シナリオ実行
        duration = params['scenario']['duration']
        steps = int(duration / 0.05)

        for i in range(steps):
            world.tick()
            time.sleep(0.05)

            if i % 20 == 0:  # 1秒ごとに出力
                ego_loc = ego_vehicle.get_location()
                signal_transform = advanced.get_signal_transform(signal)
                distance_to_signal = ego_loc.distance(signal_transform.location)
                print(f"t={i*0.05:.2f}s: 信号機まで {distance_to_signal:.2f}m")

        print("✓ シナリオ完了")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        for actor in actors:
            actor.destroy()


if __name__ == "__main__":
    sys.exit(main())
```

### パラメータファイルの構造

opendrive_utilsを使う場合、パラメータファイルには以下を含めます:

```json
{
  "parameter_uuid": "abc12345-...",
  "logical_uuid": "550e8400-...",
  "carla": {
    "host": "localhost",
    "port": 2000,
    "map": "Town10HD_Opt"
  },
  "scenario": {
    "road_id": 10,
    "lane_id": -1,
    "duration": 20.0
  },
  "output": {
    "rrd_file": "data/rerun/550e8400-..._abc12345-....rrd",
    "mp4_file": "data/videos/550e8400-..._abc12345-....mp4"
  }
}
```

**重要**: スポーン位置の座標（x, y, z, yaw）は**含めない**。代わりに`road_id`、`lane_id`、`s`（距離）を指定し、実行時に`opendrive_utils`で計算します。

### まとめ

- ✅ **必ず`opendrive_utils`を使用してスポーン位置を計算**
- ❌ **`carla.Map.get_spawn_points()`は使用禁止**
- ✅ **レーン座標（road_id, lane_id, s）から精密に配置**
- ✅ **信号機・交差点・停止線を考慮したスポーンが可能**
- ✅ **シナリオの再現性と精度が保証される**

---

2. **具体パラメータの生成**
   - **パラメータUUID生成**: `uuid.uuid4()`で新しいUUIDを生成
   - 論理シナリオから具体的なパラメータを生成:
     - CARLAマップ名（例: Town10HD_Opt）
     - 車両配置情報（road_id, lane_id, s）**※座標（x, y, z, yaw）は含めない**
     - 初期速度
     - シミュレーション時間
     - カメラ設定
     - 出力ファイルパス: `{logical_uuid}_{parameter_uuid}.rrd/mp4`
   - `data/scenarios/params_{parameter_uuid}.json`として保存

3. **生成コードの確認**
   - 以下が含まれていることを検証:
     - ✅ `argparse`でパラメータファイルを受け取る
     - ✅ JSONファイルからパラメータをロード
     - ✅ `carla.Client`で接続
     - ✅ アクターのスポーン
     - ✅ 車両制御ロジック
     - ✅ finallyブロックでクリーンアップ

4. **パラメータファイル例** (`data/scenarios/params_abc12345-6789-0123-4567-890abcdef012.json`):

   **重要**: opendrive_utilsを使用するため、スポーン位置の座標（x, y, z, yaw）は**含めません**。

   ```json
   {
     "parameter_uuid": "abc12345-6789-0123-4567-890abcdef012",
     "logical_uuid": "550e8400-e29b-41d4-a716-446655440000",
     "carla": {
       "host": "localhost",
       "port": 2000,
       "map": "Town10HD_Opt"
     },
     "scenario": {
       "road_id": 10,
       "lane_id": -1,
       "duration": 10.0,
       "ego_vehicle": {
         "s": 50.0,
         "initial_speed": 50.0
       },
       "lead_vehicle": {
         "s": 80.0,
         "initial_speed": 80.0
       },
       "target_distance": 20.0
     },
     "output": {
       "rrd_file": "data/rerun/550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.rrd",
       "mp4_file": "data/videos/550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.mp4"
     }
   }
   ```

   **説明**:
   - `road_id`, `lane_id`: レーン座標（OpenDRIVEから取得）
   - `s`: 道路の始点からの距離（メートル）
   - 実行時に`opendrive_utils`が`s`値から正確な位置と方向を計算します

5. **実装例の参照**

   **重要**: すべての実装例は `opendrive_utils` を使用する必要があります。

   opendrive_utilsを使った完全な実装例は、このドキュメントの以下のセクションを参照してください：

   - **「## 🚨 CRITICAL: opendrive_utilsライブラリの使用」セクション**
     - 基本的な使い方（レーン座標からのスポーン）
     - 信号機を考慮したスポーン
     - 交差点での配置
     - 停止線の手前へのスポーン

   - **実装例: 信号機待ちシナリオ**（行番号: 約750-900）
     - opendrive_utilsの完全な使用例
     - AdvancedFeaturesの活用
     - Traffic Managerとの統合

   **禁止事項**:
   - ❌ 手動での座標指定（`carla.Location(x=100.0, y=200.0, ...)`）
   - ❌ `carla.Map.get_spawn_points()`の使用

   **必須**:
   - ✅ `opendrive_utils.SpawnHelper`を使用してレーン座標から配置
   - ✅ 機能が不足している場合は`opendrive_utils`に機能追加してから使用

### Phase 4: 実行・デバッグ

**目的**: Pythonコードを実行し、エラーを自動修正

**手順**:

1. **Python実行**
   - Bashツールで実行: `uv run python scenarios/{logical_uuid}.py --params data/scenarios/params_{parameter_uuid}.json`
   - CARLAサーバーが起動しているか事前確認
   - 出力ファイル: `data/rerun/{logical_uuid}_{parameter_uuid}.rrd`、`data/videos/{logical_uuid}_{parameter_uuid}.mp4`

2. **エラー検出と修正**
   - エラーの種類に応じた修正を適用:
     - `RuntimeError: time-out`: CARLA未起動 → ユーザーに通知
     - `RuntimeError: failed to spawn`: スポーンポイント不足 → 複数試行
     - `IndexError: list index out of range`: Blueprint不在 → フィルター変更
     - その他のランタイムエラー: ログを確認して修正

3. **自動修正例**
   ```python
   # Blueprint not found エラーの修正
   # Before:
   vehicle_bp = blueprint_library.filter('vehicle.tesla.model3')[0]

   # After:
   vehicles = blueprint_library.filter('vehicle.*')
   if len(vehicles) == 0:
       print("No vehicles available", file=sys.stderr)
       sys.exit(1)
   vehicle_bp = vehicles[0]
   ```

4. **成功時**
   - シナリオが正常に実行され、指定時間後に終了
   - オプション: Rerunログ（.rrd）や動画（.mp4）の生成を確認

**出力ファイル（オプション）**:

- **RRDファイル** (`data/rerun/{logical_uuid}_{parameter_uuid}.rrd`):
  - Rerun Python SDKで記録された3D可視化データ
  - 車両の軌跡、位置、速度
  - `import rerun as rr`で記録

- **MP4ファイル** (`data/videos/{logical_uuid}_{parameter_uuid}.mp4`):
  - imageioで記録
  - RGB Camera Sensorからの映像

**ファイル名の意味**:
- `logical_uuid`: どの論理シナリオの実行か
- `parameter_uuid`: どのパラメータセットで実行したか
- 同じ論理シナリオを異なるパラメータで複数回実行可能

### Phase 5: 実行トレース保存

**目的**: シナリオ実行の記録。抽象→論理→パラメータ→実装の完全なトレーサビリティを確保

**手順**:

1. **実行トレースの作成**
   - **ScenarioManagerを使用**: `manager.create_execution_trace()`を呼び出し
   - 実行結果を記録（成功/失敗、終了コード）

   ```python
   from scripts.scenario_manager import ScenarioManager

   manager = ScenarioManager()

   # シナリオを実行
   import subprocess
   python_file = f"scenarios/{logical_uuid}.py"
   command = f"uv run python {python_file} --logical-uuid {logical_uuid} --param-uuid {parameter_uuid}"

   result = subprocess.run(command, shell=True, capture_output=True, text=True)

   # 実行トレースを記録
   trace_file = manager.create_execution_trace(
       logical_uuid=logical_uuid,
       parameter_uuid=parameter_uuid,
       python_file=python_file,
       command=command,
       exit_code=result.returncode,
       status="success" if result.returncode == 0 else "failed"
   )

   print(f"実行トレースを保存: {trace_file}")
   ```

2. **トレーサビリティの自動記録**
   - 抽象シナリオUUID（parent_abstract_uuid）
   - 論理シナリオUUID
   - パラメータUUID
   - Python実装ファイルパス
   - 実行コマンド
   - 出力ファイルパス（動画、RRD）

3. **UI表示**
   - UIがある場合、シナリオ一覧を更新
   - ユーザーにシナリオが生成されたことを通知

**自動生成される実行トレースファイル** (`data/scenarios/execution_{logical_uuid}_{parameter_uuid}.json`):
```json
{
  "execution_uuid": "abc12345-6789-0123-4567-890abcdef012",
  "logical_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "abstract_uuid": "a1b2c3d4-e5f6-4789-a012-3456789abcde",
  "parameter_uuid": "abc12345-6789-0123-4567-890abcdef012",
  "name": "highway_follow",
  "description": "高速道路で前方車両を20m間隔で追従するシナリオ",
  "executed_at": "2026-02-06T23:53:00Z",
  "trace": {
    "abstract_scenario_file": "data/scenarios/abstract_a1b2c3d4-e5f6-4789-a012-3456789abcde.json",
    "logical_scenario_file": "data/scenarios/logical_550e8400-e29b-41d4-a716-446655440000.json",
    "parameter_file": "data/scenarios/params_abc12345-6789-0123-4567-890abcdef012.json",
    "implementation": {
      "python_file": "scenarios/550e8400-e29b-41d4-a716-446655440000.py",
      "command": "uv run python scenarios/550e8400-e29b-41d4-a716-446655440000.py --params data/scenarios/params_abc12345-6789-0123-4567-890abcdef012.json",
      "exit_code": 0,
      "final_status": "success"
    }
  },
  "outputs": {
    "rerun": "data/rerun/550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.rrd",
    "video": "data/videos/550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.mp4"
  }
}
```

**ファイルパス**: `data/scenarios/execution_550e8400-e29b-41d4-a716-446655440000_abc12345-6789-0123-4567-890abcdef012.json`

**トレーサビリティの自動分析**:

1. **親子関係の特定**:
   ```python
   import json

   # トレースファイルから親子関係を取得
   with open('data/scenarios/trace_550e8400-e29b-41d4-a716-446655440000.json') as f:
       trace = json.load(f)

   logical_uuid = trace['logical_uuid']
   abstract_uuid = trace['abstract_uuid']

   print(f"論理シナリオ {logical_uuid} は抽象シナリオ {abstract_uuid} から生成された")
   ```

2. **抽象シナリオの元データを参照**:
   ```python
   # 抽象シナリオファイルを読み込み
   abstract_file = trace['trace']['abstract_scenario_file']
   with open(abstract_file) as f:
       abstract = json.load(f)

   print(f"元の要件: {abstract['original_prompt']}")
   print(f"アクター: {[a['id'] for a in abstract['actors']]}")
   ```

3. **逆引き（抽象シナリオから派生した論理シナリオを探す）**:
   ```python
   import glob

   def find_logical_scenarios_by_abstract(abstract_uuid):
       """指定した抽象シナリオから生成された論理シナリオを全て探す"""
       logical_files = []
       for trace_file in glob.glob('data/scenarios/trace_*.json'):
           with open(trace_file) as f:
               trace = json.load(f)
               if trace['abstract_uuid'] == abstract_uuid:
                   logical_files.append(trace['logical_uuid'])
       return logical_files

   # 使用例
   derivatives = find_logical_scenarios_by_abstract('a1b2c3d4-e5f6-4789-a012-3456789abcde')
   print(f"抽象シナリオから派生した論理シナリオ: {derivatives}")
   ```

## 使用例

### 例1: 基本的な追従シナリオ

**ユーザー入力**:
```
シナリオ生成してください。高速道路で前方車両を追従するシナリオです。
```

**エージェントの動作**:
1. Phase 1: 抽象シナリオ生成（2台の車両、追従maneuver、UUID: `a1b2c3d4`）
2. Phase 2: 論理シナリオ生成（highway、初期位置・速度、UUID: `550e8400`、親: `a1b2c3d4`）
3. Phase 3: Python実装生成（`scenarios/550e8400.py`、論理シナリオUUID使用）
4. Phase 4: 実行（1回で成功）
5. Phase 5: トレース保存（階層関係を記録）

**出力ファイル構造**:
```
data/scenarios/
  ├── abstract_a1b2c3d4-e5f6-4789-a012-3456789abcde.json     # 抽象シナリオ
  ├── logical_550e8400-e29b-41d4-a716-446655440000.json      # 論理シナリオ（親: a1b2c3d4）
  └── trace_550e8400-e29b-41d4-a716-446655440000.json        # トレース（両UUID記録）

scenarios/
  └── 550e8400-e29b-41d4-a716-446655440000.py                # Python実装

data/rerun/
  └── 550e8400-e29b-41d4-a716-446655440000.rrd               # Rerunログ（オプション）

data/videos/
  └── 550e8400-e29b-41d4-a716-446655440000.mp4               # 動画（オプション）
```

**トレーサビリティ**:
- 論理シナリオファイルの`parent_abstract_uuid`を見れば元の抽象シナリオがわかる
- トレースファイルに両方のUUIDが記録され、ファイルパスも保存される

### 例2: 複数車両の合流シナリオ

**ユーザー入力**:
```
create scenario: 高速道路のランプから本線に合流するシナリオ。
車両は3台で、1台がランプから合流します。
```

**エージェントの動作**:
1. Phase 1: 抽象シナリオ生成（3台、合流maneuver）
2. Phase 2: 論理シナリオ生成（highway + ramp、初期位置）
3. Phase 3: Python実装生成
4. Phase 4: 実行（成功）
5. Phase 5: トレース保存

## MCPツールの使用（オプション）

このスキルは以下のMCPツールを使用できます:

- `generate_abstract_scenario(prompt: str)`: 抽象シナリオ生成
- `generate_logical_scenario(abstract: dict)`: 論理シナリオ生成
- `save_scenario_trace(trace: dict)`: トレース保存（オプション）
- `change_view(view: str)`: UI画面切り替え（UIがある場合）

## 関連スキル

- **carla-python-scenario**: CARLA Python API を使ったシナリオ記述
- **scenario-manager**: シナリオの管理・編集

## 注意事項

1. **CARLA接続の確認**
   - シナリオ実行前に、CARLAサーバーが`localhost:2000`で起動していることを確認
   - 起動していない場合はユーザーに通知

2. **リソース使用量**
   - .rrdファイルと.mp4ファイルは数百MBになる可能性がある
   - ディスク容量を確認

3. **同期モードの影響**
   - 同期モードではCARLAの実行速度がシミュレーションステップに依存
   - リアルタイムより遅くなる可能性がある

## トラブルシューティング

### CARLAに接続できない

- CARLAサーバーが起動しているか確認: `./CarlaUE4.sh`
- ポート2000が使用可能か確認

### スポーンに失敗する

- スポーンポイントが不足している可能性
- 別のマップを試す
- 既存の車両を削除してから再試行

### Blueprintが見つからない

- 利用可能な車両をリスト表示して確認
- フィルター条件を`'vehicle.*'`に変更して最初の車両を使用

### 動画生成に失敗する

- imageioがインストールされているか確認: `uv pip install imageio imageio-ffmpeg`
- カメラセンサーが正しく設定されているか確認

---

## imageioを使った動画記録

**Python実装での動画記録にはimageioを使用します**:

```python
import imageio
import numpy as np

# ビデオライター初期化
video_writer = imageio.get_writer(
    'data/videos/scenario.mp4',
    fps=20,
    codec='libx264',
    quality=8
)

# カメラコールバック
frames = []

def process_image(image):
    # CARLA imageをnumpy arrayに変換
    array = np.frombuffer(image.raw_data, dtype=np.uint8)
    array = array.reshape((image.height, image.width, 4))  # BGRA
    array = array[:, :, :3]  # BGRAからRGBに変換
    frames.append(array)

camera.listen(process_image)

# シナリオ実行後
for frame in frames:
    video_writer.append_data(frame)
video_writer.close()
```

---

**このスキルは包括的なシナリオ生成ワークフローを提供し、ユーザーの自然言語要件から実行可能なCARLAシナリオまでを自動化します。**
