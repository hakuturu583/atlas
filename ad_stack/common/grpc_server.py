"""
gRPCサーバー共通コード

VLAServiceの実装
"""

import logging
import sys
import os
from concurrent import futures

import grpc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from generated.grpc_pb2 import (
    sensor_data_pb2,
    control_command_pb2,
    ad_stack_pb2,
    ad_stack_pb2_grpc,
)

logger = logging.getLogger(__name__)


class VLAServicer(ad_stack_pb2_grpc.VLAServiceServicer):
    """
    VLAService実装

    VLAモデルをラップしてgRPC経由で提供
    """

    def __init__(self, vla_model):
        """
        Args:
            vla_model: VLAModelBaseを継承したモデルインスタンス
        """
        self.vla_model = vla_model

    def ProcessSensorData(self, request, context):
        """センサーデータを処理してVLA出力を返す"""
        try:
            if not self.vla_model.is_ready():
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details("Model not initialized yet")
                return control_command_pb2.VLAOutput()

            vla_output = self.vla_model.predict(request)
            return vla_output

        except Exception as e:
            logger.error(f"ProcessSensorData error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return control_command_pb2.VLAOutput()

    def ProcessSensorDataBatch(self, request, context):
        """バッチ処理"""
        try:
            if not self.vla_model.is_ready():
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details("Model not initialized yet")
                return ad_stack_pb2.SensorDataBatchResponse()

            vla_outputs = []
            responses = []

            for bundle in request.bundles:
                try:
                    vla_output = self.vla_model.predict(bundle)
                    vla_outputs.append(vla_output)

                    response = control_command_pb2.ControlResponse(
                        success=True,
                        timestamp_ns=bundle.timestamp_ns,
                    )
                    responses.append(response)

                except Exception as e:
                    logger.error(f"Batch item processing error: {e}")
                    # エラー時は空の出力
                    vla_outputs.append(control_command_pb2.VLAOutput())
                    responses.append(
                        control_command_pb2.ControlResponse(
                            success=False, error_message=str(e)
                        )
                    )

            return ad_stack_pb2.SensorDataBatchResponse(
                vla_outputs=vla_outputs, responses=responses
            )

        except Exception as e:
            logger.error(f"ProcessSensorDataBatch error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ad_stack_pb2.SensorDataBatchResponse()

    def HealthCheck(self, request, context):
        """ヘルスチェック"""
        try:
            status_enum = ad_stack_pb2.HealthCheckResponse

            # 初期化状態を取得
            init_status = self.vla_model.get_initialization_status()

            if init_status.is_ready:
                status = status_enum.SERVING
            elif init_status.stage in ["not_started", "initializing", "downloading_weights", "loading_model", "compiling"]:
                status = status_enum.INITIALIZING
            else:
                status = status_enum.NOT_SERVING

            response = ad_stack_pb2.HealthCheckResponse(
                status=status,
                version=self.vla_model.version,
                model_name=self.vla_model.model_name,
                initialization_progress=init_status.progress,
                initialization_stage=init_status.stage,
                initialization_message=init_status.message,
            )

            response.metadata["device"] = "cuda"  # TODO: 実際のデバイスを取得

            return response

        except Exception as e:
            logger.error(f"HealthCheck error: {e}")
            return ad_stack_pb2.HealthCheckResponse(
                status=ad_stack_pb2.HealthCheckResponse.UNKNOWN
            )

    def Reset(self, request, context):
        """VLAモデルをリセット"""
        try:
            logger.info(f"Reset requested for scenario: {request.scenario_id}")

            # モデルのリセット処理（必要に応じて実装）
            # 例: 内部状態のクリア、キャッシュのクリアなど

            return ad_stack_pb2.ResetResponse(
                success=True, message=f"Reset for scenario {request.scenario_id}"
            )

        except Exception as e:
            logger.error(f"Reset error: {e}")
            return ad_stack_pb2.ResetResponse(success=False, message=str(e))


def serve(vla_model, port: int = 50051, max_workers: int = 10):
    """
    gRPCサーバーを起動

    Args:
        vla_model: VLAモデルインスタンス
        port: ポート番号
        max_workers: 最大ワーカー数
    """
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )

    ad_stack_pb2_grpc.add_VLAServiceServicer_to_server(
        VLAServicer(vla_model), server
    )

    server.add_insecure_port(f"[::]:{port}")

    logger.info(f"Starting VLA gRPC server on port {port}...")
    server.start()

    logger.info(f"VLA server listening on port {port}")
    logger.info(f"Model: {vla_model.model_name} v{vla_model.version}")

    return server
