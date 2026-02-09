---
name: scenario-writer
description: This skill should be used when the user asks to "create scenario", "generate CARLA scenario", "build new scenario", "シナリオ生成", "シナリオ作成", "新しいシナリオ", or provides natural language scenario requirements. Automates full workflow from requirements through C++ implementation, build, and debugging.
---

# Scenario Writer Agent

**役割**: ユーザーの自然言語要件からCARLAシミュレーション用のシナリオを生成し、C++実装、ビルド、実行、デバッグまでを自動化する統合エージェント。

## 重要な制約事項

1. **すべての車両はCARLAのNPC**
   - 現時点では外部の自動運転スタックは統合されていない
   - 1台は「将来自動運転スタックを統合予定」のNPCとしてマーク（`is_autonomous_stack: true`）

2. **同期モードで実行**
   - 決定性を担保するため、CARLAは同期モード（`synchronous_mode=true`）で動作
   - 固定タイムステップ（`fixed_delta_seconds=0.05`）で20Hz実行

3. **スペクターカメラ配置**
   - 自動運転スタック予定NPCの運転席付近にスペクターカメラを配置
   - カメラ映像をmp4として記録

4. **ファイル命名規則**
   - 各シナリオはUUIDで識別
   - 出力ファイル: `{uuid}.rrd`（Rerunログ）、`{uuid}.mp4`（動画）
   - 設定ファイル: `{uuid}_config.json`（パラメータ）

5. **パラメータ化**
   - 具体的な位置、速度などのパラメータはJSONファイルで管理
   - バイナリ起動時に`--config {uuid}_config.json`で渡す

## ワークフロー

### Phase 1: 要件分析と抽象シナリオ生成

**目的**: ユーザーの自然言語要件を構造化された抽象シナリオに変換

**手順**:

1. **要件の受け取り**
   - ユーザーからの自然言語要件を確認
   - 例: "高速道路で前方車両を追従するシナリオ"

2. **不明点の確認**
   - `AskUserQuestion`ツールを使用して不明点を質問
   - 質問例:
     - 車両台数は？（デフォルト: 2台）
     - 追従距離は？（デフォルト: 20m）
     - シナリオの継続時間は？（デフォルト: 10秒）

3. **抽象シナリオの生成**
   - MCPツール`generate_abstract_scenario`を呼び出し
   - 生成内容:
     - `description`: シナリオの概要
     - `actors`: アクターのリスト（最低1台は`is_autonomous_stack: true`）
     - `maneuvers`: 操作・動作の列挙

4. **ユーザー確認**
   - 生成された抽象シナリオをユーザーに提示
   - 承認を得る

**出力例**:
```json
{
  "description": "高速道路で前方車両を20m間隔で追従するシナリオ",
  "actors": [
    {
      "id": "ego_vehicle",
      "role": "自動運転スタック予定",
      "type": "vehicle",
      "is_autonomous_stack": true
    },
    {
      "id": "lead_vehicle",
      "role": "前方車両",
      "type": "vehicle",
      "is_autonomous_stack": false
    }
  ],
  "maneuvers": [
    {
      "actor": "lead_vehicle",
      "action": "一定速度で走行",
      "duration": "10s"
    },
    {
      "actor": "ego_vehicle",
      "action": "前方車両を追従",
      "duration": "10s",
      "conditions": ["距離を20m維持"]
    }
  ]
}
```

### Phase 2: 論理シナリオ生成

**目的**: 抽象シナリオからOpenDRIVE非依存の論理シナリオを生成

**手順**:

1. **論理シナリオの生成**
   - MCPツール`generate_logical_scenario`を呼び出し
   - OpenDRIVE非依存の記述を作成:
     - `map_requirements`: 地図の要件（道路タイプ、レーン数など）
     - `initial_conditions`: 初期状態（symbolic location）
     - `events`: イベント列（時刻とアクション）

2. **ユーザー確認**
   - 生成された論理シナリオをユーザーに提示
   - 承認を得る

**出力例**:
```json
{
  "map_requirements": {
    "road_type": "highway",
    "lanes": 3,
    "length_min": 500
  },
  "initial_conditions": {
    "ego_vehicle": {
      "location": "highway_lane_2",
      "speed": 50.0,
      "distance_behind_lead": 20.0
    },
    "lead_vehicle": {
      "location": "highway_lane_2_front",
      "speed": 80.0
    }
  },
  "events": [
    {
      "time": 0.0,
      "type": "start_scenario"
    },
    {
      "time": 0.0,
      "type": "lead_vehicle_set_constant_speed",
      "speed": 80.0
    },
    {
      "time": 0.0,
      "type": "ego_vehicle_follow_lead",
      "target_distance": 20.0
    },
    {
      "time": 10.0,
      "type": "end_scenario"
    }
  ]
}
```

### Phase 3: C++実装生成（サブエージェント起動）

