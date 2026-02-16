#!/usr/bin/env python3
"""
VLA gRPCサーバー

環境変数:
- VLA_MODEL: 使用するモデル ("dummy", "alpamayo") [default: dummy]
- VLA_PORT: gRPCポート [default: 50051]
- VLA_MAX_WORKERS: 最大ワーカー数 [default: 10]
"""

import logging
import os
import sys
import signal
import threading

# 絶対インポートを使用（python -m ad_stack.server で実行するため）
from ad_stack.common.grpc_server import serve
from ad_stack.models.dummy import DummyVLAModel
from ad_stack.models.alpamayo import AlpamayoR1Model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    # 環境変数から設定を取得
    model_type = os.getenv("VLA_MODEL", "dummy")
    port = int(os.getenv("VLA_PORT", "50051"))
    max_workers = int(os.getenv("VLA_MAX_WORKERS", "10"))

    logger.info("=" * 60)
    logger.info("VLA gRPC Server Starting")
    logger.info("=" * 60)
    logger.info(f"Model: {model_type}")
    logger.info(f"Port: {port}")
    logger.info(f"Max workers: {max_workers}")
    logger.info("=" * 60)

    # VLAモデルを選択
    if model_type == "dummy":
        vla_model = DummyVLAModel()
    elif model_type == "alpamayo":
        vla_model = AlpamayoR1Model()
    else:
        logger.error(f"Unknown model type: {model_type}")
        sys.exit(1)

    # バックグラウンドでモデル初期化
    def initialize_model():
        logger.info("Initializing model in background...")
        success = vla_model.initialize()
        if success:
            logger.info("✓ Model initialization completed")
        else:
            logger.error("✗ Model initialization failed")

    init_thread = threading.Thread(target=initialize_model, daemon=True)
    init_thread.start()

    # gRPCサーバーを起動
    server = serve(vla_model, port=port, max_workers=max_workers)

    # シグナルハンドラー設定
    def signal_handler(sig, frame):
        logger.info("\nShutting down server...")
        server.stop(grace=5)
        vla_model.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # サーバー実行
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
        server.stop(grace=5)
        vla_model.shutdown()


if __name__ == "__main__":
    main()
