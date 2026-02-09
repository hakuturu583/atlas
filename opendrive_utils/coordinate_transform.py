"""
座標系変換ユーティリティ

世界座標系（World Coordinate）とRoad/Lane座標系の相互変換を提供します。
"""

import carla
import math
from dataclasses import dataclass
from typing import Optional, Tuple
from .parser import OpenDriveMap


@dataclass
class WorldCoord:
    """世界座標系の座標"""
    x: float
    y: float
    z: float = 0.0

    def to_location(self) -> carla.Location:
        """carla.Locationに変換"""
        return carla.Location(x=self.x, y=self.y, z=self.z)


@dataclass
class RoadCoord:
    """Road座標系の座標"""
    road_id: int
    s: float  # 道路の始点からの距離
    t: float  # 道路中心線からの横方向オフセット（左が正）

    def __str__(self) -> str:
        return f"RoadCoord(road_id={self.road_id}, s={self.s:.2f}, t={self.t:.2f})"


@dataclass
class LaneCoord:
    """Lane座標系の座標"""
    road_id: int
    lane_id: int  # 正: 左側、負: 右側
    s: float  # 道路の始点からの距離
    offset: float = 0.0  # レーン中心からのオフセット

    def __str__(self) -> str:
        return f"LaneCoord(road_id={self.road_id}, lane_id={self.lane_id}, s={self.s:.2f}, offset={self.offset:.2f})"


