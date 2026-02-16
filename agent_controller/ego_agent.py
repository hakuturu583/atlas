"""
EgoAgent - VLAモデルと連携する自車エージェント

gRPC通信でVLAモデル（Alpamayo-R1-10B、RT-2、OpenVLAなど）からアクションを取得し、
CARLAで車両を制御します。
"""

import carla
import grpc
import io
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from PIL import Image

# gRPC生成コード
from generated.grpc_pb2 import (
    sensor_data_pb2,
    control_command_pb2,
    ad_stack_pb2,
    ad_stack_pb2_grpc,
)

# agent_controller
from .sensor_config import SensorConfig, SensorDefinition
from .stamp_logger import STAMPLogger, ControlAction, StateType

logger = logging.getLogger(__name__)


@dataclass
class EgoAgentMetrics:
    """EgoAgentのパフォーマンスメトリクス"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def avg_latency_ms(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests


class EgoAgent:
    """
    VLAモデルと連携する自車エージェント

    特徴:
    - gRPC通信でVLAモデルとやり取り
    - URDFで定義されたセンサーを自動アタッチ
    - センサーデータを収集してVLAモデルに送信
    - VLA出力（Waypoint/Discrete/Continuous）を処理
    - 低レベル制御コマンドに変換してCARLAに適用
    - STAMPLoggerでログ記録
    """

    def __init__(
        self,
        vehicle: carla.Vehicle,
        agent_id: str,
        sensor_config: SensorConfig,
        grpc_host: str = "localhost",
        grpc_port: int = 50051,
        stamp_logger: Optional[STAMPLogger] = None,
        controller_type: str = "pure_pursuit",
        max_message_length: int = 50 * 1024 * 1024,  # 50 MB
    ):
        """
        Args:
            vehicle: CARLA車両
            agent_id: エージェント識別子
            sensor_config: センサー構成（URDFから生成）
            grpc_host: VLAサービスのホスト
            grpc_port: VLAサービスのポート
            stamp_logger: STAMPLogger（オプション）
            controller_type: コントローラータイプ（"pure_pursuit", "stanley", "mpc"）
            max_message_length: gRPC最大メッセージサイズ
        """
        self.vehicle = vehicle
        self.agent_id = agent_id
        self.sensor_config = sensor_config
        self.grpc_host = grpc_host
        self.grpc_port = grpc_port
        self.stamp_logger = stamp_logger
        self.controller_type = controller_type

        # gRPCチャネル設定
        self.channel = grpc.insecure_channel(
            f"{grpc_host}:{grpc_port}",
            options=[
                ("grpc.max_send_message_length", max_message_length),
                ("grpc.max_receive_message_length", max_message_length),
            ],
        )
        self.stub = ad_stack_pb2_grpc.VLAServiceStub(self.channel)

        # センサー管理
        self.sensors: Dict[str, carla.Sensor] = {}
        self.sensor_data: Dict[str, any] = {}

        # メトリクス
        self.metrics = EgoAgentMetrics()

        # センサーをアタッチ
        self._attach_sensors()

        # VLAサービスの初期化を待機
        if not self._wait_for_vla_initialization(timeout=300.0):
            logger.warning(
                f"VLA service initialization timeout. Agent may not work correctly."
            )

        logger.info(
            f"EgoAgent '{agent_id}' initialized with {len(self.sensors)} sensors"
        )

    def _attach_sensors(self):
        """URDFで定義されたセンサーをCARLA車両にアタッチ"""
        world = self.vehicle.get_world()
        blueprint_library = world.get_blueprint_library()

        for sensor_def in self.sensor_config.sensors:
            try:
                # Blueprintの取得
                bp = blueprint_library.find(sensor_def.sensor_type)

                # パラメータ設定
                for key, value in sensor_def.parameters.items():
                    if bp.has_attribute(key):
                        bp.set_attribute(key, str(value))

                # Transform設定
                x, y, z, pitch, yaw, roll = sensor_def.to_carla_transform()
                transform = carla.Transform(
                    carla.Location(x=x, y=y, z=z),
                    carla.Rotation(pitch=pitch, yaw=yaw, roll=roll),
                )

                # センサーをスポーン
                sensor = world.spawn_actor(bp, transform, attach_to=self.vehicle)

                # データ収集用のリスナー登録
                sensor.listen(
                    lambda data, sid=sensor_def.sensor_id: self._on_sensor_data(
                        sid, data
                    )
                )

                self.sensors[sensor_def.sensor_id] = sensor
                logger.debug(f"Attached sensor: {sensor_def.sensor_id}")

            except Exception as e:
                logger.error(f"Failed to attach sensor {sensor_def.sensor_id}: {e}")

    def _wait_for_vla_initialization(self, timeout: float = 300.0) -> bool:
        """
        VLAサービスの初期化完了を待つ

        Args:
            timeout: タイムアウト時間（秒）

        Returns:
            bool: 初期化が完了した場合True
        """
        logger.info(f"Waiting for VLA service initialization (timeout: {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                health_request = ad_stack_pb2.HealthCheckRequest(
                    service_name="VLAService"
                )
                health_response = self.stub.HealthCheck(
                    health_request, timeout=5.0
                )

                if health_response.status == ad_stack_pb2.HealthCheckResponse.SERVING:
                    logger.info("✓ VLA service is ready")
                    return True
                elif health_response.status == ad_stack_pb2.HealthCheckResponse.INITIALIZING:
                    progress = health_response.initialization_progress * 100
                    stage = health_response.initialization_stage
                    message = health_response.initialization_message
                    logger.info(
                        f"  Initializing... {progress:.1f}% ({stage}: {message})"
                    )
                    time.sleep(2.0)
                else:
                    logger.warning(
                        f"VLA service status: {health_response.status}"
                    )
                    time.sleep(2.0)

            except grpc.RpcError as e:
                logger.debug(f"VLA service not ready yet: {e.code()}")
                time.sleep(2.0)
            except Exception as e:
                logger.warning(f"Health check error: {e}")
                time.sleep(2.0)

        logger.error(f"VLA service initialization timeout ({timeout}s)")
        return False

    def _on_sensor_data(self, sensor_id: str, data: carla.SensorData):
        """センサーデータの受信コールバック"""
        self.sensor_data[sensor_id] = data

    def process_frame(self, frame: int, timestamp: float) -> bool:
        """
        1フレーム分の処理を実行

        Args:
            frame: フレーム番号
            timestamp: タイムスタンプ（秒）

        Returns:
            bool: 成功した場合True
        """
        try:
            start_time = time.time()

            # 1. センサーデータを収集
            sensor_bundle = self._build_sensor_data_bundle(frame, timestamp)

            # 2. VLAモデルへ送信
            vla_output = self.stub.ProcessSensorData(sensor_bundle)

            # 3. VLA出力を処理
            control_command = self._process_vla_output(vla_output)

            # 4. 制御コマンドを適用
            self._apply_control_command(control_command)

            # 5. メトリクス更新
            latency_ms = (time.time() - start_time) * 1000
            self._update_metrics(success=True, latency_ms=latency_ms)

            # 6. STAMPログ記録
            if self.stamp_logger:
                self._log_stamp(frame, timestamp, vla_output, control_command)

            return True

        except Exception as e:
            logger.error(f"EgoAgent frame processing failed: {e}")
            self._update_metrics(success=False)
            return False

    def _build_sensor_data_bundle(
        self, frame: int, timestamp: float
    ) -> sensor_data_pb2.SensorDataBundle:
        """センサーデータをgRPCメッセージに変換"""
        # 車両状態の取得
        vehicle_transform = self.vehicle.get_transform()
        vehicle_velocity = self.vehicle.get_velocity()
        vehicle_control = self.vehicle.get_control()

        vehicle_state = sensor_data_pb2.VehicleState(
            transform=sensor_data_pb2.Transform(
                location=sensor_data_pb2.Vector3(
                    x=vehicle_transform.location.x,
                    y=vehicle_transform.location.y,
                    z=vehicle_transform.location.z,
                ),
                rotation=sensor_data_pb2.Vector3(
                    x=vehicle_transform.rotation.pitch,
                    y=vehicle_transform.rotation.yaw,
                    z=vehicle_transform.rotation.roll,
                ),
            ),
            velocity=sensor_data_pb2.Vector3(
                x=vehicle_velocity.x, y=vehicle_velocity.y, z=vehicle_velocity.z
            ),
            speed_kmh=3.6
            * (vehicle_velocity.x**2 + vehicle_velocity.y**2 + vehicle_velocity.z**2)
            ** 0.5,
            throttle=vehicle_control.throttle,
            brake=vehicle_control.brake,
            steering_angle=vehicle_control.steer * 70.0,  # 正規化されたステアリングを角度に変換（概算）
            hand_brake=vehicle_control.hand_brake,
            gear=vehicle_control.gear,
        )

        # カメラ画像の収集
        cameras = []
        for sensor_id, sensor_data in self.sensor_data.items():
            if isinstance(sensor_data, carla.Image):
                camera_image = self._compress_camera_image(sensor_id, sensor_data)
                cameras.append(camera_image)

        # SensorDataBundleの構築
        bundle = sensor_data_pb2.SensorDataBundle(
            frame_number=frame,
            timestamp_ns=int(timestamp * 1e9),
            vehicle_state=vehicle_state,
            cameras=cameras,
        )

        return bundle

    def _compress_camera_image(
        self, sensor_id: str, image_data: carla.Image
    ) -> sensor_data_pb2.CameraImage:
        """カメラ画像をJPEG圧縮してgRPCメッセージに変換"""
        # CARLA画像データをPIL Imageに変換
        array = image_data.raw_data
        image = Image.frombytes("RGBA", (image_data.width, image_data.height), array)
        image = image.convert("RGB")  # RGBAからRGBに変換

        # JPEG圧縮
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=80)
        jpeg_data = buffer.getvalue()

        # gRPCメッセージ構築
        camera_image = sensor_data_pb2.CameraImage(
            camera_id=sensor_id,
            width=image_data.width,
            height=image_data.height,
            image_data=jpeg_data,
            timestamp_ns=int(image_data.timestamp * 1e9),
        )

        return camera_image

    def _process_vla_output(
        self, vla_output: control_command_pb2.VLAOutput
    ) -> control_command_pb2.VehicleControlCommand:
        """
        VLA出力を低レベル制御コマンドに変換

        VLAの出力形式に応じて適切な処理を行う：
        - WaypointTrajectory: Pure Pursuit/Stanley/MPCで追従
        - DiscreteAction: アクションマッピング
        - ContinuousAction: 直接適用
        """
        if vla_output.HasField("waypoint_trajectory"):
            return self._waypoint_to_control(vla_output.waypoint_trajectory)
        elif vla_output.HasField("discrete_action"):
            return self._discrete_to_control(vla_output.discrete_action)
        elif vla_output.HasField("continuous_action"):
            return self._continuous_to_control(vla_output.continuous_action)
        else:
            logger.warning("VLA output has no recognized action type, using default")
            return control_command_pb2.VehicleControlCommand(
                throttle=0.0, steer=0.0, brake=1.0
            )

    def _waypoint_to_control(
        self, trajectory: control_command_pb2.WaypointTrajectory
    ) -> control_command_pb2.VehicleControlCommand:
        """Waypoint軌跡をPure Pursuitで追従"""
        if len(trajectory.waypoints) == 0:
            logger.warning("Empty waypoint trajectory")
            return control_command_pb2.VehicleControlCommand(
                throttle=0.0, steer=0.0, brake=1.0
            )

        # 最初のwaypointを目標とする（簡易実装）
        target_waypoint = trajectory.waypoints[0]

        # Pure Pursuitコントローラー（簡易版）
        vehicle_location = self.vehicle.get_location()
        target_x = target_waypoint.x  # 自車座標系
        target_y = target_waypoint.y

        # ステアリング計算（簡易版）
        look_ahead_distance = (target_x**2 + target_y**2) ** 0.5
        if look_ahead_distance > 0.1:
            curvature = 2.0 * target_y / (look_ahead_distance**2)
            steer = max(-1.0, min(1.0, curvature * 5.0))  # ゲイン調整
        else:
            steer = 0.0

        # スロットル/ブレーキ計算（目標速度に基づく）
        target_speed_mps = target_waypoint.speed_mps if target_waypoint.speed_mps > 0 else 10.0
        current_speed_mps = self.vehicle.get_velocity().length()

        speed_error = target_speed_mps - current_speed_mps
        if speed_error > 1.0:
            throttle = min(1.0, speed_error * 0.5)
            brake = 0.0
        elif speed_error < -1.0:
            throttle = 0.0
            brake = min(1.0, abs(speed_error) * 0.3)
        else:
            throttle = 0.3
            brake = 0.0

        return control_command_pb2.VehicleControlCommand(
            throttle=throttle,
            steer=steer,
            brake=brake,
            target_waypoint=target_waypoint,
            controller_type=self.controller_type,
        )

    def _discrete_to_control(
        self, action: control_command_pb2.DiscreteAction
    ) -> control_command_pb2.VehicleControlCommand:
        """離散アクションをマッピング（簡易実装）"""
        # 例: action_id=0:stop, 1:go, 2:left, 3:right
        action_id = action.action_id

        if action_id == 0:  # stop
            return control_command_pb2.VehicleControlCommand(
                throttle=0.0, steer=0.0, brake=1.0, controller_type="discrete_action"
            )
        elif action_id == 1:  # go
            return control_command_pb2.VehicleControlCommand(
                throttle=0.5, steer=0.0, brake=0.0, controller_type="discrete_action"
            )
        elif action_id == 2:  # left
            return control_command_pb2.VehicleControlCommand(
                throttle=0.3, steer=-0.5, brake=0.0, controller_type="discrete_action"
            )
        elif action_id == 3:  # right
            return control_command_pb2.VehicleControlCommand(
                throttle=0.3, steer=0.5, brake=0.0, controller_type="discrete_action"
            )
        else:
            return control_command_pb2.VehicleControlCommand(
                throttle=0.0, steer=0.0, brake=1.0, controller_type="discrete_action"
            )

    def _continuous_to_control(
        self, action: control_command_pb2.ContinuousAction
    ) -> control_command_pb2.VehicleControlCommand:
        """連続アクションを直接適用"""
        # action_names = ["throttle", "steer", "brake"] と仮定
        throttle = 0.0
        steer = 0.0
        brake = 0.0

        for i, name in enumerate(action.action_names):
            if i >= len(action.action_values):
                break
            value = action.action_values[i]

            if name == "throttle":
                throttle = max(0.0, min(1.0, value))
            elif name == "steer":
                steer = max(-1.0, min(1.0, value))
            elif name == "brake":
                brake = max(0.0, min(1.0, value))

        return control_command_pb2.VehicleControlCommand(
            throttle=throttle,
            steer=steer,
            brake=brake,
            controller_type="continuous_action",
        )

    def _apply_control_command(
        self, command: control_command_pb2.VehicleControlCommand
    ):
        """制御コマンドをCARLA車両に適用"""
        carla_control = carla.VehicleControl(
            throttle=command.throttle,
            steer=command.steer,
            brake=command.brake,
            hand_brake=command.hand_brake,
            reverse=command.reverse,
        )
        self.vehicle.apply_control(carla_control)

    def _update_metrics(self, success: bool, latency_ms: float = 0.0):
        """メトリクス更新"""
        self.metrics.total_requests += 1
        if success:
            self.metrics.successful_requests += 1
            self.metrics.total_latency_ms += latency_ms
            self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, latency_ms)
            self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, latency_ms)
        else:
            self.metrics.failed_requests += 1

    def _log_stamp(
        self,
        frame: int,
        timestamp: float,
        vla_output: control_command_pb2.VLAOutput,
        control_command: control_command_pb2.VehicleControlCommand,
    ):
        """STAMPログ記録"""
        # 制御アクションの記録
        action = ControlAction(
            timestamp=timestamp,
            frame=frame,
            vehicle_id=self.vehicle.id,
            action_type="vla_control",
            parameters={
                "model_name": vla_output.model_name,
                "controller_type": control_command.controller_type,
                "throttle": control_command.throttle,
                "steer": control_command.steer,
                "brake": control_command.brake,
            },
            reasoning=vla_output.reasoning_trace if vla_output.reasoning_trace else None,
        )
        self.stamp_logger.log_control_action(action)

    def get_metrics(self) -> Dict[str, any]:
        """メトリクスを取得"""
        return {
            "agent_id": self.agent_id,
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.success_rate,
            "avg_latency_ms": self.metrics.avg_latency_ms,
            "min_latency_ms": self.metrics.min_latency_ms,
            "max_latency_ms": self.metrics.max_latency_ms,
        }

    def cleanup(self):
        """リソースのクリーンアップ"""
        # センサーの破棄
        for sensor_id, sensor in self.sensors.items():
            try:
                sensor.stop()
                sensor.destroy()
            except Exception as e:
                logger.warning(f"Failed to destroy sensor {sensor_id}: {e}")

        # gRPCチャネルのクローズ
        try:
            self.channel.close()
        except Exception as e:
            logger.warning(f"Failed to close gRPC channel: {e}")

        logger.info(f"EgoAgent '{self.agent_id}' cleaned up")

    def __del__(self):
        """デストラクタ"""
        self.cleanup()
