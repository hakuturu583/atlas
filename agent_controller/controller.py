"""
Agent Controller - 統合制御クラス

すべての車両制御機能を単一のクラスから呼び出せる統合APIを提供します。
"""

from typing import Optional, Dict, Any, Callable, List, Tuple
import time
import carla

from .traffic_manager_wrapper import TrafficManagerWrapper
from .behaviors import (
    LaneChangeBehavior,
    CutInBehavior,
    TimedApproachBehavior,
    FollowBehavior,
    StopBehavior,
    BehaviorResult,
)
from .stamp_logger import STAMPLogger, ControlAction, StateType
from .command_tracker import CommandTracker, CommandStatus


class AgentController:
    """
    統合車両制御クラス

    CARLA接続、Traffic Manager、ロギング機能を統合した単一のインターフェースです。
    CARLAクライアントの接続と生存管理も自動的に行います。

    使用例（推奨）:
        >>> with AgentController(scenario_uuid="my-scenario") as controller:
        ...     world = controller.world
        ...     vehicle = world.spawn_actor(blueprint, transform)
        ...     vehicle_id = controller.register_vehicle(vehicle)
        ...     controller.lane_change(vehicle_id, frame=100, direction="left")

    使用例（既存のクライアントを使う場合）:
        >>> client = carla.Client("localhost", 2000)
        >>> with AgentController(client=client, scenario_uuid="my-scenario") as controller:
        ...     # ...
    """

    def __init__(
        self,
        scenario_uuid: str,
        client: Optional[carla.Client] = None,
        carla_host: str = "localhost",
        carla_port: int = 2000,
        carla_timeout: float = 10.0,
        tm_port: int = 8000,
        enable_logging: bool = True,
        synchronous_mode: bool = True,
        fixed_delta_seconds: float = 0.05,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        AgentControllerを初期化

        Args:
            scenario_uuid: シナリオUUID
            client: 既存のCARLAクライアント（Noneの場合は自動接続）
            carla_host: CARLAサーバーのホスト（clientがNoneの場合に使用）
            carla_port: CARLAサーバーのポート（clientがNoneの場合に使用）
            carla_timeout: 接続タイムアウト（秒）
            tm_port: Traffic Managerのポート
            enable_logging: ロギングを有効化するか
            synchronous_mode: 同期モードを有効化するか
            fixed_delta_seconds: 固定タイムステップ（秒）
            max_retries: 接続失敗時の最大リトライ回数
            retry_delay: リトライ間の待機時間（秒）
        """
        self.scenario_uuid = scenario_uuid
        self.enable_logging = enable_logging
        self.synchronous_mode = synchronous_mode
        self.fixed_delta_seconds = fixed_delta_seconds
        self._carla_host = carla_host
        self._carla_port = carla_port
        self._carla_timeout = carla_timeout
        self._tm_port = tm_port
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        # CARLAクライアントの管理
        self._owns_client = client is None
        if self._owns_client:
            # 新しいクライアントを作成（リトライ付き）
            self.client = self._connect_with_retry()
        else:
            # 既存のクライアントを使用
            self.client = client

        # Worldを取得
        self.world = self.client.get_world()

        # 同期モード設定を保存（終了時に復元するため）
        self._original_settings = self.world.get_settings()

        # 同期モードを設定
        if synchronous_mode:
            settings = self.world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = fixed_delta_seconds
            self.world.apply_settings(settings)

        # ロガー初期化
        if enable_logging:
            self.stamp_logger = STAMPLogger(scenario_uuid=scenario_uuid)
            self.command_tracker = CommandTracker(scenario_uuid=scenario_uuid)
        else:
            self.stamp_logger = None
            self.command_tracker = None

        # Traffic Manager Wrapper初期化
        self.tm_wrapper = TrafficManagerWrapper(
            client=self.client,
            port=tm_port,
            stamp_logger=self.stamp_logger,
            command_tracker=self.command_tracker,
        )

        # Behavior初期化（遅延インスタンス化）
        self._lane_change_behavior = None
        self._cut_in_behavior = None
        self._timed_approach_behavior = None
        self._follow_behavior = None
        self._stop_behavior = None

        # シミュレーションループ管理
        self._current_frame = 0
        self._callbacks: Dict[int, List[Callable[[], None]]] = {}
        self._tick_callback: Optional[Callable[[int], None]] = None

    # ========================================
    # 接続管理
    # ========================================

    def _connect_with_retry(self) -> carla.Client:
        """
        CARLAクライアントに接続（リトライ付き）

        Returns:
            CARLAクライアント

        Raises:
            RuntimeError: 最大リトライ回数を超えた場合
        """
        for attempt in range(1, self._max_retries + 1):
            try:
                print(
                    f"Connecting to CARLA at {self._carla_host}:{self._carla_port} (attempt {attempt}/{self._max_retries})..."
                )
                client = carla.Client(self._carla_host, self._carla_port)
                client.set_timeout(self._carla_timeout)

                # 接続を確認（worldを取得してみる）
                _ = client.get_world()

                print(f"✓ Successfully connected to CARLA")
                return client

            except RuntimeError as e:
                if attempt < self._max_retries:
                    print(
                        f"✗ Connection failed: {e}. Retrying in {self._retry_delay}s..."
                    )
                    time.sleep(self._retry_delay)
                else:
                    raise RuntimeError(
                        f"Failed to connect to CARLA after {self._max_retries} attempts: {e}"
                    )

    def check_connection(self) -> bool:
        """
        CARLAサーバーへの接続が有効か確認

        Returns:
            接続が有効ならTrue
        """
        try:
            # worldを取得して接続を確認
            _ = self.client.get_world()
            return True
        except RuntimeError:
            return False

    def reconnect(self) -> bool:
        """
        CARLAサーバーに再接続（自分で接続を管理している場合のみ）

        Returns:
            再接続に成功したらTrue

        Raises:
            RuntimeError: 自分で接続を管理していない場合、または再接続に失敗した場合
        """
        if not self._owns_client:
            raise RuntimeError(
                "Cannot reconnect: client is externally managed. "
                "Please handle reconnection externally."
            )

        try:
            print("Attempting to reconnect to CARLA...")
            self.client = self._connect_with_retry()
            self.world = self.client.get_world()

            # 同期モードを再設定
            if self.synchronous_mode:
                settings = self.world.get_settings()
                settings.synchronous_mode = True
                settings.fixed_delta_seconds = self.fixed_delta_seconds
                self.world.apply_settings(settings)

            # Traffic Manager Wrapperを再初期化
            self.tm_wrapper = TrafficManagerWrapper(
                client=self.client,
                port=self._tm_port,
                stamp_logger=self.stamp_logger,
                command_tracker=self.command_tracker,
            )

            print("✓ Reconnection successful")
            return True

        except RuntimeError as e:
            print(f"✗ Reconnection failed: {e}")
            return False

    def is_alive(self) -> bool:
        """
        CARLAサーバーが生きているか確認（エイリアス）

        Returns:
            サーバーが生きていればTrue
        """
        return self.check_connection()

    # ========================================
    # 車両登録・管理
    # ========================================

    def register_vehicle(
        self,
        vehicle: carla.Vehicle,
        auto_lane_change: bool = True,
        distance_to_leading: float = 2.5,
        speed_percentage: float = 100.0,
        ignore_lights: bool = False,
        ignore_vehicles: bool = False,
        ignore_signs: bool = False,
    ) -> int:
        """
        車両をTraffic Managerに登録

        Args:
            vehicle: 車両アクター
            auto_lane_change: 自動レーンチェンジを有効化
            distance_to_leading: 前方車両との距離（m）
            speed_percentage: 制限速度に対する速度パーセンテージ
            ignore_lights: 信号無視
            ignore_vehicles: 他車両無視
            ignore_signs: 標識無視

        Returns:
            車両ID
        """
        return self.tm_wrapper.register_vehicle(
            vehicle=vehicle,
            auto_lane_change=auto_lane_change,
            distance_to_leading=distance_to_leading,
            speed_percentage=speed_percentage,
            ignore_lights=ignore_lights,
            ignore_vehicles=ignore_vehicles,
            ignore_signs=ignore_signs,
        )

    def get_vehicle(self, vehicle_id: int) -> carla.Vehicle:
        """車両アクターを取得"""
        return self.tm_wrapper.get_vehicle(vehicle_id)

    def get_vehicle_config(self, vehicle_id: int) -> Dict[str, Any]:
        """車両設定を取得"""
        return self.tm_wrapper.get_vehicle_config(vehicle_id)

    def get_all_vehicles(self) -> list[int]:
        """登録されているすべての車両IDを取得"""
        return self.tm_wrapper.get_all_vehicles()

    # ========================================
    # 高レベル振る舞いAPI
    # ========================================

    def lane_change(
        self,
        vehicle_id: int,
        frame: Optional[int] = None,
        direction: str = "left",
        duration_frames: int = 100,
    ) -> BehaviorResult:
        """
        レーンチェンジを実行

        Args:
            vehicle_id: 車両ID
            frame: フレーム番号（Noneの場合は現在のフレームを使用）
            direction: "left" or "right"
            duration_frames: 実行フレーム数

        Returns:
            実行結果
        """
        if self._lane_change_behavior is None:
            self._lane_change_behavior = LaneChangeBehavior(self.tm_wrapper)

        if frame is None:
            frame = self._current_frame

        return self._lane_change_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            direction=direction,
            duration_frames=duration_frames,
        )

    def cut_in(
        self,
        vehicle_id: int,
        frame: Optional[int] = None,
        target_vehicle_id: int = None,
        gap_distance: float = 5.0,
        speed_boost: float = 120.0,
    ) -> BehaviorResult:
        """
        カットインを実行

        Args:
            vehicle_id: 実行車両ID
            frame: フレーム番号（Noneの場合は現在のフレームを使用）
            target_vehicle_id: カットイン対象車両ID
            gap_distance: 目標とする車間距離（m）
            speed_boost: 速度ブースト（%）

        Returns:
            実行結果
        """
        if self._cut_in_behavior is None:
            self._cut_in_behavior = CutInBehavior(self.tm_wrapper)

        if frame is None:
            frame = self._current_frame

        return self._cut_in_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            target_vehicle_id=target_vehicle_id,
            gap_distance=gap_distance,
            speed_boost=speed_boost,
        )

    def timed_approach(
        self,
        vehicle_id: int,
        frame: Optional[int] = None,
        target_location: carla.Location = None,
        target_time: float = None,
        speed_adjustment: float = 1.0,
        ignore_traffic: bool = False,
    ) -> BehaviorResult:
        """
        タイミングを合わせて特定地点に突入

        Args:
            vehicle_id: 車両ID
            frame: フレーム番号（Noneの場合は現在のフレームを使用）
            target_location: 目標地点
            target_time: 到達目標時刻（秒）
            speed_adjustment: 速度調整係数
            ignore_traffic: 信号・他車両を無視

        Returns:
            実行結果
        """
        if self._timed_approach_behavior is None:
            self._timed_approach_behavior = TimedApproachBehavior(self.tm_wrapper)

        if frame is None:
            frame = self._current_frame

        return self._timed_approach_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            target_location=target_location,
            target_time=target_time,
            speed_adjustment=speed_adjustment,
            ignore_traffic=ignore_traffic,
        )

    def follow(
        self,
        vehicle_id: int,
        frame: Optional[int] = None,
        target_vehicle_id: int = None,
        distance: float = 5.0,
        duration_frames: int = 200,
    ) -> BehaviorResult:
        """
        指定車両を追従

        Args:
            vehicle_id: 車両ID
            frame: フレーム番号（Noneの場合は現在のフレームを使用）
            target_vehicle_id: 追従対象車両ID
            distance: 追従距離（m）
            duration_frames: 追従フレーム数

        Returns:
            実行結果
        """
        if self._follow_behavior is None:
            self._follow_behavior = FollowBehavior(self.tm_wrapper)

        if frame is None:
            frame = self._current_frame

        return self._follow_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            target_vehicle_id=target_vehicle_id,
            distance=distance,
            duration_frames=duration_frames,
        )

    def stop(
        self,
        vehicle_id: int,
        frame: Optional[int] = None,
        duration_frames: int = 50,
    ) -> BehaviorResult:
        """
        車両を停止

        Args:
            vehicle_id: 車両ID
            frame: フレーム番号（Noneの場合は現在のフレームを使用）
            duration_frames: 停止フレーム数

        Returns:
            実行結果
        """
        if self._stop_behavior is None:
            self._stop_behavior = StopBehavior(self.tm_wrapper)

        if frame is None:
            frame = self._current_frame

        return self._stop_behavior.execute(
            vehicle_id=vehicle_id,
            frame=frame,
            duration_frames=duration_frames,
        )

    # ========================================
    # シミュレーションループとコールバック（🆕）
    # ========================================

    @property
    def current_frame(self) -> int:
        """現在のフレーム番号を取得"""
        return self._current_frame

    def register_callback(
        self, frame: int, callback: Callable[[], None]
    ) -> None:
        """
        特定フレームで実行されるコールバックを登録

        Args:
            frame: コールバックを実行するフレーム番号
            callback: 実行する関数（引数なし）

        使用例:
            >>> def on_frame_100():
            ...     controller.lane_change(ego_id, direction="left")
            >>> controller.register_callback(100, on_frame_100)
        """
        if frame not in self._callbacks:
            self._callbacks[frame] = []
        self._callbacks[frame].append(callback)

    def set_tick_callback(self, callback: Callable[[int], None]) -> None:
        """
        毎フレーム実行されるコールバックを設定

        Args:
            callback: フレーム番号を受け取る関数

        使用例:
            >>> def on_tick(frame):
            ...     if frame == 100:
            ...         controller.lane_change(ego_id, direction="left")
            >>> controller.set_tick_callback(on_tick)
        """
        self._tick_callback = callback

    def run_simulation(
        self,
        total_frames: int,
        on_tick: Optional[Callable[[int], None]] = None,
    ) -> None:
        """
        シミュレーションを実行（内部でworld.tick()を自動呼び出し）

        Args:
            total_frames: 実行するフレーム数
            on_tick: 毎フレーム実行されるコールバック（オプション）

        使用例:
            >>> # パターン1: on_tickコールバックを使用
            >>> def on_tick(frame):
            ...     if frame == 100:
            ...         controller.lane_change(ego_id, direction="left")
            >>> controller.run_simulation(total_frames=500, on_tick=on_tick)

            >>> # パターン2: register_callbackを使用
            >>> controller.register_callback(100, lambda: controller.lane_change(ego_id, direction="left"))
            >>> controller.run_simulation(total_frames=500)
        """
        if on_tick:
            self.set_tick_callback(on_tick)

        print(f"\n=== Starting Simulation ({total_frames} frames) ===\n")

        for frame in range(total_frames):
            self._current_frame = frame

            # 特定フレームのコールバックを実行
            if frame in self._callbacks:
                for callback in self._callbacks[frame]:
                    try:
                        callback()
                    except Exception as e:
                        print(f"⚠ Error in callback at frame {frame}: {e}")

            # 毎フレームのコールバックを実行
            if self._tick_callback:
                try:
                    self._tick_callback(frame)
                except Exception as e:
                    print(f"⚠ Error in tick callback at frame {frame}: {e}")

            # World更新
            self.world.tick()

            # 進捗表示（100フレームごと）
            if frame > 0 and frame % 100 == 0:
                print(f"  Frame {frame}/{total_frames}")

        print(f"\n✓ Simulation completed ({total_frames} frames)\n")

    def tick(self, frames: int = 1) -> None:
        """
        手動でWorld更新を実行（低レベルAPI）

        Args:
            frames: 更新するフレーム数
        """
        for _ in range(frames):
            self.world.tick()
            self._current_frame += 1

    # ========================================
    # 低レベルTraffic Manager設定
    # ========================================

    def set_auto_lane_change(
        self, vehicle_id: int, enable: bool, frame: Optional[int] = None
    ) -> None:
        """自動レーンチェンジの設定"""
        self.tm_wrapper.set_auto_lane_change(vehicle_id, enable, frame)

    def force_lane_change(
        self, vehicle_id: int, direction: bool, frame: Optional[int] = None
    ) -> None:
        """強制的にレーンチェンジを実行（True=左, False=右）"""
        self.tm_wrapper.force_lane_change(vehicle_id, direction, frame)

    def set_distance_to_leading(
        self, vehicle_id: int, distance: float, frame: Optional[int] = None
    ) -> None:
        """前方車両との距離を設定"""
        self.tm_wrapper.set_distance_to_leading(vehicle_id, distance, frame)

    def set_speed_percentage(
        self, vehicle_id: int, percentage: float, frame: Optional[int] = None
    ) -> None:
        """制限速度に対する速度パーセンテージを設定"""
        self.tm_wrapper.set_speed_percentage(vehicle_id, percentage, frame)

    def ignore_lights(
        self, vehicle_id: int, ignore: bool, frame: Optional[int] = None
    ) -> None:
        """信号無視の設定"""
        self.tm_wrapper.ignore_lights(vehicle_id, ignore, frame)

    def ignore_vehicles(
        self, vehicle_id: int, ignore: bool, frame: Optional[int] = None
    ) -> None:
        """他車両無視の設定"""
        self.tm_wrapper.ignore_vehicles(vehicle_id, ignore, frame)

    # ========================================
    # ロギング
    # ========================================

    def log_state_transition(
        self,
        frame: int,
        vehicle_id: int,
        to_state: StateType,
        control_action: Optional[ControlAction] = None,
        location: Optional[Dict[str, float]] = None,
        rotation: Optional[Dict[str, float]] = None,
        velocity: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """状態遷移を記録（手動ロギング用）"""
        if self.stamp_logger:
            self.stamp_logger.log_state_transition(
                frame=frame,
                vehicle_id=vehicle_id,
                to_state=to_state,
                control_action=control_action,
                location=location,
                rotation=rotation,
                velocity=velocity,
                metadata=metadata,
            )

    def log_control_action(
        self,
        frame: int,
        vehicle_id: int,
        action: ControlAction,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
    ) -> None:
        """制御アクションを記録（手動ロギング用）"""
        if self.stamp_logger:
            self.stamp_logger.log_control_action(
                frame=frame,
                vehicle_id=vehicle_id,
                action=action,
                parameters=parameters,
                result=result,
            )

    def get_vehicle_state(self, vehicle_id: int) -> StateType:
        """車両の現在の状態を取得"""
        if self.stamp_logger:
            return self.stamp_logger.get_vehicle_state(vehicle_id)
        return StateType.IDLE

    # ========================================
    # クリーンアップ
    # ========================================

    def finalize(self) -> tuple[Optional[str], Optional[str]]:
        """
        ログをファイナライズして保存

        Returns:
            (STAMP log path, Command log path)
        """
        stamp_log_path = None
        command_log_path = None

        if self.stamp_logger:
            stamp_log_path = str(self.stamp_logger.finalize())
            self.stamp_logger.print_summary()

        if self.command_tracker:
            command_log_path = str(self.command_tracker.finalize())
            self.command_tracker.print_summary()

        return stamp_log_path, command_log_path

    def cleanup(self) -> None:
        """クリーンアップ（車両のautopilot解除、設定の復元）"""
        self.tm_wrapper.cleanup()

        # 同期モード設定を元に戻す
        if self.synchronous_mode:
            self.world.apply_settings(self._original_settings)

    # ========================================
    # コンテキストマネージャ
    # ========================================

    def __enter__(self):
        """コンテキストマネージャのエントリ"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャの終了（自動クリーンアップ）"""
        self.finalize()
        self.cleanup()
        return False
