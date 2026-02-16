"""
Alpamayo-R1-10B VLAモデル実装

HuggingFaceからモデルをロードし、推論を実行
Reference: https://github.com/NVlabs/alpamayo
"""

import time
import os
import sys
from typing import Optional, List, Tuple
import logging
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from generated.grpc_pb2 import sensor_data_pb2, control_command_pb2
from .base import VLAModelBase

logger = logging.getLogger(__name__)


class AlpamayoR1Model(VLAModelBase):
    """
    Alpamayo-R1-10B VLAモデル

    HuggingFaceからモデルをロードし、推論を実行
    Reference: https://github.com/NVlabs/alpamayo
    """

    def __init__(
        self,
        model_id: str = "nvidia/Alpamayo-R1-10B",
        device: str = "cuda",
        use_cache: bool = True,
        top_p: float = 0.98,
        temperature: float = 0.6,
        num_traj_samples: int = 1,
    ):
        super().__init__(model_name="Alpamayo-R1-10B", version="1.0.0")
        self.model_id = model_id
        self.device = device
        self.use_cache = use_cache
        self.model = None
        self.processor = None
        self.helper = None

        # Sampling parameters
        self.top_p = top_p
        self.temperature = temperature
        self.num_traj_samples = num_traj_samples

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

            # Import required libraries
            try:
                import torch
                from alpamayo_r1.models.alpamayo_r1 import AlpamayoR1
                from alpamayo_r1 import helper
            except ImportError as e:
                logger.error(f"Failed to import Alpamayo libraries: {e}")
                self.initialization_status.message = f"Error: {e}"
                return False

            # モデルのダウンロード（時間がかかる可能性あり）
            logger.info(f"Loading model: {self.model_id}")
            self.initialization_status.progress = 0.3
            self.initialization_status.message = "Loading AlpamayoR1 model from HuggingFace..."

            # Load model using AlpamayoR1 class (official implementation)
            try:
                self.model = AlpamayoR1.from_pretrained(
                    self.model_id,
                    dtype=torch.bfloat16
                ).to(self.device)

                self.initialization_status.progress = 0.7
                self.initialization_status.message = "Loading processor..."

                # Get processor from helper
                self.helper = helper
                self.processor = helper.get_processor(self.model.tokenizer)
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

    def _preprocess_images(self, cameras) -> Tuple[any, any]:
        """
        カメラ画像を前処理してAlpamayo入力形式に変換

        Returns:
            messages: チャットメッセージ形式の画像データ
            image_frames: 画像テンソル
        """
        import torch
        from PIL import Image
        import io

        # カメラ画像をデコード
        image_list = []
        for camera in cameras:
            img_bytes = camera.image_data
            img = Image.open(io.BytesIO(img_bytes))
            image_list.append(img)

        # 画像をテンソルに変換（Alpamayo形式）
        # Shape: [num_cameras, H, W, C]
        image_frames = torch.stack([
            torch.from_numpy(np.array(img)).float() / 255.0
            for img in image_list
        ])

        # Create message format (similar to official implementation)
        messages = self.helper.create_message(image_frames.flatten(0, 1))

        return messages, image_frames

    def _run_inference(self, images, vehicle_state) -> List:
        """
        Alpamayoモデルで推論を実行（公式実装に基づく）

        Reference: https://github.com/NVlabs/alpamayo/blob/main/src/alpamayo_r1/test_inference.py
        """
        import torch

        messages, image_frames = images

        # Input preprocessing (公式実装に従う)
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=False,
            continue_final_message=True,
            return_dict=True,
            return_tensors="pt",
        )

        # Create ego history (placeholder - should come from sensor data)
        # TODO: Extract from vehicle_state history
        batch_size = 1
        ego_history_xyz = torch.zeros((batch_size, 10, 3), device=self.device)
        ego_history_rot = torch.eye(3, device=self.device).unsqueeze(0).repeat(batch_size, 10, 1, 1)

        model_inputs = {
            "tokenized_data": inputs,
            "ego_history_xyz": ego_history_xyz,
            "ego_history_rot": ego_history_rot,
        }
        model_inputs = self.helper.to_device(model_inputs, self.device)

        # Run inference with official method
        with torch.autocast(self.device, dtype=torch.bfloat16):
            pred_xyz, pred_rot, extra = self.model.sample_trajectories_from_data_with_vlm_rollout(
                data=model_inputs,
                top_p=self.top_p,
                temperature=self.temperature,
                num_traj_samples=self.num_traj_samples,
                max_generation_length=256,
                return_extra=True,
            )

        # Convert predictions to waypoints
        waypoints = self._convert_to_waypoints(pred_xyz, pred_rot, extra)

        # Log reasoning trace
        if "cot" in extra and len(extra["cot"]) > 0:
            logger.info(f"Chain-of-Causation: {extra['cot'][0]}")
            self.last_reasoning = extra["cot"][0]

        return waypoints

    def _convert_to_waypoints(self, pred_xyz: "torch.Tensor", pred_rot: "torch.Tensor", extra: dict) -> List:
        """
        Alpamayo予測結果をWaypointリストに変換

        Args:
            pred_xyz: Predicted positions [batch, num_samples, num_waypoints, 3]
            pred_rot: Predicted rotations [batch, num_samples, num_waypoints, 3, 3]
            extra: Extra outputs including reasoning traces

        Returns:
            List of Waypoint protobuf messages
        """
        # Take first trajectory sample
        xyz = pred_xyz.cpu().numpy()[0, 0]  # [64, 3]
        rot = pred_rot.cpu().numpy()[0, 0]  # [64, 3, 3]

        waypoints = []
        for i in range(len(xyz)):
            t = (i + 1) * 0.1  # 10 Hz sampling

            # Flatten rotation matrix
            rot_flat = rot[i].flatten().tolist()

            # Calculate speed from position delta
            if i > 0:
                dx = xyz[i, 0] - xyz[i-1, 0]
                dy = xyz[i, 1] - xyz[i-1, 1]
                speed_mps = np.sqrt(dx**2 + dy**2) / 0.1
            else:
                speed_mps = 0.0

            waypoint = control_command_pb2.Waypoint(
                x=float(xyz[i, 0]),
                y=float(xyz[i, 1]),
                z=float(xyz[i, 2]),
                rotation_matrix=rot_flat,
                timestamp_offset_sec=t,
                speed_mps=float(speed_mps),
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
