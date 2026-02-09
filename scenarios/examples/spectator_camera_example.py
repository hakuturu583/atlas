#!/usr/bin/env python3
"""
スペクターカメラと動画記録の例

ego車両の後方上にスペクターカメラを配置し、imageioで動画を記録します。
"""
import carla
import time
import math
import sys
try:
    import imageio
    import numpy as np
    IMAGEIO_AVAILABLE = True
except ImportError:
    IMAGEIO_AVAILABLE = False
    print("Warning: imageio not available")
    sys.exit(1)


def main():
    """スペクターカメラと動画記録の例"""
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.get_world()

    # 同期モード設定
    original_settings = world.get_settings()
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05  # 20 Hz
    world.apply_settings(settings)

    actors = []
    frames = []

    try:
        blueprint_library = world.get_blueprint_library()

        # 車両をスポーン
        vehicles = blueprint_library.filter('vehicle.*')
        vehicle_bp = None
        for bp in vehicles:
            vehicle_bp = bp
            break

        spawn_points = world.get_map().get_spawn_points()
        vehicle = world.spawn_actor(vehicle_bp, spawn_points[0])
        actors.append(vehicle)
        print(f"✓ 車両をスポーン: {vehicle.type_id}")

        # RGBカメラセンサーをセットアップ（動画記録用）
        camera_bp = blueprint_library.find('sensor.camera.rgb')
        camera_bp.set_attribute('image_size_x', '1280')
        camera_bp.set_attribute('image_size_y', '720')
        camera_bp.set_attribute('fov', '90.0')

        # カメラを車両の後方上に取り付け
        camera_transform = carla.Transform(
            carla.Location(x=-5.0, y=0.0, z=2.5),
            carla.Rotation(pitch=-15.0)
        )
        camera = world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)
        actors.append(camera)
        print("✓ カメラをego車両の後方上に取り付け")

        # カメラデータを受信
        def process_image(image):
            """画像をフレームリストに追加"""
            array = np.frombuffer(image.raw_data, dtype=np.uint8)
            array = array.reshape((image.height, image.width, 4))  # BGRA
            array = array[:, :, :3]  # RGB
            frames.append(array)

        camera.listen(process_image)

        # スペクターも同期（カメラと同じ視点）
        spectator = world.get_spectator()

        print("\n=== シナリオ実行（5秒間）===")
        duration = 5.0
        steps = int(duration / 0.05)

        for i in range(steps):
            # 車両を前進
            control = carla.VehicleControl(throttle=0.5)
            vehicle.apply_control(control)

            # スペクターをカメラ位置に同期
            camera_transform = camera.get_transform()
            spectator.set_transform(camera_transform)

            world.tick()

            if i % 20 == 0:
                print(f"  {i*0.05:.1f}s: {len(frames)} frames")

        # 動画を保存
        print(f"\n動画を保存中... ({len(frames)}フレーム)")
        output_file = 'data/videos/spectator_camera_example.mp4'
        imageio.mimsave(output_file, frames, fps=20, codec='libx264', quality=8)
        print(f"✓ 動画保存完了: {output_file}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # 同期モードを解除
        world.apply_settings(original_settings)

        # クリーンアップ
        print("\nクリーンアップ中...")
        for actor in actors:
            if actor is not None:
                actor.destroy()


if __name__ == "__main__":
    sys.exit(main())
