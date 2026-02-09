---
name: pegasus-analyzer
description: This skill should be used when the user asks to "analyze scenario with PEGASUS", "apply PEGASUS 6 layers", "structure scenario requirements", "use 6 layer framework", or mentions "PEGASUS", "シナリオ分析", "6層", "要件整理". Analyzes natural language requirements using PEGASUS 6 Layer framework.
---

# PEGASUS Scenario Analyzer

**役割**: ユーザーの自然言語要件をPEGASUS 6 Layerの観点から分析し、シナリオに含まれる要素を整理・構造化する。

## トリガーワード

以下のキーワードが含まれる場合、このスキルを使用してください：
- "pegasus"
- "シナリオ分析"
- "6 layer"
- "6層"
- "シナリオ整理"
- "要件分析"

## PEGASUS 6 Layer とは

PEGASUS（Project for Establishing Generally Accepted Quality Criteria, Tools and Methods as well as Scenarios for the Safety Validation of Highly Automated Vehicles）は、自動運転車のシナリオベーステストのための標準的なフレームワークです。

### 6つのレイヤー

1. **Layer 1: Road-level（道路レベル）**
   - 道路タイプ（高速道路、市街地、郊外）
   - トポロジー（直線、カーブ、交差点、合流）
   - レーン数、レーン幅
   - 曲率、勾配、路面摩擦係数

2. **Layer 2: Traffic Infrastructure（交通インフラ）**
   - 信号機（状態、サイクル時間）
   - 交通標識（停止、速度制限、一方通行）
   - 路面標示（車線、停止線、横断歩道）
   - ガードレール、障壁

3. **Layer 3: Temporary Manipulation（一時的な変更）**
   - 工事
   - 事故
   - 道路封鎖、レーン閉鎖
   - 仮設標識

4. **Layer 4: Moving Objects（移動物体）**
   - 車両、歩行者、自転車
   - 初期状態（位置、速度、加速度）
   - マニューバー（レーン追従、車線変更、右左折、追い越し）
   - 自動運転車両の識別

5. **Layer 5: Environment Conditions（環境条件）**
   - 天候（晴れ、雨、雪、霧）
   - 時間帯（朝、昼、夜）
   - 路面状態（乾燥、湿潤、凍結）
   - 視程、気温

6. **Layer 6: Digital Information（デジタル情報）**
   - V2X通信（V2V, V2I, V2P）
   - HDマップ情報
   - センサー設定（カメラ、LiDAR、レーダー）
   - 自己位置推定精度

## 分析ワークフロー

### Phase 1: 要件の理解

ユーザーの自然言語要件を読み取り、シナリオの概要を把握します。

**例**:
```
ユーザー要件: "高速道路で前方車両が急ブレーキをかけるシナリオ"
```

### Phase 2: PEGASUS 6 Layer分析

各レイヤーの観点からシナリオを分析します。

#### Layer 1: 道路レベル

**分析項目**:
- どのような道路タイプか？（高速道路、市街地、郊外）
- トポロジーは？（直線、カーブ、交差点）
- レーン数は？
- 特殊な道路条件は？（曲率、勾配）

**例**:
```
Layer 1 分析結果:
- road_type: highway（高速道路）
- topology: straight（直線）
- num_lanes: 3（片側3車線）
- lane_width: 3.5m
- curvature: null（直線のため）
- elevation: 0%（平坦）
```

#### Layer 2: 交通インフラ

**分析項目**:
- 信号機は存在するか？
- 交通標識は？
- 路面標示は？
- その他のインフラは？

**例**:
```
Layer 2 分析結果:
- traffic_lights: []（高速道路のため信号機なし）
- traffic_signs: [speed_limit: "100km/h"]
- road_markings: [solid_line, dashed_line]
- barriers: [guardrail]
```

#### Layer 3: 一時的な変更

**分析項目**:
- 工事や事故などの一時的な状況変化はあるか？
- レーン閉鎖などの制約は？

**例**:
```
Layer 3 分析結果:
- manipulation: []（通常状態、変更なし）
```

#### Layer 4: 移動物体

**分析項目**:
- どのような物体が登場するか？
- 各物体の初期状態は？
- どのようなマニューバーを行うか？
- 自動運転車両はどれか？