class CoordinateTransformer:
    """
    座標系変換を行うクラス

    CARLAのAPIとOpenDRIVEの情報を使って、以下の変換を提供:
    - 世界座標 ↔ Road座標
    - 世界座標 ↔ Lane座標
    - Road座標 ↔ Lane座標
    """

    def __init__(self, opendrive_map: OpenDriveMap):
        """
        Args:
            opendrive_map: OpenDriveMapオブジェクト
        """
        self.od_map = opendrive_map
        self.carla_map = opendrive_map.carla_map

    def world_to_road(self, world_coord: WorldCoord) -> Optional[RoadCoord]:
        """
        世界座標からRoad座標への変換

        Args:
            world_coord: 世界座標

        Returns:
            Road座標、変換できない場合はNone
        """
        # 最も近いWaypointを取得
        location = world_coord.to_location()
        waypoint = self.carla_map.get_waypoint(location, project_to_road=True)

        if waypoint is None:
            return None

        # Waypointの位置からt（横方向オフセット）を計算
        wp_location = waypoint.transform.location
        dx = location.x - wp_location.x
        dy = location.y - wp_location.y

        # Waypointの向きを取得
        yaw_rad = math.radians(waypoint.transform.rotation.yaw)

        # 道路中心線に対する垂直方向の距離を計算
        # 左側が正、右側が負
        t = -dx * math.sin(yaw_rad) + dy * math.cos(yaw_rad)

        return RoadCoord(
            road_id=waypoint.road_id,
            s=waypoint.s,
            t=t
        )

    def road_to_world(self, road_coord: RoadCoord) -> Optional[WorldCoord]:
        """
        Road座標から世界座標への変換

        Args:
            road_coord: Road座標

        Returns:
            世界座標、変換できない場合はNone
        """
        # まずレーン0（中心線）のWaypointを取得
        waypoints = self.carla_map.generate_waypoints(2.0)

        # 指定されたroad_idとs座標に最も近いWaypointを探す
        closest_waypoint = None
        min_distance = float('inf')

        for wp in waypoints:
            if wp.road_id == road_coord.road_id:
                s_diff = abs(wp.s - road_coord.s)
                if s_diff < min_distance:
                    min_distance = s_diff
                    closest_waypoint = wp

        if closest_waypoint is None:
            return None

        # Waypointの位置と向きを取得
        location = closest_waypoint.transform.location
        yaw_rad = math.radians(closest_waypoint.transform.rotation.yaw)

        # t（横方向オフセット）を適用
        # 左側が正なので、yawに対して垂直方向にオフセット
        x = location.x - road_coord.t * math.sin(yaw_rad)
        y = location.y + road_coord.t * math.cos(yaw_rad)
        z = location.z

        return WorldCoord(x=x, y=y, z=z)

    def world_to_lane(self, world_coord: WorldCoord) -> Optional[LaneCoord]:
        """
        世界座標からLane座標への変換

        Args:
            world_coord: 世界座標

        Returns:
            Lane座標、変換できない場合はNone
        """
        location = world_coord.to_location()
        waypoint = self.carla_map.get_waypoint(location, project_to_road=True)

        if waypoint is None:
            return None

        # Waypointの位置からoffsetを計算
        wp_location = waypoint.transform.location
        dx = location.x - wp_location.x
        dy = location.y - wp_location.y

        # Waypointの向きを取得
        yaw_rad = math.radians(waypoint.transform.rotation.yaw)

        # レーン中心に対する垂直方向の距離を計算
        offset = -dx * math.sin(yaw_rad) + dy * math.cos(yaw_rad)

        return LaneCoord(
            road_id=waypoint.road_id,
            lane_id=waypoint.lane_id,
            s=waypoint.s,
            offset=offset
        )

    def lane_to_world(self, lane_coord: LaneCoord) -> Optional[WorldCoord]:
        """
        Lane座標から世界座標への変換

        Args:
            lane_coord: Lane座標

        Returns:
            世界座標、変換できない場合はNone
        """
        # 指定されたレーンのWaypointを取得
        waypoints = self.carla_map.generate_waypoints(2.0)

        # 指定されたroad_id、lane_id、s座標に最も近いWaypointを探す
        closest_waypoint = None
        min_distance = float('inf')

        for wp in waypoints:
            if wp.road_id == lane_coord.road_id and wp.lane_id == lane_coord.lane_id:
                s_diff = abs(wp.s - lane_coord.s)
                if s_diff < min_distance:
                    min_distance = s_diff
                    closest_waypoint = wp

        if closest_waypoint is None:
            return None

        # Waypointの位置と向きを取得
        location = closest_waypoint.transform.location
        yaw_rad = math.radians(closest_waypoint.transform.rotation.yaw)

        # offset（レーン中心からのオフセット）を適用
        x = location.x - lane_coord.offset * math.sin(yaw_rad)
        y = location.y + lane_coord.offset * math.cos(yaw_rad)
        z = location.z

        return WorldCoord(x=x, y=y, z=z)

    def road_to_lane(self, road_coord: RoadCoord, lane_id: int) -> Optional[LaneCoord]:
        """
        Road座標からLane座標への変換

        Args:
            road_coord: Road座標
            lane_id: 変換先のLane ID

        Returns:
            Lane座標、変換できない場合はNone
        """
        # まず世界座標に変換してから、指定されたレーンに投影
        world_coord = self.road_to_world(road_coord)
        if world_coord is None:
            return None

        # 指定されたレーンのWaypointを取得
        location = world_coord.to_location()
        waypoint = self.carla_map.get_waypoint(location, project_to_road=True)

        if waypoint is None:
            return None

        # 指定されたレーンIDに切り替え
        if waypoint.lane_id != lane_id:
            # レーン変更が可能か確認
            if lane_id < 0:  # 右側レーン
                if waypoint.lane_id > 0:  # 現在左側なら、中央を経由して右側へ
                    waypoint = waypoint.get_right_lane()
            elif lane_id > 0:  # 左側レーン
                if waypoint.lane_id < 0:  # 現在右側なら、中央を経由して左側へ
                    waypoint = waypoint.get_left_lane()

        if waypoint is None or waypoint.lane_id != lane_id:
            return None

        # オフセットを計算
        wp_location = waypoint.transform.location
        dx = location.x - wp_location.x
        dy = location.y - wp_location.y
        yaw_rad = math.radians(waypoint.transform.rotation.yaw)
        offset = -dx * math.sin(yaw_rad) + dy * math.cos(yaw_rad)

        return LaneCoord(
            road_id=road_coord.road_id,
            lane_id=lane_id,
            s=road_coord.s,
            offset=offset
        )

    def lane_to_road(self, lane_coord: LaneCoord) -> RoadCoord:
        """
        Lane座標からRoad座標への変換

        Args:
            lane_coord: Lane座標

        Returns:
            Road座標
        """
        # レーン中心線からのオフセットを含めてRoad座標系のtを計算
        # レーンIDから道路中心線までの距離を計算
        lane = self.od_map.get_lane(lane_coord.road_id, lane_coord.lane_id, lane_coord.s)

        # 簡易的な計算: レーン幅を基に中心線までの距離を推定
        lane_width = self.od_map.get_lane_width(lane_coord.road_id, lane_coord.lane_id, lane_coord.s)

        # レーンIDに応じてtを計算
        # 正のID（左側）: 正のt
        # 負のID（右側）: 負のt
        if lane_coord.lane_id > 0:
            t = (abs(lane_coord.lane_id) - 0.5) * lane_width + lane_coord.offset
        else:
            t = -(abs(lane_coord.lane_id) - 0.5) * lane_width + lane_coord.offset

        return RoadCoord(
            road_id=lane_coord.road_id,
            s=lane_coord.s,
            t=t
        )

    def calculate_distance_along_lane(
        self,
        start: LaneCoord,
        end: LaneCoord
    ) -> Optional[float]:
        """
        同一レーン上での2点間の距離を計算

        Args:
            start: 開始点のLane座標
            end: 終了点のLane座標

        Returns:
            距離（メートル）、異なるレーンの場合はNone
        """
        if start.road_id != end.road_id or start.lane_id != end.lane_id:
            return None

        return abs(end.s - start.s)

    def calculate_lateral_offset(
        self,
        lane_coord: LaneCoord,
        target_lane_id: int
    ) -> Optional[float]:
        """
        現在のレーンから目標レーンへの横方向オフセットを計算

        Args:
            lane_coord: 現在のLane座標
            target_lane_id: 目標のLane ID

        Returns:
            横方向オフセット（メートル）、計算できない場合はNone
        """
        if lane_coord.lane_id == target_lane_id:
            return 0.0

        # 両方のレーン幅を取得
        current_width = self.od_map.get_lane_width(
            lane_coord.road_id, lane_coord.lane_id, lane_coord.s
        )
        target_width = self.od_map.get_lane_width(
            lane_coord.road_id, target_lane_id, lane_coord.s
        )

        # レーン数に応じた横方向距離を計算
        lane_diff = abs(target_lane_id) - abs(lane_coord.lane_id)

        # 同じ側のレーンへの移動
        if (lane_coord.lane_id > 0 and target_lane_id > 0) or \
           (lane_coord.lane_id < 0 and target_lane_id < 0):
            return lane_diff * (current_width + target_width) / 2

        # 反対側のレーンへの移動
        return (abs(lane_coord.lane_id) + abs(target_lane_id)) * (current_width + target_width) / 2
