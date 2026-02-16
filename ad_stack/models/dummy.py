"""
ダミーVLAモデル実装

テスト用のシンプルなルールベースVLAモデル
"""

import time
import math
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from generated.grpc_pb2 import sensor_data_pb2, control_command_pb2
from .base import VLAModelBase


class DummyVLAModel(VLAModelBase):
    """
    ダミーVLAモデル

    シンプルなルールベース制御を行う。
    - 前方へ直進
    - 目標速度: 30 km/h
    """

    def __init__(self):
        super().__init__(model_name="DummyVLA", version="1.0.0")

    def initialize(self) -> bool:
        """初期化（ダミーなので即座に完了）"""
        self.initialization_status.stage = "initializing"
        self.initialization_status.progress = 0.0
        self.initialization_status.message = "Starting dummy initialization..."

        # ダミー初期化シミュレーション
        for i in range(10):
            time.sleep(0.1)
            self.initialization_status.progress = (i + 1) / 10.0
            self.initialization_status.message = f"Loading... {(i+1)*10}%"

        self.initialization_status.stage = "ready"
        self.initialization_status.message = "Dummy model ready"
        self.initialization_status.is_ready = True

        return True

    def predict(
        self, sensor_bundle: sensor_data_pb2.SensorDataBundle
    ) -> control_command_pb2.VLAOutput:
        """
        ダミー予測（ルールベース制御）

        Args:
            sensor_bundle: センサーデータバンドル

        Returns:
            VLAOutput: Waypoint軌跡を返す
        """
        # 現在の車両状態
        vehicle_state = sensor_bundle.vehicle_state
        current_speed = vehicle_state.speed_kmh

        # 目標速度
        target_speed_kmh = 30.0
        target_speed_mps = target_speed_kmh / 3.6

        # 前方へのWaypoint軌跡を生成（64個、10Hz）
        waypoints = []
        for i in range(64):
            t = (i + 1) * 0.1  # 0.1秒刻み

            # 等速直線運動を仮定
            x = target_speed_mps * t
            y = 0.0
            z = 0.0

            # 単位行列（回転なし）
            rotation_matrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]

            waypoint = control_command_pb2.Waypoint(
                x=x,
                y=y,
                z=z,
                rotation_matrix=rotation_matrix,
                timestamp_offset_sec=t,
                speed_mps=target_speed_mps,
            )
            waypoints.append(waypoint)

        trajectory = control_command_pb2.WaypointTrajectory(
            waypoints=waypoints,
            prediction_horizon_sec=6.4,
            sampling_rate_hz=10,
            coordinate_frame="ego",
        )

        # 推論トレース
        reasoning = (
            f"Dummy VLA: Maintaining {target_speed_kmh:.1f} km/h. "
            f"Current speed: {current_speed:.1f} km/h. Going straight."
        )

        vla_output = control_command_pb2.VLAOutput(
            waypoint_trajectory=trajectory,
            model_name=self.model_name,
            model_version=self.version,
            reasoning_trace=reasoning,
            timestamp_ns=sensor_bundle.timestamp_ns,
            overall_confidence=0.9,
        )
        vla_output.confidence_scores["trajectory"] = 0.9
        vla_output.confidence_scores["safety"] = 0.95

        return vla_output