**例**:
```
Layer 4 分析結果:
- objects:
  1. ego_vehicle（自動運転車両）
     - object_type: vehicle
     - initial_state:
       * velocity: 100 km/h (27.8 m/s)
       * lane_id: 2（中央レーン）
     - maneuver: follow_lane（レーン追従）
     - is_autonomous: true

  2. lead_vehicle（前方車両）
     - object_type: vehicle
     - initial_state:
       * velocity: 100 km/h
       * lane_id: 2
       * distance_ahead: 50m
     - maneuver: deceleration（急ブレーキ）
     - target_velocity: 0 km/h
     - is_autonomous: false
```

#### Layer 5: 環境条件

**分析項目**:
- 天候は？
- 時間帯は？
- 路面状態は？
- 視程や気温は？

**例**:
```
Layer 5 分析結果:
- weather: clear（晴れ）
- time_of_day: afternoon（午後）
- road_surface: dry（乾燥）
- visibility: 10km
- temperature: 25℃
```

#### Layer 6: デジタル情報

**分析項目**:
- V2X通信は使用されるか？
- HDマップは必要か？
- どのようなセンサーが必要か？

**例**:
```
Layer 6 分析結果:
- v2x_enabled: false（基本シナリオ、V2X不使用）
- hd_map: null（OpenDRIVEのみ）
- sensors:
  * camera（フロントカメラ）
  * radar（前方レーダー）
  * lidar（3D LiDAR）
- localization_accuracy: 0.1m
```

### Phase 3: パラメータの抽出

各レイヤーの分析結果から、可変パラメータを抽出します。

**パラメータリスト**:
```
ego_vehicle:
  - initial_speed: 80-120 km/h（一様分布）
  - distance_to_lead: 30-100m（一様分布）
  - reaction_time: 0.3-0.8s（正規分布、mean=0.5, std=0.1）

lead_vehicle:
  - initial_speed: 80-120 km/h
  - deceleration_rate: -8 to -12 m/s^2（急ブレーキ）
  - brake_trigger_time: 3-10s（シナリオ開始後）

environment:
  - weather: [clear, cloudy, rain]（選択肢）
  - time_of_day: [morning, noon, afternoon]（選択肢）
  - road_surface: [dry, wet]（選択肢）

camera:
  - offset_x: -6.0m（固定）
  - offset_z: 3.0m（固定）
  - pitch: -20deg（固定）
```

### Phase 4: Criticalityレベルの評価

シナリオの危険度を1-5のスケールで評価します。

**評価基準**:
- **Level 1**: 基本的なシナリオ（直線走行など）
- **Level 2**: 低リスクの相互作用（車線変更など）
- **Level 3**: 中程度のリスク（合流など）
- **Level 4**: 高リスク（急ブレーキ、カットイン）
- **Level 5**: 極めて高リスク（衝突回避など）

**例**:
```
Criticality Level: 4（高リスク）
理由: 前方車両の急ブレーキによる追突リスク
```

### Phase 5: 構造化されたシナリオ定義の出力

すべての分析結果を統合して、構造化されたシナリオ定義を出力します。

**出力フォーマット（Markdown）**:

````markdown
# PEGASUS Scenario Analysis

## シナリオ概要
- **名前**: 高速道路急ブレーキシナリオ
- **説明**: 高速道路で前方車両が急ブレーキをかけ、自動運転車両が反応する
- **Criticality Level**: 4（高リスク）

## Layer 1: Road-level
- **Road Type**: highway
- **Topology**: straight
- **Lanes**: 3
- **Lane Width**: 3.5m

## Layer 2: Traffic Infrastructure
- **Traffic Lights**: なし
- **Traffic Signs**: 速度制限100km/h
- **Road Markings**: 実線、破線

## Layer 3: Temporary Manipulation
- なし（通常状態）

## Layer 4: Moving Objects
### ego_vehicle（自動運転車両）
- **Type**: vehicle
- **Initial Velocity**: 100 km/h
- **Lane**: 2（中央）
- **Maneuver**: follow_lane → emergency_brake

### lead_vehicle（前方車両）
- **Type**: vehicle
- **Initial Velocity**: 100 km/h
- **Lane**: 2
- **Distance Ahead**: 50m
- **Maneuver**: deceleration（急ブレーキ）

## Layer 5: Environment Conditions
- **Weather**: clear
- **Time of Day**: afternoon
- **Road Surface**: dry
- **Visibility**: 10km

## Layer 6: Digital Information
- **V2X**: disabled
- **HD Map**: not required
- **Sensors**: camera, radar, lidar

