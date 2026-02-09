#!/usr/bin/env python3
"""
Example CARLA scenario using Python API
"""
import carla
import time
import sys


def main():
    """Run a simple CARLA scenario"""
    # Connect to CARLA
    try:
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        print(f"Connected to CARLA server")

        # Get the world
        world = client.get_world()
        print(f"World: {world.get_map().name}")

        # Get blueprint library
        blueprint_library = world.get_blueprint_library()

        # Spawn a vehicle
        vehicle_bp = blueprint_library.filter('vehicle.tesla.model3')[0]
        spawn_points = world.get_map().get_spawn_points()

        if len(spawn_points) > 0:
            spawn_point = spawn_points[0]
            vehicle = world.spawn_actor(vehicle_bp, spawn_point)
            print(f"Spawned vehicle: {vehicle.type_id} at {spawn_point.location}")

            # Let the vehicle run for a few seconds
            time.sleep(5)

            # Cleanup
            vehicle.destroy()
            print("Vehicle destroyed")
        else:
            print("No spawn points available")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