**目的**: 論理シナリオからCARLAのC++実装を生成

**手順**:

1. **サブエージェントの起動**
   - `Task`ツールで`general-purpose`サブエージェントを起動
   - タスク内容:
     ```
     以下の論理シナリオからCARLA C++実装を生成してください。

     論理シナリオ:
     {logical_scenario_json}

     要件:
     - carla-cpp-scenarioスキルを使用
     - rerun-carla-sdkスキルを使用
     - CARLA C++ API Referenceを参照
     - 同期モード設定（synchronous_mode=true, fixed_delta_seconds=0.05）
     - VideoRecorder統合（mp4記録）
     - ScenarioConfig::load()でJSONパラメータ読み込み
     - スペクターカメラを自動運転スタックNPC付近に配置
     - ファイル名: {uuid}.rrd, {uuid}.mp4
     - 出力先: /workspace/output/{uuid}.rrd, /workspace/output/{uuid}.mp4
     ```

2. **生成コードの確認**
   - サブエージェントが生成した`main.cpp`を確認
   - 以下が含まれていることを検証:
     - ✅ 同期モード設定
     - ✅ VideoRecorder統合
     - ✅ ScenarioConfig::load()
     - ✅ スペクターカメラ配置
     - ✅ Rerun初期化（ヘッドレスモード）
     - ✅ 適切なファイル名

3. **JSONパラメータファイルの生成**
   - 論理シナリオから具体的なパラメータを生成
   - `{uuid}_config.json`として保存
   - 内容例:
     ```json
     {
       "carla_host": "localhost",
       "carla_port": 2000,
       "carla_map": "Town04",
       "spawn_points": {
         "ego_vehicle": {
           "vehicle_type": "vehicle.tesla.model3",
           "x": 100.0,
           "y": 200.0,
           "z": 0.3,
           "yaw": 0.0,
           "is_autonomous_stack": true
         },
         "lead_vehicle": {
           "vehicle_type": "vehicle.audi.a2",
           "x": 120.0,
           "y": 200.0,
           "z": 0.3,
           "yaw": 0.0,
           "is_autonomous_stack": false
         }
       },
       "camera_config": {
         "offset_x": -5.0,
         "offset_y": 0.0,
         "offset_z": 2.5
       },
       "duration_steps": 200
     }
     ```

### Phase 4: ビルド・実行・デバッグループ

**目的**: C++コードをビルド・実行し、エラーを自動修正

**手順**:

1. **Sandbox起動**
   - MCPツール`launch_scenario_with_retry`を呼び出し
   - パラメータ:
     - `cpp_code`: 生成されたC++コード
     - `scenario_uuid`: シナリオのUUID
     - `max_retries`: 最大リトライ回数（デフォルト: 5）

2. **ビルド・実行サイクル**
   - `sandbox/src/main.cpp`にコードを書き込み
   - `sandbox/workspace/{uuid}/config.json`にパラメータを保存
   - CMakeでビルド実行
   - エラー検出:
     - コンパイルエラー: エラーメッセージ解析→修正
     - リンクエラー: 依存関係確認→修正
     - ランタイムエラー: CARLA接続確認→修正

3. **自動修正ロジック**
   - エラーの種類に応じた修正を適用:
     - `undefined reference`: ライブラリ不足 → `CMakeLists.txt`修正
     - `no matching function`: API不一致 → CARLA API Reference参照
     - `connection refused`: CARLA未起動 → ユーザーに通知
   - 修正後、再度ビルド

4. **最大リトライ回数に達した場合**
   - ビルドエラーの履歴をユーザーに提示
   - 人間の介入を依頼

5. **成功時**
   - `.rrd`ファイルの存在確認
   - `.mp4`ファイルの存在確認
   - ファイルサイズが0でないことを確認

### Phase 5: トレース保存

**目的**: 抽象→論理→実装の階層関係をJSONに保存

**手順**:

1. **トレース情報の作成**
   - `ScenarioTrace`モデルを構築:
     - `id`: シナリオUUID
     - `name`: シナリオ名
     - `description`: 概要
     - `trace.original_prompt`: ユーザーの元の要件
     - `trace.abstract_scenario`: Phase 1の出力
     - `trace.logical_scenario`: Phase 2の出力
     - `trace.concrete_scenario`: JSONパラメータ
     - `trace.implementation`: ビルド情報（試行回数、エラー、最終ステータス）
   - `sandbox_uuid`: UUIDを記録
   - `rerun_file`: .rrdファイルパス
   - `video_file`: .mp4ファイルパス
   - `config_file`: JSONパラメータファイルパス

2. **保存**
   - MCPツール`save_scenario_trace`を呼び出し
   - `data/scenarios/{scenario_id}.json`に保存

3. **UI表示**
   - MCPツール`change_view`で画面を切り替え
   - `scenario_list`または`scenario_analysis`を表示
   - ユーザーにシナリオが生成されたことを通知