## パラメータ空間
```python
ego_vehicle:
  initial_speed: uniform(80, 120) km/h
  distance_to_lead: uniform(30, 100) m
  reaction_time: normal(0.5, 0.1) s

lead_vehicle:
  initial_speed: uniform(80, 120) km/h
  deceleration_rate: uniform(-12, -8) m/s^2
  brake_trigger_time: uniform(3, 10) s

environment:
  weather: choice(["clear", "cloudy", "rain"])
  time_of_day: choice(["morning", "noon", "afternoon"])
  road_surface: choice(["dry", "wet"])
```

## 次のステップ
1. 論理シナリオの生成（パラメータ空間の定義）
2. CARLAマップの選択（Town04推奨）
3. Pythonスクリプトの実装
4. パラメータサンプリング
5. シミュレーション実行
````

## 使用例

### 例1: 交差点右折シナリオ

```
ユーザー: "市街地の交差点で右折するときに対向車が接近してくるシナリオを分析して"

Claude: PEGASUS 6 Layerに基づいて分析します。

【Layer 1: 道路レベル】
- road_type: urban（市街地）
- topology: junction（交差点、十字路）
- num_lanes: 2（片側2車線）
- lane_width: 3.0m

【Layer 2: 交通インフラ】
- traffic_lights: [信号機（青→黄→赤サイクル）]
- traffic_signs: [一時停止標識なし]
- road_markings: [停止線、右折レーン]

【Layer 3: 一時的な変更】
- なし

【Layer 4: 移動物体】
- ego_vehicle: 右折待ち → 右折実行
- oncoming_vehicle: 直進（対向車）
- initial_gap: 50-100m

【Layer 5: 環境条件】
- weather: clear
- time_of_day: noon
- road_surface: dry

【Layer 6: デジタル情報】
- v2x_enabled: false
- sensors: camera, lidar

【Criticality Level】: 4（高リスク - 衝突の可能性）

【パラメータ空間】
- ego_vehicle.turn_speed: 10-20 km/h
- oncoming_vehicle.speed: 40-60 km/h
- initial_gap: 50-100m
- traffic_light_state: choice(["green", "yellow"])
```

### 例2: 高速道路合流シナリオ

```
ユーザー: "高速道路の合流でメインレーンを走行中に加速レーンから車両が合流してくるシナリオ"

Claude: PEGASUS 6 Layerで分析します。

【Layer 1: 道路レベル】
- road_type: highway
- topology: merge（合流）
- num_lanes: 3 → 4（加速レーン含む）
- lane_width: 3.5m

【Layer 2: 交通インフラ】
- traffic_signs: [合流注意標識]
- road_markings: [破線（合流許可）]

【Layer 3: 一時的な変更】
- なし

【Layer 4: 移動物体】
- ego_vehicle: メインレーン走行
- merging_vehicle: 加速レーン → メインレーン合流
- initial_speed_ego: 100 km/h
- initial_speed_merging: 60-80 km/h

【Layer 5: 環境条件】
- weather: clear
- time_of_day: morning
- road_surface: dry

【Layer 6: デジタル情報】
- v2x_enabled: false

【Criticality Level】: 3（中リスク - 合流衝突）

【パラメータ空間】
- ego_vehicle.initial_speed: 90-110 km/h
- merging_vehicle.initial_speed: 60-80 km/h
- merging_vehicle.acceleration: 2-4 m/s^2
- lateral_distance_at_merge: 30-80m
```

## 重要な注意事項

1. **すべてのレイヤーを分析する**
   - 6つのレイヤーすべてについて、要件を明確化する
   - 情報が不足している場合は、合理的な仮定を置く

2. **パラメータの抽出**
   - 固定値と可変値を明確に区別する
   - 可変値には適切な分布を割り当てる

3. **Criticalityレベルの評価**
   - 客観的な基準で評価する
   - 衝突リスク、反応時間、速度差などを考慮

4. **CARLAマップとの対応**
   - 分析結果をCARLAマップにマッピングする
   - 適切なマップ（Town01-Town12）を推奨

5. **次のステップへの引き継ぎ**
   - 分析結果を`scenario-writer`スキルに引き継ぐ
   - 論理シナリオ、パラメータ空間の定義に活用

## 関連スキル

- **scenario-writer**: PEGASUS分析結果からシナリオ生成
- **scenario-manager**: シナリオ管理

## 参考文献

- ISO 34501: Road vehicles - Test scenarios for automated driving systems
- ISO 34502: Road vehicles - Test scenarios for automated driving systems - Scenario based safety evaluation framework
- PEGASUS Method: An Overview
