"""
OpenDRIVE Utilities のテスト

注意: これらのテストはCARLAサーバーが起動している必要があります
"""

import pytest
import carla
from opendrive_utils import (
    OpenDriveMap,
    CoordinateTransformer,
    SpawnHelper,
    WorldCoord,
    LaneCoord,
    RoadCoord,
)


@pytest.fixture(scope="module")
def carla_world():
    """CARLAワールドのフィクスチャ"""
    try:
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        world = client.get_world()
        yield world
    except RuntimeError:
        pytest.skip("CARLAサーバーが起動していません")


@pytest.fixture(scope="module")
def od_map(carla_world):
    """OpenDriveMapのフィクスチャ"""
    return OpenDriveMap(carla_world)


@pytest.fixture(scope="module")
def transformer(od_map):
    """CoordinateTransformerのフィクスチャ"""
    return CoordinateTransformer(od_map)


@pytest.fixture(scope="module")
def spawn_helper(od_map):
    """SpawnHelperのフィクスチャ"""
    return SpawnHelper(od_map)


class TestOpenDriveMap:
    """OpenDriveMapクラスのテスト"""

    def test_list_roads(self, od_map):
        """道路リストの取得"""
        roads = od_map.list_roads()
        assert isinstance(roads, list)
        assert len(roads) > 0
        assert 'id' in roads[0]
        assert 'length' in roads[0]

    def test_get_road(self, od_map):
        """道路の取得"""
        roads = od_map.list_roads()
        road_id = roads[0]['id']
        road = od_map.get_road(road_id)
        assert road is not None
        assert road.id == road_id

    def test_get_road_length(self, od_map):
        """道路の長さ取得"""
        roads = od_map.list_roads()
        road_id = roads[0]['id']
        length = od_map.get_road_length(road_id)
        assert length > 0.0

    def test_get_available_lanes(self, od_map):
        """利用可能なレーンの取得"""
        roads = od_map.list_roads()
        # 通常の道路（交差点でない）を探す
        for road in roads:
            if road['junction'] == -1:
                lane_ids = od_map.get_available_lanes(road['id'], s=10.0)
                if lane_ids:
                    assert isinstance(lane_ids, list)
                    assert len(lane_ids) > 0
                    break

    def test_is_junction(self, od_map):
        """交差点判定"""
        roads = od_map.list_roads()
        for road in roads:
            is_junction = od_map.is_junction(road['id'])
            expected = road['junction'] != -1
            assert is_junction == expected


class TestCoordinateTransformer:
    """CoordinateTransformerクラスのテスト"""

    def test_world_to_lane_to_world(self, transformer):
        """世界座標→レーン座標→世界座標の変換"""
        # 適当な世界座標
        world_coord = WorldCoord(x=100.0, y=50.0, z=0.0)

        # レーン座標に変換
        lane_coord = transformer.world_to_lane(world_coord)
        assert lane_coord is not None
        assert isinstance(lane_coord, LaneCoord)

        # 世界座標に戻す
        world_coord_back = transformer.lane_to_world(lane_coord)
        assert world_coord_back is not None

        # 誤差が小さいことを確認（数メートル以内）
        dx = abs(world_coord.x - world_coord_back.x)
        dy = abs(world_coord.y - world_coord_back.y)
        assert dx < 5.0
        assert dy < 5.0

    def test_calculate_distance_along_lane(self, transformer, od_map):
        """レーン上の距離計算"""
        roads = od_map.list_roads()

        # 通常の道路を探す
        for road in roads:
            if road['junction'] == -1 and road['length'] > 50.0:
                lane_ids = od_map.get_available_lanes(road['id'], s=10.0)
                if lane_ids:
                    lane_id = lane_ids[0]

                    start = LaneCoord(road_id=road['id'], lane_id=lane_id, s=10.0)
                    end = LaneCoord(road_id=road['id'], lane_id=lane_id, s=40.0)

                    distance = transformer.calculate_distance_along_lane(start, end)
                    assert distance is not None
                    assert abs(distance - 30.0) < 0.1  # 30mのはず
                    break


