#!/usr/bin/env python3
"""利用可能な車両をリスト"""
import carla

client = carla.Client('localhost', 2000)
client.set_timeout(10.0)
world = client.get_world()
blueprint_library = world.get_blueprint_library()

vehicles = blueprint_library.filter('vehicle.*')
print(f"利用可能な車両 ({len(vehicles)}台):")
count = 0
for vehicle in vehicles:
    count += 1
    print(f"  {count}. {vehicle.id}")
    if count >= 20:
        break
