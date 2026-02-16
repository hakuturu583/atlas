#!/usr/bin/env python3
"""
Phase 1検証: gRPCメッセージの生成とシリアライズテスト
"""

from generated.grpc_pb2 import sensor_data_pb2, control_command_pb2, ad_stack_pb2


def test_sensor_data_bundle():
    """SensorDataBundleメッセージの生成とシリアライズテスト"""
    print("📦 Testing SensorDataBundle...")

    # VehicleStateメッセージ
    vehicle_state = sensor_data_pb2.VehicleState(
        transform=sensor_data_pb2.Transform(
            location=sensor_data_pb2.Vector3(x=100.0, y=50.0, z=0.5),
            rotation=sensor_data_pb2.Vector3(x=0.0, y=0.0, z=90.0),
        ),
        velocity=sensor_data_pb2.Vector3(x=10.0, y=0.0, z=0.0),
        speed_kmh=36.0,
        throttle=0.5,
        brake=0.0,
        steering_angle=0.0,
        hand_brake=False,
        gear=1,
    )

    # CameraImageメッセージ
    camera = sensor_data_pb2.CameraImage(
        camera_id="CAM_FRONT",
        width=1600,
        height=900,
        image_data=b"fake_jpeg_data_here",
        timestamp_ns=1234567890000,
        transform=sensor_data_pb2.Transform(
            location=sensor_data_pb2.Vector3(x=1.70, y=0.0, z=1.54),
            rotation=sensor_data_pb2.Vector3(x=0.0, y=0.0, z=0.0),
        ),
    )

    # SensorDataBundleメッセージ
    bundle = sensor_data_pb2.SensorDataBundle(
        frame_number=100,
        timestamp_ns=1234567890000,
        vehicle_state=vehicle_state,
        cameras=[camera],
    )

    # シリアライズ
    serialized = bundle.SerializeToString()
    print(f"  ✓ Serialized size: {len(serialized)} bytes")

    # デシリアライズ
    bundle2 = sensor_data_pb2.SensorDataBundle()
    bundle2.ParseFromString(serialized)

    assert bundle2.frame_number == 100
    assert bundle2.vehicle_state.speed_kmh == 36.0
    assert len(bundle2.cameras) == 1
    assert bundle2.cameras[0].camera_id == "CAM_FRONT"

    print("  ✓ SensorDataBundle test passed")


def test_vla_output_waypoint():
    """VLAOutput（Waypoint系）のテスト - Alpamayo相当"""
    print("🚗 Testing VLAOutput (Waypoint Trajectory)...")

    # Waypoint軌跡を生成（Alpamayoスタイル）
    waypoints = []
    for i in range(5):
        waypoint = control_command_pb2.Waypoint(
            x=float(i * 2.0),           # 2m刻みで前進
            y=0.0,
            z=0.0,
            rotation_matrix=[            # 単位行列（回転なし）
                1.0, 0.0, 0.0,
                0.0, 1.0, 0.0,
                0.0, 0.0, 1.0,
            ],
            timestamp_offset_sec=i * 0.1,  # 0.1秒刻み（10Hz）
            speed_mps=10.0,                # 10 m/s
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
        model_name="Alpamayo-R1-10B",
        model_version="1.0.0",
        reasoning_trace="Detected clear road ahead. Maintaining speed and lane position.",
        timestamp_ns=1234567890000,
        overall_confidence=0.95,
    )
    vla_output.confidence_scores["trajectory"] = 0.95
    vla_output.confidence_scores["safety"] = 0.98

    # シリアライズ
    serialized = vla_output.SerializeToString()
    print(f"  ✓ Serialized size: {len(serialized)} bytes")

    # デシリアライズ
    vla_output2 = control_command_pb2.VLAOutput()
    vla_output2.ParseFromString(serialized)

    assert vla_output2.HasField("waypoint_trajectory")
    assert len(vla_output2.waypoint_trajectory.waypoints) == 5
    assert abs(vla_output2.waypoint_trajectory.waypoints[0].x - 0.0) < 0.0001
    assert abs(vla_output2.waypoint_trajectory.waypoints[4].x - 8.0) < 0.0001
    assert vla_output2.model_name == "Alpamayo-R1-10B"
    assert "clear road ahead" in vla_output2.reasoning_trace

    print("  ✓ VLAOutput (Waypoint) test passed")


