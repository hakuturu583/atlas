# agent_controller - CARLA Traffic Manager Wrapper

CARLA Traffic Managerをラップし、高レベルAPIを提供するパッケージです。
テストケースでよくあるシナリオを簡単に記述でき、STAMP状態遷移ロガーとユーザー指示追跡機能を統合しています。

## 📋 特徴

- **統合API**: CARLAクライアント接続、Traffic Manager、ロギング機能を単一クラスで管理
- **自動接続管理**: CARLAサーバーへの接続、リトライ、生存確認を自動化
- **高レベルAPI**: レーンチェンジ、カットイン、タイミング突入などの振る舞いを簡単に記述
- **STAMPロギング**: STAMP理論に基づいた状態遷移とcontrol actionを記録
- **指示追跡**: ユーザーからの指示の完遂状態を記録
- **安全性メトリクス**: TTC、急ブレーキ、急加速などの自動運転評価指標を自動計算 🆕
- **意味論的カバレッジ**: イベント発生有無に基づくカバレッジ計測 🆕
- **Traffic Manager統合**: CARLA Traffic Managerの機能をすべて利用可能
- **将来のカバレッジ計測**: NPCロジックを統一し、カバレッジ計測の基盤を提供

## 🏗️ アーキテクチャ

```
agent_controller/
├── __init__.py                     # パッケージエントリポイント
├── controller.py                   # 統合コントローラ（推奨）
├── traffic_manager_wrapper.py     # Traffic Managerラッパー
├── behaviors.py                    # 高レベル振る舞い
├── stamp_logger.py                 # STAMP状態遷移ロガー
├── command_tracker.py              # ユーザー指示追跡
└── README.md                       # このファイル
```

## 🚀 使い方

### 推奨: トリガー関数ベース（最もシンプル＆拡張性が高い）🆕

トリガー関数を使うと、world.tick()やフレーム管理が不要になり、シナリオを宣言的に記述できます。

```python
from agent_controller import AgentController, VehicleConfig, CAUTIOUS_DRIVER
from opendrive_utils import LaneCoord

with AgentController(scenario_uuid="my_scenario") as controller:
    # 車両設定を定義
    ego_config = VehicleConfig(
        auto_lane_change=False,
        distance_to_leading=5.0,
        speed_percentage=80.0,
    )

    # 車両をスポーン（自動登録）
    lane_coord_1 = LaneCoord(road_id=10, lane_id=-1, s=50.0)
    ego_vehicle, ego_id = controller.spawn_vehicle_from_lane(
        "vehicle.tesla.model3",
        lane_coord_1,
        config=ego_config,
    )

    # プリセットを使ってNPC車両をスポーン
    lane_coord_2 = LaneCoord(road_id=10, lane_id=-1, s=80.0)
    npc_vehicle, npc_id = controller.spawn_vehicle_from_lane(
        "vehicle.tesla.model3",
        lane_coord_2,
        config=CAUTIOUS_DRIVER,  # 慎重なドライバー
    )

    # トリガー関数でシナリオを定義（フレーム管理不要！）
    controller.register_callback(
        controller.when_timestep_equals(100),
        lambda: controller.lane_change(ego_id, direction="left")
    )

    controller.register_callback(
        controller.when_timestep_equals(200),
        lambda: controller.cut_in(ego_id, target_vehicle_id=npc_id)
    )

    controller.register_callback(
        controller.when_timestep_equals(350),
        lambda: controller.follow(ego_id, target_vehicle_id=npc_id)
    )

    controller.register_callback(
        controller.when_timestep_equals(550),
        lambda: controller.stop(ego_id)
    )

    # 高度なトリガー: 車両間距離が10m以下になったら警告
    controller.register_callback(
        controller.when_distance_between(ego_id, npc_id, 10.0, operator="less"),
        lambda: print("⚠ Too close!"),
        one_shot=False  # リピート実行
    )

    # シミュレーション実行（world.tick()は自動呼び出し）
    controller.run_simulation(total_frames=600)

    # 車両は自動的に破棄される（明示的な破棄は不要）

# コンテキストマネージャを抜けると自動的に:
# - スポーンした車両が破棄される
# - ログがファイナライズ・保存される
# - 同期モードが元に戻される
```

### パターン2: on_tickコールバック🆕

毎フレーム実行されるコールバックを使う方法：

