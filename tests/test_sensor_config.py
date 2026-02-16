#!/usr/bin/env python3
"""
Phase 2検証: SensorConfig とURDF読み込みのテスト
"""

from agent_controller.sensor_config import (
    SensorConfig,
    NUSCENES_CAMERAS,
    SINGLE_CAMERA,
    LIDAR_CAMERA,
)


def test_nuscenes_cameras():
    """NuScenesカメラ配置のテスト"""
    print("📷 Testing NuScenes Cameras...")

    config = NUSCENES_CAMERAS()

    assert config.name == "nuscenes_sensors"
    assert len(config) == 6, f"Expected 6 sensors, got {len(config)}"

    # CAM_FRONTの確認
    cam_front = config.get_sensor("CAM_FRONT")
    assert cam_front is not None
    assert cam_front.sensor_type == "sensor.camera.rgb"
    assert abs(cam_front.x - 1.70) < 0.01
    assert abs(cam_front.y - 0.0) < 0.01
    assert abs(cam_front.z - 1.54) < 0.01
    assert cam_front.parameters["image_size_x"] == 1600
    assert cam_front.parameters["image_size_y"] == 900
    assert cam_front.parameters["fov"] == 70

    # CAM_FRONT_LEFTの確認
    cam_front_left = config.get_sensor("CAM_FRONT_LEFT")
    assert cam_front_left is not None
    assert abs(cam_front_left.x - 1.52) < 0.01
    assert abs(cam_front_left.y - 0.49) < 0.01
    assert abs(cam_front_left.yaw - 55.0) < 1.0  # 55度

    # 全センサーIDの確認
    sensor_ids = [s.sensor_id for s in config.sensors]
    expected_ids = [
        "CAM_FRONT",
        "CAM_FRONT_LEFT",
        "CAM_FRONT_RIGHT",
        "CAM_BACK",
        "CAM_BACK_LEFT",
        "CAM_BACK_RIGHT",
    ]
    for expected_id in expected_ids:
        assert expected_id in sensor_ids, f"Missing sensor: {expected_id}"

    print(f"  ✓ Loaded {len(config)} sensors")
    print(f"  ✓ Sensor IDs: {', '.join(sensor_ids)}")
    print("  ✓ NuScenes Cameras test passed")


def test_single_camera():
    """シングルカメラのテスト"""
    print("📷 Testing Single Camera...")

    config = SINGLE_CAMERA()

    assert config.name == "single_camera"
    assert len(config) == 1

    cam = config.get_sensor("CAM_FRONT")
    assert cam is not None
    assert cam.sensor_type == "sensor.camera.rgb"
    assert abs(cam.x - 2.0) < 0.01
    assert cam.parameters["image_size_x"] == 1920
    assert cam.parameters["image_size_y"] == 1080

    print(f"  ✓ Loaded {len(config)} sensor")
    print("  ✓ Single Camera test passed")


def test_lidar_camera():
    """LiDAR + カメラのテスト"""
    print("📷 Testing LiDAR + Camera...")

    config = LIDAR_CAMERA()

    assert config.name == "lidar_camera"
    assert len(config) == 2

    # カメラ
    cam = config.get_sensor("CAM_FRONT")
    assert cam is not None
    assert cam.sensor_type == "sensor.camera.rgb"

    # LiDAR
    lidar = config.get_sensor("LIDAR_TOP")
    assert lidar is not None
    assert lidar.sensor_type == "sensor.lidar.ray_cast"
    assert abs(lidar.z - 2.5) < 0.01
    assert lidar.parameters["channels"] == 64
    assert lidar.parameters["range"] == 100.0

    print(f"  ✓ Loaded {len(config)} sensors")
    print("  ✓ LiDAR + Camera test passed")


def test_carla_transform():
    """CARLA Transform変換のテスト"""
    print("🔄 Testing CARLA Transform conversion...")

    config = NUSCENES_CAMERAS()
    cam_front = config.get_sensor("CAM_FRONT")

    transform = cam_front.to_carla_transform()
    x, y, z, pitch, yaw, roll = transform

    assert abs(x - 1.70) < 0.01
    assert abs(y - 0.0) < 0.01
    assert abs(z - 1.54) < 0.01
    assert abs(pitch - 0.0) < 0.01
    assert abs(yaw - 0.0) < 0.01
    assert abs(roll - 0.0) < 0.01

    print("  ✓ CARLA Transform conversion test passed")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 2 Verification: SensorConfig Tests")
    print("=" * 70)
    print()

    test_nuscenes_cameras()
    print()
    test_single_camera()
    print()
    test_lidar_camera()
    print()
    test_carla_transform()
    print()
    print("=" * 70)
    print("✅ All Phase 2 tests passed!")
    print("=" * 70)