class TestSpawnHelper:
    """SpawnHelperクラスのテスト"""

    def test_get_spawn_transform_from_lane(self, spawn_helper, od_map):
        """レーン座標からTransform取得"""
        roads = od_map.list_roads()

        # 通常の道路を探す
        for road in roads:
            if road['junction'] == -1:
                lane_ids = od_map.get_available_lanes(road['id'], s=10.0)
                if lane_ids:
                    lane_coord = LaneCoord(
                        road_id=road['id'],
                        lane_id=lane_ids[0],
                        s=10.0
                    )

                    transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)
                    assert transform is not None
                    assert isinstance(transform, carla.Transform)
                    assert transform.location is not None
                    assert transform.rotation is not None
                    break

    def test_get_spawn_transform_at_distance(self, spawn_helper, od_map):
        """指定距離でのTransform取得"""
        roads = od_map.list_roads()

        # 長い道路を探す
        for road in roads:
            if road['junction'] == -1 and road['length'] > 100.0:
                lane_ids = od_map.get_available_lanes(road['id'], s=10.0)
                if lane_ids:
                    start_lane_coord = LaneCoord(
                        road_id=road['id'],
                        lane_id=lane_ids[0],
                        s=10.0
                    )

                    transform = spawn_helper.get_spawn_transform_at_distance(
                        start_lane_coord,
                        distance=30.0
                    )
                    assert transform is not None
                    assert isinstance(transform, carla.Transform)
                    break

    def test_get_spawn_points_along_lane(self, spawn_helper, od_map):
        """レーン上の複数スポーン位置取得"""
        roads = od_map.list_roads()

        # 長い道路を探す
        for road in roads:
            if road['junction'] == -1 and road['length'] > 100.0:
                lane_ids = od_map.get_available_lanes(road['id'], s=10.0)
                if lane_ids:
                    lane_coord = LaneCoord(
                        road_id=road['id'],
                        lane_id=lane_ids[0],
                        s=10.0
                    )

                    transforms = spawn_helper.get_spawn_points_along_lane(
                        lane_coord,
                        num_points=3,
                        spacing=20.0
                    )
                    assert isinstance(transforms, list)
                    assert len(transforms) > 0
                    for t in transforms:
                        assert isinstance(t, carla.Transform)
                    break

    def test_calculate_relative_spawn(self, spawn_helper):
        """相対位置のスポーン計算"""
        # 基準Transform
        reference = carla.Transform(
            carla.Location(x=0.0, y=0.0, z=0.0),
            carla.Rotation(pitch=0.0, yaw=0.0, roll=0.0)
        )

        # 前方10m、左2mの位置を計算
        relative = spawn_helper.calculate_relative_spawn(
            reference,
            forward_distance=10.0,
            lateral_offset=2.0
        )

        assert relative is not None
        assert isinstance(relative, carla.Transform)

        # 前方10mなのでxが約10.0
        assert abs(relative.location.x - 10.0) < 0.1

        # 左2mなのでyが約2.0
        assert abs(relative.location.y - 2.0) < 0.1


def test_integration(carla_world, od_map, spawn_helper):
    """統合テスト: 実際に車両をスポーンして削除"""
    roads = od_map.list_roads()

    # 通常の道路を探す
    for road in roads:
        if road['junction'] == -1:
            lane_ids = od_map.get_available_lanes(road['id'], s=10.0)
            if lane_ids:
                lane_coord = LaneCoord(
                    road_id=road['id'],
                    lane_id=lane_ids[0],
                    s=10.0
                )

                transform = spawn_helper.get_spawn_transform_from_lane(lane_coord)
                assert transform is not None

                # 車両をスポーン
                blueprint = carla_world.get_blueprint_library().filter('vehicle.tesla.model3')[0]
                try:
                    vehicle = carla_world.spawn_actor(blueprint, transform)
                    assert vehicle is not None

                    # 削除
                    vehicle.destroy()
                except RuntimeError:
                    # スポーンに失敗する場合もあるのでスキップ
                    pass

                break