```python
with AgentController(scenario_uuid="my_scenario") as controller:
    # 車両をスポーン・登録
    ego_id = controller.register_vehicle(vehicle)
    npc_id = controller.register_vehicle(npc_vehicle)

    # 毎フレーム呼ばれるコールバック
    def on_tick(frame: int):
        if frame == 100:
            controller.lane_change(ego_id, direction="left")
        elif frame == 200:
            controller.cut_in(ego_id, target_vehicle_id=npc_id)
        elif frame == 350:
            controller.follow(ego_id, target_vehicle_id=npc_id)
        elif frame == 550:
            controller.stop(ego_id)

    # シミュレーション実行
    controller.run_simulation(total_frames=600, on_tick=on_tick)
```

### パターン3: 手動でworld.tick()を呼ぶ（従来の方法）

```python
with AgentController(scenario_uuid="my_scenario") as controller:
    world = controller.world

    # 車両を登録
    ego_id = controller.register_vehicle(vehicle)

    # 手動でフレーム管理
    frame = 0
    for i in range(100):
        world.tick()
        frame += 1

    # レーンチェンジ
    result = controller.lane_change(
        vehicle_id=ego_id,
        frame=frame,
        direction="left",
        duration_frames=100,
    )

    for i in range(100):
        world.tick()
        frame += 1

    # ... 以下同様
```

### 低レベルAPI: TrafficManagerWrapperを直接使う（上級者向け）

低レベルAPIを使うと、より細かい制御が可能ですが、コードが複雑になります。

```python
import carla
from agent_controller import (
    TrafficManagerWrapper,
    STAMPLogger,
    CommandTracker,
    LaneChangeBehavior,
)

# 手動でCARLA接続
client = carla.Client("localhost", 2000)
client.set_timeout(10.0)
world = client.get_world()

# ロガー初期化
stamp_logger = STAMPLogger(scenario_uuid="my_scenario")
command_tracker = CommandTracker(scenario_uuid="my_scenario")

# Traffic Manager Wrapper初期化
tm_wrapper = TrafficManagerWrapper(
    client=client,
    port=8000,
    stamp_logger=stamp_logger,
    command_tracker=command_tracker,
)

# 車両登録と振る舞い実行
# ...

# 手動でクリーンアップ
stamp_logger.finalize()
command_tracker.finalize()
tm_wrapper.cleanup()
```

## 📚 API リファレンス

### VehicleConfig（車両設定）🆕

車両のTraffic Manager設定をまとめたデータクラス。型安全で読みやすいコードを実現します。

```python
from agent_controller import VehicleConfig

# カスタム設定
config = VehicleConfig(
    auto_lane_change=False,      # 自動レーンチェンジ
    distance_to_leading=5.0,     # 前方車両との距離（m）
    speed_percentage=80.0,       # 制限速度に対する速度（%）
    ignore_lights=False,         # 信号無視
    ignore_vehicles=False,       # 他車両無視
    ignore_signs=False,          # 標識無視
)

vehicle, vehicle_id = controller.spawn_vehicle_from_lane(
    "vehicle.tesla.model3",
    lane_coord,
    config=config
)
```

#### プリセット設定

よく使われる設定がプリセットとして用意されています：

- `NORMAL_DRIVER` - 通常のドライバー（デフォルト設定）
- `CAUTIOUS_DRIVER` - 慎重なドライバー（車間距離が長く、速度が遅い）
- `AGGRESSIVE_DRIVER` - アグレッシブなドライバー（車間距離が短く、速度が速い）
- `RECKLESS_DRIVER` - 無謀なドライバー（すべての交通ルールを無視）

```python
from agent_controller import CAUTIOUS_DRIVER, AGGRESSIVE_DRIVER

# プリセットを使用
cautious_vehicle, _ = controller.spawn_vehicle_from_lane(
    "vehicle.tesla.model3",
    lane_coord,
    config=CAUTIOUS_DRIVER
)

aggressive_vehicle, _ = controller.spawn_vehicle_from_lane(
    "vehicle.audi.a2",
    lane_coord,
    config=AGGRESSIVE_DRIVER
)
```

### MetricsConfig（メトリクス設定）🆕

安全性メトリクスの計算設定をまとめたデータクラス。自動運転システムの評価指標を自動計算し、ログファイルに保存します。

