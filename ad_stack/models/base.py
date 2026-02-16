"""
VLAモデル基底クラス

すべてのVLAモデル実装が継承する抽象基底クラス
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import sys
import os

# generated/grpc_pb2をインポートパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from generated.grpc_pb2 import sensor_data_pb2, control_command_pb2


@dataclass
class InitializationStatus:
    """初期化状態"""

    progress: float = 0.0  # 0.0 ~ 1.0
    stage: str = "not_started"
    message: str = ""
    is_ready: bool = False


class VLAModelBase(ABC):
    """
    VLAモデル基底クラス

    すべてのVLAモデル実装はこのクラスを継承する。
    """

    def __init__(self, model_name: str, version: str = "1.0.0"):
        self.model_name = model_name
        self.version = version
        self.initialization_status = InitializationStatus()

    @abstractmethod
    def initialize(self) -> bool:
        """
        モデルを初期化（重みのダウンロード、モデルのロードなど）

        Returns:
            bool: 成功した場合True
        """
        pass

    @abstractmethod
    def predict(
        self, sensor_bundle: sensor_data_pb2.SensorDataBundle
    ) -> control_command_pb2.VLAOutput:
        """
        センサーデータからVLA出力を生成

        Args:
            sensor_bundle: センサーデータバンドル

        Returns:
            VLAOutput: VLA出力
        """
        pass

    def get_initialization_status(self) -> InitializationStatus:
        """初期化状態を取得"""
        return self.initialization_status

    def is_ready(self) -> bool:
        """モデルが使用可能か"""
        return self.initialization_status.is_ready

    def shutdown(self):
        """リソースのクリーンアップ"""
        pass
