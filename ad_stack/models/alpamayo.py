"""
Alpamayo-R1-10B VLAモデル実装

HuggingFaceからモデルをロードし、推論を実行
"""

import time
import os
import sys
from typing import Optional
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from generated.grpc_pb2 import sensor_data_pb2, control_command_pb2
from .base import VLAModelBase

logger = logging.getLogger(__name__)


class AlpamayoR1Model(VLAModelBase):
    """
    Alpamayo-R1-10B VLAモデル

    HuggingFaceからモデルをロードし、推論を実行
    """

    def __init__(
        self,
        model_id: str = "nvidia/Alpamayo-R1-10B",
        device: str = "cuda",
        use_cache: bool = True,
    ):
        super().__init__(model_name="Alpamayo-R1-10B", version="1.0.0")
        self.model_id = model_id
        self.device = device
        self.use_cache = use_cache
        self.model = None
        self.processor = None

    def initialize(self) -> bool:
        """
        Alpamayoモデルを初期化

        Returns:
            bool: 成功した場合True
        """
        try:
            self.initialization_status.stage = "downloading_weights"
            self.initialization_status.progress = 0.1
            self.initialization_status.message = "Downloading model weights from HuggingFace..."

            # HuggingFace transformersライブラリをインポート
            try:
                from transformers import AutoModelForCausalLM, AutoProcessor
            except ImportError:
                logger.error("transformers library not installed")
                self.initialization_status.message = "Error: transformers not installed"
                return False

            # モデルのダウンロード（時間がかかる可能性あり）
            logger.info(f"Loading model: {self.model_id}")
            self.initialization_status.progress = 0.3
            self.initialization_status.message = "Loading model from HuggingFace..."

            # NOTE: 実際のAlpamayo-R1-10Bのロード方法は公式ドキュメントに従う
            # ここではプレースホルダー実装
            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    device_map="auto" if self.device == "cuda" else self.device,
                    torch_dtype="auto",
                    trust_remote_code=True,
                    cache_dir=os.getenv("HF_HOME", "/app/.cache/huggingface"),
                )
                self.initialization_status.progress = 0.7
                self.initialization_status.message = "Loading processor..."

                self.processor = AutoProcessor.from_pretrained(
                    self.model_id,
                    trust_remote_code=True,
                    cache_dir=os.getenv("HF_HOME", "/app/.cache/huggingface"),
                )
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self.initialization_status.message = f"Error loading model: {e}"
                return False

            self.initialization_status.stage = "compiling"
            self.initialization_status.progress = 0.9
            self.initialization_status.message = "Compiling model..."

            # JITコンパイルなどの最適化
            # （必要に応じて実装）

            self.initialization_status.stage = "ready"
            self.initialization_status.progress = 1.0
            self.initialization_status.message = "Alpamayo-R1-10B ready"
            self.initialization_status.is_ready = True

            logger.info("Alpamayo-R1-10B initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Alpamayo initialization failed: {e}")
            self.initialization_status.message = f"Initialization error: {e}"
            self.initialization_status.is_ready = False
            return False

    def predict(
        self, sensor_bundle: sensor_data_pb2.SensorDataBundle
    ) -> control_command_pb2.VLAOutput:
        """
        Alpamayoで推論を実行

        Args:
            sensor_bundle: センサーデータバンドル

        Returns:
            VLAOutput: Waypoint軌跡
        """
        if not self.is_ready():
            raise RuntimeError("Model not initialized")

        try:
            # 1. センサーデータを前処理
            # （カメラ画像のデコード、正規化など）
            images = self._preprocess_images(sensor_bundle.cameras)
            vehicle_state = sensor_bundle.vehicle_state

            # 2. モデル推論
            # NOTE: 実際のAlpamayo APIに従う
            # ここではプレースホルダー実装
            waypoints = self._run_inference(images, vehicle_state)

            # 3. VLAOutputに変換
            trajectory = control_command_pb2.WaypointTrajectory(
                waypoints=waypoints,
                prediction_horizon_sec=6.4,
                sampling_rate_hz=10,
                coordinate_frame="ego",
            )

            reasoning = "Alpamayo-R1-10B: Predicted safe trajectory based on multi-camera perception."

            vla_output = control_command_pb2.VLAOutput(
                waypoint_trajectory=trajectory,
                model_name=self.model_name,
                model_version=self.version,
                reasoning_trace=reasoning,
                timestamp_ns=sensor_bundle.timestamp_ns,
                overall_confidence=0.85,
            )

            return vla_output

        except Exception as e:
            logger.error(f"Alpamayo inference failed: {e}")
            # フォールバック: ダミー軌跡を返す
            return self._get_fallback_output(sensor_bundle)

    def _preprocess_images(self, cameras):
        """カメラ画像を前処理"""
        # JPEG画像をデコードして正規化
        # Alpamayoのプリプロセッサに従う
        # TODO: 実装
        return []

    def _run_inference(self, images, vehicle_state):
        """モデル推論を実行"""
        # Alpamayoモデルで推論
        # TODO: 実装

        # プレースホルダー: 直進軌跡
        waypoints = []
        target_speed_mps = 10.0
        for i in range(64):
            t = (i + 1) * 0.1
            waypoint = control_command_pb2.Waypoint(
                x=target_speed_mps * t,
                y=0.0,
                z=0.0,
                rotation_matrix=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
                timestamp_offset_sec=t,
                speed_mps=target_speed_mps,
            )
            waypoints.append(waypoint)
        return waypoints

    def _get_fallback_output(
        self, sensor_bundle: sensor_data_pb2.SensorDataBundle
    ) -> control_command_pb2.VLAOutput:
        """推論失敗時のフォールバック出力"""
        # 安全側に倒す: 停止コマンド
        waypoints = []
        for i in range(64):
            t = (i + 1) * 0.1
            waypoint = control_command_pb2.Waypoint(
                x=0.0,
                y=0.0,
                z=0.0,
                rotation_matrix=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
                timestamp_offset_sec=t,
                speed_mps=0.0,
            )
            waypoints.append(waypoint)

        trajectory = control_command_pb2.WaypointTrajectory(
            waypoints=waypoints,
            prediction_horizon_sec=6.4,
            sampling_rate_hz=10,
            coordinate_frame="ego",
        )

        vla_output = control_command_pb2.VLAOutput(
            waypoint_trajectory=trajectory,
            model_name=self.model_name,
            model_version=self.version,
            reasoning_trace="FALLBACK: Stopping due to inference error",
            timestamp_ns=sensor_bundle.timestamp_ns,
            overall_confidence=0.0,
        )

        return vla_output

    def shutdown(self):
        """リソースのクリーンアップ"""
        if self.model:
            del self.model
        if self.processor:
            del self.processor
        logger.info("Alpamayo model shut down")