```python
from agent_controller import AgentController
from agent_controller.metrics import MetricsConfig

# カスタムメトリクス設定
metrics_config = MetricsConfig(
    ttc_threshold=3.0,                    # TTC閾値（秒）
    sudden_braking_threshold=5.0,         # 急ブレーキ閾値（m/s²）
    sudden_acceleration_threshold=4.0,    # 急加速閾値（m/s²）
    lateral_acceleration_threshold=3.0,   # 横方向加速度閾値（m/s²）
    jerk_threshold=10.0,                  # ジャーク閾値（m/s³）
    min_distance_threshold=2.0,           # 最小車間距離閾値（m）
    speed_violation_margin=10.0,          # 速度違反マージン（km/h）
)

# メトリクス計算を有効化
with AgentController(
    scenario_uuid="my_scenario",
    enable_metrics=True,           # メトリクス有効化
    metrics_config=metrics_config, # カスタム設定
) as controller:
    # シナリオ実行...
    controller.run_simulation(total_frames=600)

# コンテキストマネージャを抜けると自動的に:
# - メトリクスログが data/logs/metrics/ に保存される
# - STAMPログが data/logs/stamp/ に保存される
# - コマンドログが data/logs/commands/ に保存される
```

#### 計算されるメトリクス

以下の安全性メトリクスが自動的に計算されます：

- **TTC (Time To Collision)**: 前方車両への衝突時間（秒）
- **急ブレーキ (Sudden Braking)**: 減速度が閾値を超えた場合（m/s²）
- **急加速 (Sudden Acceleration)**: 加速度が閾値を超えた場合（m/s²）
- **横方向加速度 (Lateral Acceleration)**: レーンチェンジ時の横加速度（m/s²）
- **ジャーク (Jerk)**: 加速度の変化率（m/s³）
- **最小車間距離 (Minimum Distance)**: 前方車両との最小距離（m）
- **速度違反 (Speed Violation)**: 制限速度超過（km/h）

#### メトリクスの出力

メトリクスは`data/logs/metrics/`に保存されます：

```json
{
  "scenario_uuid": "my_scenario",
  "config": {...},
  "summary": {
    "total_events": 12,
    "event_counts": {
      "sudden_braking": 3,
      "low_ttc": 5,
      "sudden_acceleration": 2,
      "high_jerk": 2
    },
    "min_ttc_per_vehicle": {
      "42": 2.1,
      "43": 2.8
    },
    "min_distances": {
      "42": 1.5,
      "43": 2.3
    }
  },
  "events": [
    {
      "frame": 150,
      "timestamp": 1234567890.0,
      "event_type": "sudden_braking",
      "vehicle_id": 42,
      "value": 6.2,
      "threshold": 5.0,
      "description": "急ブレーキ検出: 6.20 m/s²",
      "location": [100.5, 50.2, 0.3]
    }
  ]
}
```

### AgentController（推奨）

統合コントローラークラス。CARLAクライアント接続、Traffic Manager、ロギング機能を統合。

#### 初期化

```python
AgentController(
    scenario_uuid: str,
    client: Optional[carla.Client] = None,  # Noneの場合は自動接続
    carla_host: str = "localhost",
    carla_port: int = 2000,
    carla_timeout: float = 10.0,
    tm_port: int = 8000,
    enable_logging: bool = True,
    synchronous_mode: bool = True,
    fixed_delta_seconds: float = 0.05,
    max_retries: int = 3,              # 🆕 接続失敗時の最大リトライ回数
    retry_delay: float = 2.0,          # 🆕 リトライ間の待機時間（秒）
)
```

#### 接続管理メソッド（🆕）

- `check_connection() -> bool` - CARLAサーバーへの接続が有効か確認
- `is_alive() -> bool` - CARLAサーバーが生きているか確認（エイリアス）
- `reconnect() -> bool` - CARLAサーバーに再接続（自動接続時のみ）

```python
# 接続確認
if controller.is_alive():
    print("✓ Server is alive")

# 接続が切れた場合の再接続
if not controller.check_connection():
    print("Connection lost. Reconnecting...")
    if controller.reconnect():
        print("✓ Reconnected successfully")
```

#### 車両スポーンとブループリント（🆕）

