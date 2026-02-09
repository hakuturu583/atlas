"""動画埋め込みベクトル生成サービス

NVIDIA NIM Cosmos Embed1を使用して動画ファイルから埋め込みベクトルを生成する。
Docker Python API経由でコンテナを管理し、API経由でembeddingを計算する。
"""

import base64
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

import docker
from docker.models.containers import Container
import httpx

logger = logging.getLogger(__name__)


class EmbeddingService:
    """動画埋め込みベクトル生成サービス"""

    def __init__(
        self,
        nim_image: str = "nvcr.io/nim/nvidia/cosmos-embed1:1.0.0",
        container_port: int = 8000,
        host_port: int = 8001,
        gpu_device: str = "0",
        timeout: int = 300
    ):
        """
        Args:
            nim_image: NIM Cosmos Embed1のDockerイメージ
            container_port: コンテナ内のポート
            host_port: ホスト側のポート（デフォルト: 8001）
            gpu_device: 使用するGPUデバイス（デフォルト: "0"）
            timeout: コンテナ起動のタイムアウト（秒）
        """
        self.nim_image = nim_image
        self.container_port = container_port
        self.host_port = host_port
        self.gpu_device = gpu_device
        self.timeout = timeout
        self.client = docker.from_env()
        self.container: Optional[Container] = None
        self.base_url = f"http://localhost:{host_port}"

        # 保存先ディレクトリ
        self.embeddings_dir = Path("data/embeddings")
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

    def start_container(self) -> None:
        """NIM Cosmos Embed1コンテナを起動"""
        logger.info(f"Starting NIM Cosmos Embed1 container on port {self.host_port}...")

        try:
            # 既存のコンテナをチェック
            existing_containers = self.client.containers.list(
                filters={"ancestor": self.nim_image}
            )
            for container in existing_containers:
                logger.info(f"Found existing container {container.id[:12]}, stopping...")
                container.stop()
                container.remove()

            # コンテナを起動
            self.container = self.client.containers.run(
                self.nim_image,
                detach=True,
                ports={f"{self.container_port}/tcp": self.host_port},
                device_requests=[
                    docker.types.DeviceRequest(
                        device_ids=[self.gpu_device],
                        capabilities=[["gpu"]]
                    )
                ],
                environment={
                    "NVIDIA_VISIBLE_DEVICES": self.gpu_device,
                },
                shm_size="16g",
                remove=True  # コンテナ停止時に自動削除
            )

            logger.info(f"Container started: {self.container.id[:12]}")

            # ヘルスチェック
            self._wait_for_ready()
            logger.info("NIM Cosmos Embed1 is ready!")

        except docker.errors.ImageNotFound:
            logger.error(f"Image not found: {self.nim_image}")
            raise
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            raise

    def _wait_for_ready(self) -> None:
        """コンテナの準備完了を待機"""
        health_url = f"{self.base_url}/v1/health/ready"
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            try:
                with httpx.Client() as client:
                    response = client.get(health_url, timeout=5.0)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("message") == "NIM Service is ready":
                            return
            except (httpx.RequestError, httpx.TimeoutException):
                pass

            logger.debug("Waiting for NIM to be ready...")
            time.sleep(5)

        raise TimeoutError(f"NIM failed to be ready within {self.timeout} seconds")

    def stop_container(self) -> None:
        """コンテナを停止"""
        if self.container:
            logger.info(f"Stopping container {self.container.id[:12]}...")
            try:
                self.container.stop(timeout=10)
                logger.info("Container stopped successfully")
            except docker.errors.APIError as e:
                logger.error(f"Error stopping container: {e}")
            finally:
                self.container = None

    def compute_embedding(
        self,
        video_path: Path,
        request_type: str = "query",
        model: str = "nvidia/cosmos-embed1"
    ) -> Dict[str, Any]:
        """動画からembeddingを計算

        Args:
            video_path: 動画ファイルのパス
            request_type: リクエストタイプ（query, bulk_video）
            model: 使用するモデル

        Returns:
            API応答（embedding含む）
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        logger.info(f"Computing embedding for {video_path.name}...")

        # 動画をBase64エンコード
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        video_b64 = base64.b64encode(video_bytes).decode("utf-8")

        # リクエストペイロード
        # mp4形式を明示的に指定
        payload = {
            "input": [f"data:video/mp4;base64,{video_b64}"],
            "request_type": request_type,
            "encoding_format": "float",
            "model": model
        }

        # API呼び出し
        embeddings_url = f"{self.base_url}/v1/embeddings"
        with httpx.Client(timeout=120.0) as client:
            response = client.post(embeddings_url, json=payload)
            response.raise_for_status()
            result = response.json()

        logger.info(f"Embedding computed successfully (dim: {len(result['data'][0]['embedding'])})")
        return result

    def save_embedding(
        self,
        embedding_data: Dict[str, Any],
        scenario_uuid: str,
        save_numpy: bool = True
    ) -> Dict[str, str]:
        """Embeddingを保存

        Args:
            embedding_data: compute_embeddingの戻り値
            scenario_uuid: シナリオUUID
            save_numpy: NumPy形式でも保存するか

        Returns:
            保存されたファイルのパス
        """
        paths = {}

        # JSON形式で保存
        json_path = self.embeddings_dir / f"{scenario_uuid}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(embedding_data, f, indent=2)
        paths["json"] = str(json_path)
        logger.info(f"Embedding saved to {json_path}")

        # NumPy形式でも保存（オプション）
        if save_numpy:
            import numpy as np
            embedding_vector = embedding_data["data"][0]["embedding"]
            npy_path = self.embeddings_dir / f"{scenario_uuid}.npy"
            np.save(npy_path, embedding_vector)
            paths["numpy"] = str(npy_path)
            logger.info(f"Embedding vector saved to {npy_path}")

        return paths

    def process_video(
        self,
        video_path: Path,
        scenario_uuid: str,
        auto_stop: bool = True
    ) -> Dict[str, Any]:
        """動画を処理してembeddingを計算・保存（ワンストップ）

        Args:
            video_path: 動画ファイルのパス
            scenario_uuid: シナリオUUID
            auto_stop: 処理後にコンテナを自動停止するか

        Returns:
            処理結果（embedding_data, saved_paths）
        """
        try:
            # コンテナ起動（未起動の場合）
            if not self.container:
                self.start_container()

            # Embedding計算
            embedding_data = self.compute_embedding(video_path)

            # 保存
            saved_paths = self.save_embedding(embedding_data, scenario_uuid)

            logger.info(f"Video processing completed for {scenario_uuid}")
            return {
                "success": True,
                "embedding_data": embedding_data,
                "saved_paths": saved_paths,
                "video_path": str(video_path),
                "scenario_uuid": scenario_uuid
            }

        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return {
                "success": False,
                "error": str(e),
                "video_path": str(video_path),
                "scenario_uuid": scenario_uuid
            }

        finally:
            if auto_stop:
                self.stop_container()

    def __enter__(self):
        """コンテキストマネージャー: 起動"""
        self.start_container()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー: 停止"""
        self.stop_container()


# グローバルインスタンス（シングルトン的に使用）
embedding_service = EmbeddingService()
