"""
スポーン位置計算ヘルパー

レーン座標から車両やNPCのスポーン位置（carla.Transform）を計算します。
"""

import carla
import math
from typing import Optional, List, Tuple
from .parser import OpenDriveMap
from .coordinate_transform import (
    CoordinateTransformer,
    LaneCoord,
    RoadCoord,
    WorldCoord,
)


class SpawnHelper:
    """
    スポーン位置計算を行うヘルパークラス

    レーン座標や道路座標から、車両やNPCをスポーンするための
    carla.Transformを計算します。
    """

    def __init__(self, opendrive_map: OpenDriveMap):
        """
        Args:
            opendrive_map: OpenDriveMapオブジェクト
        """
        self.od_map = opendrive_map
        self.transformer = CoordinateTransformer(opendrive_map)
        self.carla_map = opendrive_map.carla_map

    def get_spawn_transform_from_lane(
        self,
        lane_coord: LaneCoord,
        z_offset: float = 0.5
    ) -> Optional[carla.Transform]:
        """
        レーン座標からスポーン用のTransformを計算

        Args:
            lane_coord: レーン座標
            z_offset: 地面からの高さオフセット（デフォルト: 0.5m）

        Returns:
            carla.Transform、計算できない場合はNone
        """
        # レーン座標から世界座標に変換
        world_coord = self.transformer.lane_to_world(lane_coord)
        if world_coord is None:
            return None

        # 最も近いWaypointを取得して向きを得る
        location = world_coord.to_location()
        waypoint = self.carla_map.get_waypoint(
            location,
            project_to_road=True,
            lane_type=carla.LaneType.Driving
        )

        if waypoint is None:
            return None

        # Z座標にオフセットを適用
        final_location = carla.Location(
            x=world_coord.x,
            y=world_coord.y,
            z=world_coord.z + z_offset
        )

        # Waypointの向きを使用
        rotation = waypoint.transform.rotation

        return carla.Transform(final_location, rotation)

    def get_spawn_transform_from_road(
        self,
        road_coord: RoadCoord,
        z_offset: float = 0.5
    ) -> Optional[carla.Transform]:
        """
        Road座標からスポーン用のTransformを計算

        Args:
            road_coord: Road座標
            z_offset: 地面からの高さオフセット（デフォルト: 0.5m）

        Returns:
            carla.Transform、計算できない場合はNone
        """
        # Road座標から世界座標に変換
        world_coord = self.transformer.road_to_world(road_coord)
        if world_coord is None:
            return None

        # 最も近いWaypointを取得して向きを得る
        location = world_coord.to_location()
        waypoint = self.carla_map.get_waypoint(location, project_to_road=True)

        if waypoint is None:
            return None

        # Z座標にオフセットを適用
        final_location = carla.Location(
            x=world_coord.x,
            y=world_coord.y,
            z=world_coord.z + z_offset
        )

        rotation = waypoint.transform.rotation

        return carla.Transform(final_location, rotation)

    def get_spawn_transform_at_distance(
        self,
        start_lane_coord: LaneCoord,
        distance: float,
        z_offset: float = 0.5
    ) -> Optional[carla.Transform]:
        """
        開始レーン座標から指定距離前方のスポーン位置を計算

        Args:
            start_lane_coord: 開始レーン座標
            distance: 前方への距離（メートル）
            z_offset: 地面からの高さオフセット（デフォルト: 0.5m）

        Returns:
            carla.Transform、計算できない場合はNone
        """
        # 新しいs座標を計算
        new_s = start_lane_coord.s + distance

        # 道路の長さを超えないようにチェック
        road_length = self.od_map.get_road_length(start_lane_coord.road_id)
        if new_s > road_length:
            # 道路の終端を使用
            new_s = road_length - 1.0  # 少し手前
        elif new_s < 0:
            new_s = 0.0

        # 新しいレーン座標を作成
        target_lane_coord = LaneCoord(
            road_id=start_lane_coord.road_id,
            lane_id=start_lane_coord.lane_id,
            s=new_s,
            offset=start_lane_coord.offset
        )

        return self.get_spawn_transform_from_lane(target_lane_coord, z_offset)

    def get_spawn_points_along_lane(
        self,
        lane_coord: LaneCoord,
        num_points: int,
        spacing: float,
        z_offset: float = 0.5
    ) -> List[carla.Transform]:
        """
        レーン上に等間隔でスポーン位置を配置

        Args:
            lane_coord: 開始レーン座標
            num_points: スポーン位置の数
            spacing: スポーン位置間の距離（メートル）
            z_offset: 地面からの高さオフセット（デフォルト: 0.5m）

        Returns:
            carla.Transformのリスト
        """
        transforms = []

        for i in range(num_points):
            distance = i * spacing
            transform = self.get_spawn_transform_at_distance(
                lane_coord,
                distance,
                z_offset
            )
            if transform is not None:
                transforms.append(transform)

        return transforms

    def get_spawn_transform_at_junction(
        self,
        junction_road_id: int,
        entry_road_id: int,
        exit_road_id: int,
        progress: float = 0.5,
        z_offset: float = 0.5
    ) -> Optional[carla.Transform]:
        """
        交差点内でのスポーン位置を計算

        Args:
            junction_road_id: 交差点のRoad ID
            entry_road_id: 流入道路のRoad ID
            exit_road_id: 流出道路のRoad ID
            progress: 交差点内での進行度（0.0～1.0）
            z_offset: 地面からの高さオフセット（デフォルト: 0.5m）

        Returns:
            carla.Transform、計算できない場合はNone
        """
        # 交差点の長さを取得
        road_length = self.od_map.get_road_length(junction_road_id)
        if road_length == 0.0:
            return None

        # 進行度に基づいてs座標を計算
        s = road_length * progress

        # 利用可能なレーンを取得
        available_lanes = self.od_map.get_available_lanes(junction_road_id, s)
        if not available_lanes:
            return None

        # 最初のレーンを使用
        lane_id = available_lanes[0]

        lane_coord = LaneCoord(
            road_id=junction_road_id,
            lane_id=lane_id,
            s=s,
            offset=0.0
        )

        return self.get_spawn_transform_from_lane(lane_coord, z_offset)

    def find_spawn_point_near_location(
        self,
        location: carla.Location,
        lane_type: carla.LaneType = carla.LaneType.Driving,
        z_offset: float = 0.5
    ) -> Optional[carla.Transform]:
        """
        指定した世界座標近くの有効なスポーン位置を検索

        Args:
            location: 検索の基準となる世界座標
            lane_type: レーンタイプ（デフォルト: Driving）
            z_offset: 地面からの高さオフセット（デフォルト: 0.5m）

        Returns:
            carla.Transform、見つからない場合はNone
        """
        waypoint = self.carla_map.get_waypoint(
            location,
            project_to_road=True,
            lane_type=lane_type
        )

        if waypoint is None:
            return None

        # Z座標にオフセットを適用
        final_location = carla.Location(
            x=waypoint.transform.location.x,
            y=waypoint.transform.location.y,
            z=waypoint.transform.location.z + z_offset
        )

        return carla.Transform(final_location, waypoint.transform.rotation)

    def get_safe_spawn_points(
        self,
        road_id: int,
        lane_id: int,
        min_spacing: float = 10.0,
        z_offset: float = 0.5
    ) -> List[carla.Transform]:
        """
        指定したレーン上の安全なスポーン位置をすべて取得

        Args:
            road_id: Road ID
            lane_id: Lane ID
            min_spacing: 最小間隔（メートル）
            z_offset: 地面からの高さオフセット（デフォルト: 0.5m）

        Returns:
            carla.Transformのリスト
        """
        road_length = self.od_map.get_road_length(road_id)
        if road_length == 0.0:
            return []

        transforms = []
        s = 0.0

        while s < road_length:
            lane_coord = LaneCoord(
                road_id=road_id,
                lane_id=lane_id,
                s=s,
                offset=0.0
            )

            transform = self.get_spawn_transform_from_lane(lane_coord, z_offset)
            if transform is not None:
                transforms.append(transform)

            s += min_spacing

        return transforms

    def calculate_relative_spawn(
        self,
        reference_transform: carla.Transform,
        forward_distance: float,
        lateral_offset: float,
        z_offset: float = 0.0
    ) -> carla.Transform:
        """
        基準Transformから相対位置にスポーン位置を計算

        Args:
            reference_transform: 基準となるTransform
            forward_distance: 前方への距離（メートル）
            lateral_offset: 横方向のオフセット（メートル、左が正）
            z_offset: 高さオフセット（メートル）

        Returns:
            相対位置のcarla.Transform
        """
        # 基準の位置と向き
        ref_location = reference_transform.location
        ref_rotation = reference_transform.rotation
        yaw_rad = math.radians(ref_rotation.yaw)

        # 前方と横方向のベクトルを計算
        forward_x = math.cos(yaw_rad) * forward_distance
        forward_y = math.sin(yaw_rad) * forward_distance

        lateral_x = -math.sin(yaw_rad) * lateral_offset
        lateral_y = math.cos(yaw_rad) * lateral_offset

        # 新しい位置を計算
        new_location = carla.Location(
            x=ref_location.x + forward_x + lateral_x,
            y=ref_location.y + forward_y + lateral_y,
            z=ref_location.z + z_offset
        )

        # 向きは基準と同じ
        return carla.Transform(new_location, ref_rotation)