- `get_blueprint_library() -> carla.BlueprintLibrary` - ブループリントライブラリを取得
- `get_map() -> carla.Map` - CARLAマップを取得
- `spawn_vehicle(blueprint_name, transform, auto_register, auto_destroy, config, **kwargs) -> (Vehicle, int)` - 車両をスポーン
- `spawn_vehicle_from_lane(blueprint_name, lane_coord, auto_register, auto_destroy, config, **kwargs) -> (Vehicle, int)` - レーン座標から車両をスポーン
- `destroy_vehicle(vehicle_id) -> bool` - 車両を破棄（通常は不要、自動破棄される）

```python
# パターン1: VehicleConfigを使用（推奨）
from opendrive_utils import LaneCoord
from agent_controller import VehicleConfig

config = VehicleConfig(
    auto_lane_change=False,
    distance_to_leading=5.0,
    speed_percentage=80.0,
)

lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
vehicle, vehicle_id = controller.spawn_vehicle_from_lane(
    "vehicle.tesla.model3",
    lane_coord,
    config=config,
    auto_register=True,   # 自動的にTraffic Managerに登録
    auto_destroy=True,    # デストラクタで自動破棄（デフォルト）
)

# パターン2: プリセットを使用
from agent_controller import CAUTIOUS_DRIVER

vehicle, vehicle_id = controller.spawn_vehicle_from_lane(
    "vehicle.tesla.model3",
    lane_coord,
    config=CAUTIOUS_DRIVER,
)

# パターン3: キーワード引数を使用（後方互換性）
vehicle, vehicle_id = controller.spawn_vehicle_from_lane(
    "vehicle.tesla.model3",
    lane_coord,
    speed_percentage=80.0,
    auto_lane_change=False,
)

# 車両を破棄（通常は不要、with文を抜けると自動破棄される）
controller.destroy_vehicle(vehicle_id)
```

**重要**:
- `auto_destroy=True`（デフォルト）の場合、コンテキストマネージャを抜けると自動的に車両が破棄されます。
- VehicleConfigを使うことで型安全で読みやすいコードになります（推奨）。

#### 車両登録・管理メソッド

- `register_vehicle(vehicle, **config) -> int` - 車両を登録（低レベルAPI）
- `get_vehicle(vehicle_id) -> carla.Vehicle` - 車両アクターを取得
- `get_vehicle_config(vehicle_id) -> Dict` - 車両設定を取得
- `get_all_vehicles() -> list[int]` - 登録されているすべての車両IDを取得

#### トリガー関数（条件判定）🆕

トリガー関数は、条件が満たされたときにTrueを返す関数を生成します。

**タイムステップベース:**
- `when_timestep_equals(frame)` - 特定フレームに到達
- `when_timestep_greater_than(frame)` - フレームが指定値を超える

**位置ベース:**
- `when_vehicle_at_location(vehicle_id, location, threshold)` - 車両が位置に到達

**距離ベース:**
- `when_distance_between(vehicle_id1, vehicle_id2, distance, operator)` - 車両間距離が条件を満たす
  - operator: "less", "greater", "equal"

**速度ベース:**
- `when_speed_greater_than(vehicle_id, speed)` - 速度が閾値を超える
- `when_speed_less_than(vehicle_id, speed)` - 速度が閾値を下回る

```python
# 特定フレームで実行
controller.register_callback(
    controller.when_timestep_equals(100),
    lambda: controller.lane_change(ego_id, direction="left")
)

# 車両が位置に到達したら実行
controller.register_callback(
    controller.when_vehicle_at_location(ego_id, target_location, threshold=5.0),
    lambda: print("Target reached!")
)

# 車両間距離が条件を満たしたら実行（リピート）
controller.register_callback(
    controller.when_distance_between(ego_id, npc_id, 10.0, operator="less"),
    lambda: print("⚠ Too close!"),
    one_shot=False  # 継続的に監視
)

# 速度が閾値を超えたら実行
controller.register_callback(
    controller.when_speed_greater_than(ego_id, 80.0),
    lambda: print("⚠ Speeding!")
)
```

#### シミュレーションループとコールバック（🆕）

- `run_simulation(total_frames, on_tick)` - シミュレーション実行（world.tick()を自動呼び出し）
- `register_callback(trigger, callback, one_shot)` - トリガー条件でコールバックを登録
- `set_tick_callback(callback)` - 毎フレーム実行されるコールバックを設定
- `current_frame` - 現在のフレーム番号（プロパティ）
- `tick(frames)` - 手動でWorld更新を実行（低レベルAPI）

