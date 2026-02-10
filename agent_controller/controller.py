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
from .vehicle_config import VehicleConfig


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
        self._world = self.client.get_world()

        # 同期モード設定を保存（終了時に復元するため）
        self._original_settings = self._world.get_settings()

        # 同期モードを設定
        if synchronous_mode:
            settings = self._world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = fixed_delta_seconds
            self._world.apply_settings(settings)

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
        self._callbacks: List[Tuple[Callable[[], bool], Callable[[], None], bool]] = (
            []
        )  # (trigger_fn, callback_fn, one_shot)
        self._tick_callback: Optional[Callable[[int], None]] = None

        # 車両生存管理
        self._spawned_vehicles: List[carla.Vehicle] = []  # スポーンした車両を追跡

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
            self._world = self.client.get_world()

            # 同期モードを再設定
            if self.synchronous_mode:
                settings = self._world.get_settings()
                settings.synchronous_mode = True
                settings.fixed_delta_seconds = self.fixed_delta_seconds
                self._world.apply_settings(settings)

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
    # 車両スポーンとブループリント
    # ========================================

    def get_blueprint_library(self) -> carla.BlueprintLibrary:
        """
        ブループリントライブラリを取得

        Returns:
            ブループリントライブラリ
        """
        return self._world.get_blueprint_library()

    def get_map(self) -> carla.Map:
        """
        CARLAマップを取得

        Returns:
            CARLAマップ
        """
        return self._world.get_map()

    def spawn_vehicle(
        self,
        blueprint_name: str,
        transform: carla.Transform,
        auto_register: bool = True,
        auto_destroy: bool = True,
        config: Optional[VehicleConfig] = None,
        **register_kwargs,
    ) -> Tuple[carla.Vehicle, Optional[int]]:
        """
        車両をスポーン（オプションで自動登録・自動破棄）

        Args:
            blueprint_name: ブループリント名（例: "vehicle.tesla.model3"）
            transform: スポーン位置
            auto_register: Trueの場合、自動的にTraffic Managerに登録
            auto_destroy: Trueの場合、デストラクタで自動的に破棄
            config: 車両設定（VehicleConfig）
            **register_kwargs: register_vehicle()に渡す追加パラメータ（configより優先）

        Returns:
            (車両アクター, 車両ID)
            ※ auto_register=Falseの場合、車両IDはNone

        使用例:
            >>> # パターン1: VehicleConfigを使用（推奨）
            >>> from agent_controller import VehicleConfig
            >>> config = VehicleConfig(
            ...     auto_lane_change=False,
            ...     speed_percentage=80.0
            ... )
            >>> vehicle, vehicle_id = controller.spawn_vehicle(
            ...     "vehicle.tesla.model3",
            ...     transform,
            ...     config=config
            ... )

            >>> # パターン2: キーワード引数を使用
            >>> vehicle, vehicle_id = controller.spawn_vehicle(
            ...     "vehicle.tesla.model3",
            ...     transform,
            ...     speed_percentage=80.0
            ... )
        """
        blueprint_library = self.get_blueprint_library()
        blueprint = blueprint_library.find(blueprint_name)
        vehicle = self._world.spawn_actor(blueprint, transform)

        # 自動破棄が有効な場合、追跡リストに追加
        if auto_destroy:
            self._spawned_vehicles.append(vehicle)

        if auto_register:
            # VehicleConfigがある場合は、その設定を使用
            if config:
                kwargs = config.to_dict()
                # キーワード引数で上書き
                kwargs.update(register_kwargs)
            else:
                kwargs = register_kwargs

            vehicle_id = self.register_vehicle(vehicle, **kwargs)
            return vehicle, vehicle_id
        else:
            return vehicle, None

    def spawn_vehicle_from_lane(
        self,
        blueprint_name: str,
        lane_coord: "LaneCoord",
        auto_register: bool = True,
        auto_destroy: bool = True,
        config: Optional[VehicleConfig] = None,
        **register_kwargs,
    ) -> Tuple[carla.Vehicle, Optional[int]]:
        """
        レーン座標から車両をスポーン（opendrive_utilsが必要）

        Args:
            blueprint_name: ブループリント名
            lane_coord: レーン座標（LaneCoord）
            auto_register: Trueの場合、自動的にTraffic Managerに登録
            auto_destroy: Trueの場合、デストラクタで自動的に破棄
            config: 車両設定（VehicleConfig）
            **register_kwargs: register_vehicle()に渡す追加パラメータ（configより優先）

        Returns:
            (車両アクター, 車両ID)

        使用例:
            >>> # パターン1: VehicleConfigを使用（推奨）
            >>> from opendrive_utils import LaneCoord
            >>> from agent_controller import VehicleConfig
            >>> lane_coord = LaneCoord(road_id=10, lane_id=-1, s=50.0)
            >>> config = VehicleConfig(
            ...     auto_lane_change=False,
            ...     speed_percentage=80.0
            ... )
            >>> vehicle, vehicle_id = controller.spawn_vehicle_from_lane(
            ...     "vehicle.tesla.model3",
            ...     lane_coord,
            ...     config=config
            ... )

            >>> # パターン2: プリセットを使用
            >>> from agent_controller import CAUTIOUS_DRIVER
            >>> vehicle, vehicle_id = controller.spawn_vehicle_from_lane(
            ...     "vehicle.tesla.model3",
            ...     lane_coord,
            ...     config=CAUTIOUS_DRIVER
            ... )
        """
        from opendrive_utils import OpenDriveMap, SpawnHelper

        od_map = OpenDriveMap(self._world)
        spawn_helper = SpawnHelper(od_map)
        transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)

        return self.spawn_vehicle(
            blueprint_name,
            transform,
            auto_register,
            auto_destroy,
            config,
            **register_kwargs,
        )

    def destroy_vehicle(self, vehicle_id: int) -> bool:
        """
        車両を破棄

        Args:
            vehicle_id: 車両ID

        Returns:
            成功したらTrue
        """
        vehicle = self.get_vehicle(vehicle_id)
        if vehicle:
            # 追跡リストから削除
            if vehicle in self._spawned_vehicles:
                self._spawned_vehicles.remove(vehicle)

            vehicle.destroy()

            # 内部管理から削除
            if vehicle_id in self.tm_wrapper.vehicles:
                del self.tm_wrapper.vehicles[vehicle_id]
            if vehicle_id in self.tm_wrapper.vehicle_configs:
                del self.tm_wrapper.vehicle_configs[vehicle_id]
            return True
        return False

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

    # ========================================
    # トリガー関数（条件判定）
    # ========================================

    def when_timestep_equals(self, frame: int) -> Callable[[], bool]:
        """
        特定のタイムステップ（フレーム）に到達したときにTrueを返すトリガー関数

        Args:
            frame: トリガーするフレーム番号

        Returns:
            条件判定関数

        使用例:
            >>> controller.register_callback(
            ...     controller.when_timestep_equals(100),
            ...     lambda: controller.lane_change(ego_id, direction="left")
            ... )
        """

        def trigger():
            return self._current_frame == frame

        return trigger

    def when_timestep_greater_than(self, frame: int) -> Callable[[], bool]:
        """
        タイムステップが指定値を超えたときにTrueを返すトリガー関数

        Args:
            frame: 比較するフレーム番号

        Returns:
            条件判定関数
        """

        def trigger():
            return self._current_frame > frame

        return trigger

    def when_vehicle_at_location(
        self,
        vehicle_id: int,
        target_location: carla.Location,
        threshold: float = 5.0,
    ) -> Callable[[], bool]:
        """
        車両が特定の位置に到達したときにTrueを返すトリガー関数

        Args:
            vehicle_id: 車両ID
            target_location: 目標位置
            threshold: 距離の閾値（m）

        Returns:
            条件判定関数
        """

        def trigger():
            vehicle = self.get_vehicle(vehicle_id)
            if vehicle is None:
                return False
            current_location = vehicle.get_location()
            distance = current_location.distance(target_location)
            return distance <= threshold

        return trigger

    def when_distance_between(
        self,
        vehicle_id1: int,
        vehicle_id2: int,
        distance: float,
        operator: str = "less",
    ) -> Callable[[], bool]:
        """
        2つの車両間の距離が条件を満たすときにTrueを返すトリガー関数

        Args:
            vehicle_id1: 車両1のID
            vehicle_id2: 車両2のID
            distance: 比較する距離（m）
            operator: 比較演算子 ("less", "greater", "equal")

        Returns:
            条件判定関数
        """

        def trigger():
            vehicle1 = self.get_vehicle(vehicle_id1)
            vehicle2 = self.get_vehicle(vehicle_id2)
            if vehicle1 is None or vehicle2 is None:
                return False

            loc1 = vehicle1.get_location()
            loc2 = vehicle2.get_location()
            current_distance = loc1.distance(loc2)

            if operator == "less":
                return current_distance < distance
            elif operator == "greater":
                return current_distance > distance
            elif operator == "equal":
                return abs(current_distance - distance) < 0.5
            else:
                return False

        return trigger

    def when_speed_greater_than(
        self, vehicle_id: int, speed: float
    ) -> Callable[[], bool]:
        """
        車両の速度が閾値を超えたときにTrueを返すトリガー関数

        Args:
            vehicle_id: 車両ID
            speed: 速度の閾値（km/h）

        Returns:
            条件判定関数
        """

        def trigger():
            vehicle = self.get_vehicle(vehicle_id)
            if vehicle is None:
                return False
            velocity = vehicle.get_velocity()
            current_speed = (
                3.6 * (velocity.x**2 + velocity.y**2 + velocity.z**2) ** 0.5
            )
            return current_speed > speed

        return trigger

    def when_speed_less_than(
        self, vehicle_id: int, speed: float
    ) -> Callable[[], bool]:
        """
        車両の速度が閾値を下回ったときにTrueを返すトリガー関数

        Args:
            vehicle_id: 車両ID
            speed: 速度の閾値（km/h）

        Returns:
            条件判定関数
        """

        def trigger():
            vehicle = self.get_vehicle(vehicle_id)
            if vehicle is None:
                return False
            velocity = vehicle.get_velocity()
            current_speed = (
                3.6 * (velocity.x**2 + velocity.y**2 + velocity.z**2) ** 0.5
            )
            return current_speed < speed

        return trigger

    # ========================================
    # コールバック登録
    # ========================================

    def register_callback(
        self,
        trigger: Callable[[], bool],
        callback: Callable[[], None],
        one_shot: bool = True,
    ) -> None:
        """
        トリガー条件が満たされたときに実行されるコールバックを登録

        Args:
            trigger: 条件判定関数（Trueを返すとコールバックが実行される）
            callback: 実行する関数（引数なし）
            one_shot: Trueの場合、一度実行したら自動削除（デフォルト: True）

        使用例:
            >>> # パターン1: 特定フレームで実行
            >>> controller.register_callback(
            ...     controller.when_timestep_equals(100),
            ...     lambda: controller.lane_change(ego_id, direction="left")
            ... )

            >>> # パターン2: 車両が位置に到達したら実行
            >>> controller.register_callback(
            ...     controller.when_vehicle_at_location(ego_id, target_location),
            ...     lambda: print("Target reached!")
            ... )

            >>> # パターン3: 継続的に監視（リピート）
            >>> controller.register_callback(
            ...     controller.when_speed_greater_than(ego_id, 80.0),
            ...     lambda: print("Speeding!"),
            ...     one_shot=False
            ... )
        """
        self._callbacks.append((trigger, callback, one_shot))

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
            >>> # パターン1: トリガー関数を使用（推奨）
            >>> controller.register_callback(
            ...     controller.when_timestep_equals(100),
            ...     lambda: controller.lane_change(ego_id, direction="left")
            ... )
            >>> controller.run_simulation(total_frames=500)

            >>> # パターン2: on_tickコールバックを使用
            >>> def on_tick(frame):
            ...     if frame == 100:
            ...         controller.lane_change(ego_id, direction="left")
            >>> controller.run_simulation(total_frames=500, on_tick=on_tick)
        """
        if on_tick:
            self.set_tick_callback(on_tick)

        print(f"\n=== Starting Simulation ({total_frames} frames) ===\n")

        for frame in range(total_frames):
            self._current_frame = frame

            # トリガーベースのコールバックを評価・実行
            callbacks_to_remove = []
            for i, (trigger, callback, one_shot) in enumerate(self._callbacks):
                try:
                    # トリガー条件を評価
                    if trigger():
                        # コールバックを実行
                        try:
                            callback()
                        except Exception as e:
                            print(f"⚠ Error in callback at frame {frame}: {e}")

                        # ワンショットの場合は削除リストに追加
                        if one_shot:
                            callbacks_to_remove.append(i)
                except Exception as e:
                    print(f"⚠ Error evaluating trigger at frame {frame}: {e}")

            # ワンショットコールバックを削除（逆順で削除）
            for i in reversed(callbacks_to_remove):
                self._callbacks.pop(i)

            # 毎フレームのコールバックを実行
            if self._tick_callback:
                try:
                    self._tick_callback(frame)
                except Exception as e:
                    print(f"⚠ Error in tick callback at frame {frame}: {e}")

            # World更新
            self._world.tick()

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
            self._world.tick()
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
            self._world.apply_settings(self._original_settings)

    # ========================================
    # コンテキストマネージャ
    # ========================================

    def __enter__(self):
        """コンテキストマネージャのエントリ"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャの終了（自動クリーンアップ）"""
        # スポーンした車両を自動破棄
        if self._spawned_vehicles:
            print(f"\n=== Auto-destroying {len(self._spawned_vehicles)} vehicles ===")
            for vehicle in self._spawned_vehicles[:]:  # コピーを作って反復
                try:
                    vehicle.destroy()
                    print(f"  ✓ Vehicle {vehicle.id} destroyed")
                except Exception as e:
                    print(f"  ✗ Failed to destroy vehicle {vehicle.id}: {e}")
            self._spawned_vehicles.clear()

        self.finalize()
        self.cleanup()
        return False
