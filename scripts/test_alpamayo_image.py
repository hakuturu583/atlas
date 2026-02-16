#!/usr/bin/env python3
"""
Alpamayo-R1 Docker Image Test Script

Dockerイメージをビルドして起動し、gRPC通信をテストします。
合格したらDocker Hubにプッシュします。
"""

import subprocess
import time
import sys
import grpc
from PIL import Image
import io
import numpy as np

# gRPC protobuf imports
try:
    from generated.grpc_pb2 import sensor_data_pb2, control_command_pb2, ad_stack_pb2_grpc
except ImportError:
    print("❌ Error: gRPC protobuf files not found. Run 'make generate-grpc' first.")
    sys.exit(1)


class AlpamayoImageTester:
    def __init__(self, image_name: str = "hakuturu583/alpamayo-r1:latest"):
        self.image_name = image_name
        self.container_name = "test-alpamayo-r1"
        self.port = 50051

    def build_image(self) -> bool:
        """Dockerイメージをビルド"""
        print("=" * 60)
        print("Step 1: Building Docker image...")
        print("=" * 60)

        cmd = [
            "docker", "build",
            "-t", self.image_name,
            "-f", "docker/Dockerfile.alpamayo",
            "."
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✓ Docker image built successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build image: {e}")
            print(f"stderr: {e.stderr}")
            return False

    def start_container(self) -> bool:
        """コンテナを起動"""
        print("\n" + "=" * 60)
        print("Step 2: Starting container...")
        print("=" * 60)

        # 既存のコンテナを削除
        subprocess.run(
            ["docker", "rm", "-f", self.container_name],
            capture_output=True
        )

        cmd = [
            "docker", "run",
            "-d",
            "--name", self.container_name,
            "-p", f"{self.port}:{self.port}",
            "-e", "VLA_MODEL=alpamayo",
            "-e", "VLA_PORT=50051",
            self.image_name
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✓ Container started: {self.container_name}")
            print(f"  Container ID: {result.stdout.strip()[:12]}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start container: {e}")
            return False

    def wait_for_ready(self, timeout: int = 60) -> bool:
        """コンテナが準備完了するまで待機"""
        print("\n" + "=" * 60)
        print("Step 3: Waiting for container to be ready...")
        print("=" * 60)

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # ログを確認
                result = subprocess.run(
                    ["docker", "logs", self.container_name],
                    capture_output=True,
                    text=True
                )

                logs = result.stdout + result.stderr

                if "Server started" in logs or "Listening on" in logs:
                    print("✓ Container is ready")
                    return True

                # エラーチェック
                if "Error" in logs or "Failed" in logs:
                    print(f"❌ Container error detected:")
                    print(logs[-500:])  # 最後の500文字を表示
                    return False

                print(f"  Waiting... ({int(time.time() - start_time)}s)")
                time.sleep(5)

            except Exception as e:
                print(f"❌ Error checking logs: {e}")
                return False

        print(f"❌ Timeout waiting for container to be ready")
        return False

    def test_grpc_connection(self) -> bool:
        """gRPC接続をテスト"""
        print("\n" + "=" * 60)
        print("Step 4: Testing gRPC connection...")
        print("=" * 60)

        try:
            channel = grpc.insecure_channel(f'localhost:{self.port}')
            stub = ad_stack_pb2_grpc.VLAServiceStub(channel)

            # ダミー画像を作成
            print("  Creating dummy sensor data...")
            img = Image.new('RGB', (800, 600), color=(73, 109, 137))
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()

            # センサーデータを構築
            sensor_data = sensor_data_pb2.SensorData(
                timestamp=time.time(),
                frame_id=1
            )

            # カメラデータを追加
            camera_data = sensor_data_pb2.CameraData(
                sensor_id="test_camera",
                image_data=img_bytes,
                width=800,
                height=600,
                encoding="jpeg"
            )
            sensor_data.cameras.append(camera_data)

            # 車両状態を追加
            vehicle_state = sensor_data_pb2.VehicleState(
                velocity=10.0,
                acceleration=0.5,
                steering_angle=0.0
            )
            sensor_data.vehicle_state.CopyFrom(vehicle_state)

            print("  Sending request to VLA service...")
            # タイムアウトを設定
            response = stub.ProcessSensorData(sensor_data, timeout=30)

            print(f"✓ Received response:")
            print(f"    Throttle: {response.throttle:.3f}")
            print(f"    Steer: {response.steer:.3f}")
            print(f"    Brake: {response.brake:.3f}")
            print(f"    Processing time: {response.processing_time_ms:.1f}ms")

            channel.close()
            return True

        except grpc.RpcError as e:
            print(f"❌ gRPC error: {e.code()}: {e.details()}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def cleanup(self):
        """コンテナをクリーンアップ"""
        print("\n" + "=" * 60)
        print("Cleanup: Stopping and removing container...")
        print("=" * 60)

        subprocess.run(
            ["docker", "stop", self.container_name],
            capture_output=True
        )
        subprocess.run(
            ["docker", "rm", self.container_name],
            capture_output=True
        )
        print("✓ Container cleaned up")

    def push_to_dockerhub(self) -> bool:
        """Docker Hubにプッシュ"""
        print("\n" + "=" * 60)
        print("Step 5: Pushing image to Docker Hub...")
        print("=" * 60)

        cmd = ["docker", "push", self.image_name]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✓ Image pushed successfully: {self.image_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to push image: {e}")
            print(f"stderr: {e.stderr}")
            return False

    def run_full_test(self) -> bool:
        """完全なテストを実行"""
        print("\n")
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 10 + "Alpamayo-R1 Docker Image Test" + " " * 18 + "║")
        print("╚" + "═" * 58 + "╝")
        print()

        try:
            # Step 1: Build
            if not self.build_image():
                return False

            # Step 2: Start container
            if not self.start_container():
                return False

            # Step 3: Wait for ready
            if not self.wait_for_ready():
                self.cleanup()
                return False

            # Step 4: Test gRPC
            if not self.test_grpc_connection():
                self.cleanup()
                return False

            # Cleanup
            self.cleanup()

            # Step 5: Push to Docker Hub
            print("\n" + "=" * 60)
            print("All tests passed! ✓")
            print("=" * 60)

            user_input = input("\nPush to Docker Hub? (y/N): ").strip().lower()
            if user_input == 'y':
                return self.push_to_dockerhub()
            else:
                print("Skipped pushing to Docker Hub")
                return True

        except KeyboardInterrupt:
            print("\n\n❌ Test interrupted by user")
            self.cleanup()
            return False
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()
            return False


def main():
    tester = AlpamayoImageTester()
    success = tester.run_full_test()

    if success:
        print("\n" + "=" * 60)
        print("SUCCESS: Image is ready for deployment! 🚀")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("FAILED: Image testing failed ❌")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