```python
# パターン1: トリガー関数を使用（推奨）
controller.register_callback(
    controller.when_timestep_equals(100),
    lambda: controller.lane_change(ego_id, direction="left")
)
controller.run_simulation(total_frames=500)

# パターン2: on_tickコールバックを使用
def on_tick(frame):
    if frame == 100:
        controller.lane_change(ego_id, direction="left")

controller.run_simulation(total_frames=500, on_tick=on_tick)
```

#### 高レベル振る舞いメソッド

**重要**: frameパラメータは省略可能になりました（Noneの場合は現在のフレームを使用）。

- `lane_change(vehicle_id, frame=None, direction, duration_frames)` - レーンチェンジ
- `cut_in(vehicle_id, frame=None, target_vehicle_id, gap_distance, speed_boost)` - カットイン
- `timed_approach(vehicle_id, frame=None, target_location, target_time, ...)` - タイミング突入
- `follow(vehicle_id, frame=None, target_vehicle_id, distance, duration_frames)` - 追従
- `stop(vehicle_id, frame=None, duration_frames)` - 停止

#### 低レベルTraffic Manager設定メソッド

- `set_auto_lane_change(vehicle_id, enable, frame)` - 自動レーンチェンジ設定
- `force_lane_change(vehicle_id, direction, frame)` - 強制レーンチェンジ
- `set_distance_to_leading(vehicle_id, distance, frame)` - 前方車両との距離設定
- `set_speed_percentage(vehicle_id, percentage, frame)` - 速度設定
- `ignore_lights(vehicle_id, ignore, frame)` - 信号無視設定
- `ignore_vehicles(vehicle_id, ignore, frame)` - 他車両無視設定

#### ロギングメソッド

- `log_state_transition(...)` - 状態遷移を記録（手動ロギング用）
- `log_control_action(...)` - 制御アクションを記録（手動ロギング用）
- `get_vehicle_state(vehicle_id) -> StateType` - 車両の現在状態を取得

#### クリーンアップメソッド

- `finalize() -> tuple[str, str]` - ログをファイナライズして保存（返り値: STAMPログパス、コマンドログパス）
- `cleanup()` - クリーンアップ（車両のautopilot解除、設定の復元）

#### コンテキストマネージャ

`with`文を使うことで、自動的にクリーンアップが実行されます（推奨）。

```python
with AgentController(scenario_uuid="my_scenario") as controller:
    # ... 処理 ...
    pass
# 自動的にfinalize()とcleanup()が実行される
```

### TrafficManagerWrapper（低レベルAPI）

Traffic Managerの基本機能をラップします。

#### メソッド

- `register_vehicle(vehicle, **config)` - 車両を登録
- `set_auto_lane_change(vehicle_id, enable)` - 自動レーンチェンジ設定
- `force_lane_change(vehicle_id, direction)` - 強制レーンチェンジ
- `set_distance_to_leading(vehicle_id, distance)` - 前方車両との距離設定
- `set_speed_percentage(vehicle_id, percentage)` - 速度設定
- `ignore_lights(vehicle_id, ignore)` - 信号無視設定
- `ignore_vehicles(vehicle_id, ignore)` - 他車両無視設定

### Behaviors

高レベルな振る舞いを提供します。

#### LaneChangeBehavior

レーンチェンジを実行します。

```python
lane_change = LaneChangeBehavior(tm_wrapper)
result = lane_change.execute(
    vehicle_id=vehicle_id,
    frame=100,
    direction="left",  # or "right"
    duration_frames=100,
)
```

#### CutInBehavior

カットインを実行します。

```python
cut_in = CutInBehavior(tm_wrapper)
result = cut_in.execute(
    vehicle_id=vehicle_id,
    frame=100,
    target_vehicle_id=other_vehicle_id,
    gap_distance=3.0,
    speed_boost=120.0,
)
```

#### TimedApproachBehavior

タイミングを合わせて特定地点に突入します。

```python
timed_approach = TimedApproachBehavior(tm_wrapper)
result = timed_approach.execute(
    vehicle_id=vehicle_id,
    frame=100,
    target_location=carla.Location(x=100.0, y=50.0, z=0.5),
    target_time=5.0,  # 5秒で到達
    speed_adjustment=1.2,
    ignore_traffic=True,
)
```