**トレースファイル例**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "高速道路追従シナリオ",
  "description": "前方車両を20m間隔で追従するシナリオ",
  "created_at": "2026-02-06T14:30:00Z",
  "trace": {
    "original_prompt": "高速道路で前方車両を追従するシナリオ",
    "generated_at": "2026-02-06T14:30:00Z",
    "agent_version": "1.0.0",
    "abstract_scenario": { /* Phase 1の出力 */ },
    "logical_scenario": { /* Phase 2の出力 */ },
    "concrete_scenario": { /* JSONパラメータ */ },
    "implementation": {
      "cpp_file": "sandbox/src/main.cpp",
      "build_attempts": 2,
      "build_errors": [
        {
          "attempt": 1,
          "error": "undefined reference to `cv::VideoWriter::write'",
          "fix": "Added OpenCV library to CMakeLists.txt"
        }
      ],
      "final_status": "success"
    }
  },
  "sandbox_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "rerun_file": "sandbox/workspace/550e8400-e29b-41d4-a716-446655440000/output/550e8400-e29b-41d4-a716-446655440000.rrd",
  "video_file": "sandbox/workspace/550e8400-e29b-41d4-a716-446655440000/output/550e8400-e29b-41d4-a716-446655440000.mp4",
  "config_file": "sandbox/workspace/550e8400-e29b-41d4-a716-446655440000/550e8400-e29b-41d4-a716-446655440000_config.json"
}
```

## 使用例

### 例1: 基本的な追従シナリオ

**ユーザー入力**:
```
シナリオ生成してください。高速道路で前方車両を追従するシナリオです。
```

**エージェントの動作**:
1. Phase 1: 抽象シナリオ生成（2台の車両、追従maneuver）
2. Phase 2: 論理シナリオ生成（highway、初期位置・速度）
3. Phase 3: サブエージェントがC++実装生成
4. Phase 4: ビルド・実行（1回で成功）
5. Phase 5: トレース保存、UI表示

**出力**:
- `data/scenarios/{uuid}.json`: トレースファイル
- `sandbox/workspace/{uuid}/output/{uuid}.rrd`: Rerunログ
- `sandbox/workspace/{uuid}/output/{uuid}.mp4`: 動画

### 例2: 複数車両の合流シナリオ

**ユーザー入力**:
```
create scenario: 高速道路のランプから本線に合流するシナリオ。
車両は3台で、1台がランプから合流します。
```

**エージェントの動作**:
1. Phase 1: 抽象シナリオ生成（3台、合流maneuver）
2. Phase 2: 論理シナリオ生成（highway + ramp、初期位置）
3. Phase 3: C++実装生成
4. Phase 4: ビルドエラー（1回）→ 自動修正 → 成功
5. Phase 5: トレース保存

## MCPツールの使用

このスキルは以下のMCPツールを使用します:

- `generate_abstract_scenario(prompt: str)`: 抽象シナリオ生成
- `generate_logical_scenario(abstract: dict)`: 論理シナリオ生成
- `launch_scenario_with_retry(cpp_code: str, scenario_uuid: str, max_retries: int)`: ビルド・実行
- `save_scenario_trace(trace: dict)`: トレース保存
- `change_view(view: str)`: UI画面切り替え

## 関連スキル

- **carla-cpp-scenario**: CARLA C++ API を使ったシナリオ記述
- **rerun-carla-sdk**: Rerun可視化とログ記録
- **scenario-manager**: シナリオの管理・編集

## 注意事項

1. **CARLA接続の確認**
   - シナリオ実行前に、CARLAサーバーが`localhost:2000`で起動していることを確認
   - 起動していない場合はユーザーに通知

2. **ビルド時間**
   - C++コードのビルドには数分かかる場合がある
   - ユーザーに進捗を適宜報告

3. **リソース使用量**
   - .rrdファイルと.mp4ファイルは数百MBになる可能性がある
   - ディスク容量を確認

4. **同期モードの影響**
   - 同期モードではCARLAの実行速度がシミュレーションステップに依存
   - リアルタイムより遅くなる可能性がある

## トラブルシューティング

### ビルドエラーが解決しない

- 最大リトライ回数（5回）に達した場合、エラーログを提示
- ユーザーに手動修正を依頼

### .rrdファイルが生成されない

- Rerunの初期化に失敗している可能性
- ログを確認し、`rerun_carla_sdk`の使用方法を再確認

### .mp4ファイルが生成されない

- VideoRecorderの初期化に失敗している可能性
- OpenCV依存関係を確認

### CARLAに接続できない

- CARLAサーバーが起動しているか確認
- ポート2000が使用可能か確認

---

**このスキルは包括的なシナリオ生成ワークフローを提供し、ユーザーの自然言語要件から実行可能なCARLAシナリオまでを自動化します。**