def test_vla_output_discrete():
    """VLAOutput（離散アクション系）のテスト - RT-2相当"""
    print("🎮 Testing VLAOutput (Discrete Action)...")

    discrete_action = control_command_pb2.DiscreteAction(
        action_id=3,
        action_labels=["stop", "go_straight", "turn_left", "turn_right"],
        action_probs=[0.05, 0.75, 0.15, 0.05],
        action_space="navigation_4way",
    )

    vla_output = control_command_pb2.VLAOutput(
        discrete_action=discrete_action,
        model_name="RT-2",
        model_version="1.0.0",
        reasoning_trace="High confidence to go straight.",
        timestamp_ns=1234567890000,
        overall_confidence=0.75,
    )

    # シリアライズ
    serialized = vla_output.SerializeToString()
    print(f"  ✓ Serialized size: {len(serialized)} bytes")

    # デシリアライズ
    vla_output2 = control_command_pb2.VLAOutput()
    vla_output2.ParseFromString(serialized)

    assert vla_output2.HasField("discrete_action")
    assert vla_output2.discrete_action.action_id == 3
    assert len(vla_output2.discrete_action.action_labels) == 4
    assert abs(vla_output2.discrete_action.action_probs[1] - 0.75) < 0.0001
    assert vla_output2.model_name == "RT-2"

    print("  ✓ VLAOutput (Discrete) test passed")


def test_vla_output_continuous():
    """VLAOutput（連続アクション系）のテスト"""
    print("🕹️  Testing VLAOutput (Continuous Action)...")

    continuous_action = control_command_pb2.ContinuousAction(
        action_values=[0.6, 0.1, 0.0],
        action_names=["throttle", "steer", "brake"],
        action_bounds_min=[0.0, -1.0, 0.0],
        action_bounds_max=[1.0, 1.0, 1.0],
    )

    vla_output = control_command_pb2.VLAOutput(
        continuous_action=continuous_action,
        model_name="OpenVLA",
        model_version="1.0.0",
        reasoning_trace="Smooth acceleration with slight left turn.",
        timestamp_ns=1234567890000,
        overall_confidence=0.88,
    )

    # シリアライズ
    serialized = vla_output.SerializeToString()
    print(f"  ✓ Serialized size: {len(serialized)} bytes")

    # デシリアライズ
    vla_output2 = control_command_pb2.VLAOutput()
    vla_output2.ParseFromString(serialized)

    assert vla_output2.HasField("continuous_action")
    assert len(vla_output2.continuous_action.action_values) == 3
    assert abs(vla_output2.continuous_action.action_values[0] - 0.6) < 0.0001
    assert vla_output2.continuous_action.action_names[1] == "steer"
    assert vla_output2.model_name == "OpenVLA"

    print("  ✓ VLAOutput (Continuous) test passed")


def test_control_command():
    """VehicleControlCommandメッセージのテスト（低レベル制御）"""
    print("🎮 Testing VehicleControlCommand...")

    # Target waypointを含む制御コマンド
    target_waypoint = control_command_pb2.Waypoint(
        x=5.0,
        y=0.5,
        z=0.0,
        rotation_matrix=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        timestamp_offset_sec=0.5,
    )

    command = control_command_pb2.VehicleControlCommand(
        throttle=0.6,
        steer=0.1,
        brake=0.0,
        hand_brake=False,
        reverse=False,
        target_waypoint=target_waypoint,
        controller_type="pure_pursuit",
    )

    # シリアライズ
    serialized = command.SerializeToString()
    print(f"  ✓ Serialized size: {len(serialized)} bytes")

    # デシリアライズ
    command2 = control_command_pb2.VehicleControlCommand()
    command2.ParseFromString(serialized)

    assert abs(command2.throttle - 0.6) < 0.0001
    assert abs(command2.steer - 0.1) < 0.0001
    assert command2.controller_type == "pure_pursuit"
    assert abs(command2.target_waypoint.x - 5.0) < 0.0001

    print("  ✓ VehicleControlCommand test passed")


def test_health_check():
    """HealthCheckメッセージのテスト"""
    print("💓 Testing HealthCheck...")

    request = ad_stack_pb2.HealthCheckRequest(service_name="ADStackService")

    response = ad_stack_pb2.HealthCheckResponse(
        status=ad_stack_pb2.HealthCheckResponse.SERVING,
        version="0.1.0",
        model_name="Alpamayo-R1-10B",
    )
    response.metadata["gpu"] = "NVIDIA RTX 3090"

    # シリアライズ
    serialized = response.SerializeToString()
    print(f"  ✓ Serialized size: {len(serialized)} bytes")

    # デシリアライズ
    response2 = ad_stack_pb2.HealthCheckResponse()
    response2.ParseFromString(serialized)

    assert response2.status == ad_stack_pb2.HealthCheckResponse.SERVING
    assert response2.model_name == "Alpamayo-R1-10B"
    assert response2.metadata["gpu"] == "NVIDIA RTX 3090"

    print("  ✓ HealthCheck test passed")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 1 Verification: gRPC Message Tests (VLA Abstraction)")
    print("=" * 70)
    print()

    test_sensor_data_bundle()
    print()
    test_vla_output_waypoint()
    print()
    test_vla_output_discrete()
    print()
    test_vla_output_continuous()
    print()
    test_control_command()
    print()
    test_health_check()
    print()
    print("=" * 70)
    print("✅ All Phase 1 tests passed! (VLA Abstraction)")
    print("=" * 70)