#### FollowBehavior

指定車両を追従します。

```python
follow = FollowBehavior(tm_wrapper)
result = follow.execute(
    vehicle_id=vehicle_id,
    frame=100,
    target_vehicle_id=lead_vehicle_id,
    distance=5.0,
    duration_frames=200,
)
```

#### StopBehavior

車両を停止します。

```python
stop = StopBehavior(tm_wrapper)
result = stop.execute(
    vehicle_id=vehicle_id,
    frame=100,
    duration_frames=50,
)
```

### STAMPLogger

STAMP理論に基づいた状態遷移ロガーです。

#### メソッド

- `log_state_transition(frame, vehicle_id, to_state, ...)` - 状態遷移を記録
- `log_control_action(frame, vehicle_id, action, ...)` - 制御アクションを記録
- `get_vehicle_state(vehicle_id)` - 車両の現在状態を取得
- `finalize()` - ログをファイルに保存
- `print_summary()` - サマリーを出力

#### 出力形式

```json
{
  "scenario_uuid": "uuid-123",
  "start_time": "2025-01-01T12:00:00",
  "end_time": "2025-01-01T12:05:00",
  "duration_seconds": 300.0,
  "state_transitions": [
    {
      "timestamp": 1234567890.0,
      "frame": 100,
      "vehicle_id": 42,
      "from_state": "idle",
      "to_state": "driving",
      "control_action": "accelerate",
      "location": {"x": 100.0, "y": 50.0, "z": 0.5},
      "rotation": {"pitch": 0.0, "yaw": 90.0, "roll": 0.0},
      "velocity": {"x": 5.0, "y": 0.0, "z": 0.0},
      "metadata": {}
    }
  ],
  "control_actions": [...],
  "summary": {
    "total_transitions": 10,
    "total_actions": 5,
    "vehicles": [42, 43]
  }
}
```

### CommandTracker

ユーザー指示の追跡と完遂記録を行います。

#### メソッド

- `create_command(description, ...)` - 新しい指示を作成
- `start_command(command_id, ...)` - 指示の実行を開始
- `complete_command(command_id, ...)` - 指示を完了
- `cancel_command(command_id, ...)` - 指示をキャンセル
- `update_metrics(command_id, metrics)` - メトリクスを更新
- `get_command(command_id)` - 指示を取得
- `get_pending_commands()` - 実行待ち指示を取得
- `finalize()` - ログをファイルに保存
- `print_summary()` - サマリーを出力

#### 出力形式

```json
{
  "scenario_uuid": "uuid-123",
  "start_time": "2025-01-01T12:00:00",
  "end_time": "2025-01-01T12:05:00",
  "commands": [
    {
      "command_id": "cmd_0001",
      "description": "Lane change to left",
      "status": "completed",
      "created_at": 1234567890.0,
      "started_at": 1234567891.0,
      "completed_at": 1234567895.0,
      "vehicle_id": 42,
      "behavior_type": "lane_change",
      "parameters": {"direction": "left", "duration_frames": 100},
      "success": true,
      "error_message": null,
      "metrics": {
        "duration_seconds": 4.0,
        "duration_frames": 80,
        "distance_traveled": 50.0
      },
      "frame_start": 100,
      "frame_end": 180,
      "location_start": {"x": 100.0, "y": 50.0, "z": 0.5},
      "location_end": {"x": 150.0, "y": 53.5, "z": 0.5}
    }
  ],
  "summary": {
    "total_commands": 5,
    "completed": 4,
    "failed": 1,
    "success_rate": 0.8
  }
}
```

## 🔧 拡張方法

### 新しい振る舞いの追加

`Behavior`クラスを継承して新しい振る舞いを追加できます：

