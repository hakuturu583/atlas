# agent_controller - CARLA Traffic Manager Wrapper

CARLA Traffic Managerをラップし、高レベルAPIを提供するパッケージです。
テストケースでよくあるシナリオを簡単に記述でき、STAMP状態遷移ロガーとユーザー指示追跡機能を統合しています。

## 📋 特徴

- **統合API**: CARLAクライアント接続、Traffic Manager、ロギング機能を単一クラスで管理
- **自動接続管理**: CARLAサーバーへの接続、リトライ、生存確認を自動化
- **高レベルAPI**: レーンチェンジ、カットイン、タイミング突入などの振る舞いを簡単に記述
- **STAMPロギング**: STAMP理論に基づいた状態遷移とcontrol actionを記録
- **指示追跡**: ユーザーからの指示の完遂状態を記録
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

### 推奨: AgentControllerを使う（最もシンプル）

```python
from agent_controller import AgentController
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

# AgentControllerが自動的に:
# - CARLAに接続（リトライ機能付き）
# - 同期モードを設定
# - ログを初期化
with AgentController(
    scenario_uuid="my_scenario",
    carla_host="localhost",
    carla_port=2000,
) as controller:
    world = controller.world

    # 接続確認
    if controller.is_alive():
        print("✓ CARLA server is alive")

    # 車両をスポーン
    blueprint = world.get_blueprint_library().find("vehicle.tesla.model3")
    od_map = OpenDriveMap(world)
    spawn_helper = SpawnHelper(od_map)

    lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
    transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)
    vehicle = world.spawn_actor(blueprint, transform)

    # 車両を登録
    vehicle_id = controller.register_vehicle(
        vehicle=vehicle,
        auto_lane_change=False,
        distance_to_leading=5.0,
        speed_percentage=80.0,
    )

    # 高レベルAPIで振る舞いを実行
    frame = 0

    # レーンチェンジ
    result = controller.lane_change(
        vehicle_id=vehicle_id,
        frame=frame,
        direction="left",
        duration_frames=100,
    )
    print(f"{result.message}")

    # カットイン（他の車両が必要）
    result = controller.cut_in(
        vehicle_id=vehicle_id,
        frame=frame + 100,
        target_vehicle_id=other_vehicle_id,
        gap_distance=3.0,
        speed_boost=120.0,
    )

    # 追従
    result = controller.follow(
        vehicle_id=vehicle_id,
        frame=frame + 200,
        target_vehicle_id=lead_vehicle_id,
        distance=5.0,
        duration_frames=200,
    )

    # 停止
    result = controller.stop(
        vehicle_id=vehicle_id,
        frame=frame + 400,
        duration_frames=50,
    )

    # 車両を破棄
    vehicle.destroy()

# コンテキストマネージャを抜けると自動的に:
# - ログがファイナライズ・保存される
# - サマリーが出力される
# - 同期モードが元に戻される
# - クリーンアップが実行される
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

#### 車両登録・管理メソッド

- `register_vehicle(vehicle, **config) -> int` - 車両を登録
- `get_vehicle(vehicle_id) -> carla.Vehicle` - 車両アクターを取得
- `get_vehicle_config(vehicle_id) -> Dict` - 車両設定を取得
- `get_all_vehicles() -> list[int]` - 登録されているすべての車両IDを取得

#### 高レベル振る舞いメソッド

- `lane_change(vehicle_id, frame, direction, duration_frames)` - レーンチェンジ
- `cut_in(vehicle_id, frame, target_vehicle_id, gap_distance, speed_boost)` - カットイン
- `timed_approach(vehicle_id, frame, target_location, target_time, ...)` - タイミング突入
- `follow(vehicle_id, frame, target_vehicle_id, distance, duration_frames)` - 追従
- `stop(vehicle_id, frame, duration_frames)` - 停止

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

## 🎯 将来の展望

- **カバレッジ計測**: NPCロジックの実行パスを記録し、カバレッジを計測
- **パフォーマンスメトリクス**: 振る舞いの実行時間、成功率などを自動集計
- **安全性分析**: STAMP理論に基づいた安全性分析ツールの統合
- **機械学習統合**: ログデータを使った学習モデルのトレーニング

## 📝 ライセンス

このパッケージはATLASプロジェクトの一部です。