```python
from agent_controller.behaviors import Behavior, BehaviorResult

class MyCustomBehavior(Behavior):
    """カスタム振る舞い"""

    def execute(self, vehicle_id: int, frame: int, **kwargs) -> BehaviorResult:
        """
        カスタム振る舞いを実行

        Args:
            vehicle_id: 車両ID
            frame: 現在のフレーム番号
            **kwargs: 追加パラメータ

        Returns:
            実行結果
        """
        start_location = self._get_vehicle_location(vehicle_id)
        start_frame = frame

        # コマンド作成
        command_id = self._create_command(
            description="My custom behavior",
            vehicle_id=vehicle_id,
            behavior_type="custom",
            **kwargs,
        )
        self._start_command(command_id, frame, start_location)

        # STAMP状態遷移ログ
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=frame,
                vehicle_id=vehicle_id,
                to_state=StateType.DRIVING,
                control_action=ControlAction.ACCELERATE,
            )

        # 振る舞いの実装
        # ...

        # 完了
        end_frame = frame + 100
        end_location = self._get_vehicle_location(vehicle_id)

        metrics = {"my_metric": 42}

        # コマンド完了
        self._complete_command(
            command_id=command_id,
            success=True,
            frame=end_frame,
            location=end_location,
            metrics=metrics,
        )

        return BehaviorResult(
            success=True,
            message="Custom behavior completed",
            metrics=metrics,
            start_frame=start_frame,
            end_frame=end_frame,
            start_location=start_location,
            end_location=end_location,
        )
```

### 機能不足時の対応

agent_controllerパッケージに必要な機能が不足している場合：

1. **Issue作成**: GitHubに機能リクエストのIssueを作成
2. **実装**: 新しい振る舞いやTraffic Manager機能を実装
3. **テスト**: 動作確認とテストコード作成
4. **PR作成**: Pull Requestを作成して提出

#### PRの推奨構成

```
agent_controller/
├── behaviors.py              # 新しい振る舞いを追加
└── tests/
    └── test_new_behavior.py  # テストコード
```

## 📊 ログの活用

### STAMP状態遷移ログの分析

```python
import json
from pathlib import Path

# ログを読み込む
log_path = Path("data/logs/stamp/stamp_uuid-123_20250101_120000.json")
with open(log_path) as f:
    log_data = json.load(f)

# 状態遷移を分析
transitions = log_data["state_transitions"]
for t in transitions:
    print(f"Frame {t['frame']}: {t['from_state']} -> {t['to_state']}")
    if t["control_action"]:
        print(f"  Action: {t['control_action']}")
```

### コマンド完遂率の分析

```python
import json
from pathlib import Path

# ログを読み込む
log_path = Path("data/logs/commands/commands_uuid-123_20250101_120000.json")
with open(log_path) as f:
    log_data = json.load(f)

# サマリーを表示
summary = log_data["summary"]
print(f"Total Commands: {summary['total_commands']}")
print(f"Completed: {summary['completed']}")
print(f"Failed: {summary['failed']}")
print(f"Success Rate: {summary['success_rate'] * 100:.1f}%")

# 失敗したコマンドを確認
failed = [cmd for cmd in log_data["commands"] if cmd["status"] == "failed"]
for cmd in failed:
    print(f"\nFailed: {cmd['description']}")
    print(f"  Error: {cmd['error_message']}")
```

### 安全性メトリクスの分析 🆕

```python
import json
from pathlib import Path

# メトリクスログを読み込む
log_path = Path("data/logs/metrics/metrics_uuid-123.json")
with open(log_path) as f:
    metrics_data = json.load(f)

# サマリーを表示
summary = metrics_data["summary"]
print(f"Total Events: {summary['total_events']}")
print(f"Event Counts: {summary['event_counts']}")

# 最小TTCを確認
min_ttc = summary["min_ttc_per_vehicle"]
for vehicle_id, ttc in min_ttc.items():
    print(f"Vehicle {vehicle_id}: Min TTC = {ttc:.2f}s")

# 特定のイベントを分析
events = metrics_data["events"]
sudden_braking_events = [e for e in events if e["event_type"] == "sudden_braking"]
print(f"\nSudden Braking Events: {len(sudden_braking_events)}")
for event in sudden_braking_events[:5]:
    print(f"  Frame {event['frame']}: {event['description']}")
```

## 🎯 将来の展望

- **カバレッジ計測**: NPCロジックの実行パスを記録し、カバレッジを計測
- **パフォーマンスメトリクス**: 振る舞いの実行時間、成功率などを自動集計
- **安全性分析**: STAMP理論に基づいた安全性分析ツールの統合
- **機械学習統合**: ログデータを使った学習モデルのトレーニング

## 📝 ライセンス

このパッケージはATLASプロジェクトの一部です。
