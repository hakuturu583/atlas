"""
OpenDRIVEファイルの読み込みと解析
"""

import carla
import pyxodr
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import xml.etree.ElementTree as ET


class OpenDriveMap:
    """
    OpenDRIVEマップの解析と情報取得を行うクラス

    CARLAワールドから.xodrファイルを取得し、pyxodrでパースして
    道路構造の情報を提供します。
    """

    def __init__(self, world: carla.World):
        """
        Args:
            world: CARLAのWorldオブジェクト
        """
        self.world = world
        self.carla_map = world.get_map()

        # OpenDRIVEファイルの取得
        self.opendrive_content = self.carla_map.to_opendrive()

        # pyxodrでパース
        self.xodr = pyxodr.OpenDrive.from_string(self.opendrive_content)

        # キャッシュ
        self._road_cache: Dict[int, pyxodr.Road] = {}
        self._lane_cache: Dict[Tuple[int, int], pyxodr.Lane] = {}

    def save_opendrive(self, output_path: str) -> None:
        """
        OpenDRIVEファイルを保存

        Args:
            output_path: 保存先パス
        """
        Path(output_path).write_text(self.opendrive_content)

    def get_road(self, road_id: int) -> Optional[pyxodr.Road]:
        """
        Road IDからRoadオブジェクトを取得

        Args:
            road_id: Road ID

        Returns:
            Roadオブジェクト、見つからない場合はNone
        """
        if road_id in self._road_cache:
            return self._road_cache[road_id]

        for road in self.xodr.roads:
            if road.id == road_id:
                self._road_cache[road_id] = road
                return road
        return None

    def get_lane_section(self, road_id: int, s: float) -> Optional[pyxodr.LaneSection]:
        """
        指定したs座標でのLaneSectionを取得

        Args:
            road_id: Road ID
            s: Road座標系のs値（道路の始点からの距離）

        Returns:
            LaneSectionオブジェクト、見つからない場合はNone
        """
        road = self.get_road(road_id)
        if road is None:
            return None

        # s座標に対応するLaneSectionを探す
        for lane_section in road.lanes.lane_sections:
            if lane_section.s <= s < (lane_section.s + lane_section.length):
                return lane_section

        # 最後のLaneSectionの範囲外の場合は最後のLaneSectionを返す
        if road.lanes.lane_sections:
            return road.lanes.lane_sections[-1]

        return None

    def get_lane(self, road_id: int, lane_id: int, s: float) -> Optional[pyxodr.Lane]:
        """
        指定したRoad、Lane、s座標でのLaneオブジェクトを取得

        Args:
            road_id: Road ID
            lane_id: Lane ID（正: 左側、負: 右側、0: 中央線）
            s: Road座標系のs値

        Returns:
            Laneオブジェクト、見つからない場合はNone
        """
        lane_section = self.get_lane_section(road_id, s)
        if lane_section is None:
            return None

        # Lane IDに対応するLaneを探す
        if lane_id > 0:
            lanes = lane_section.left_lanes
        elif lane_id < 0:
            lanes = lane_section.right_lanes
        else:
            return lane_section.center_lanes[0] if lane_section.center_lanes else None

        for lane in lanes:
            if lane.id == lane_id:
                return lane

        return None

    def get_available_lanes(self, road_id: int, s: float) -> List[int]:
        """
        指定したRoad、s座標で利用可能なLane IDのリストを取得

        Args:
            road_id: Road ID
            s: Road座標系のs値

        Returns:
            利用可能なLane IDのリスト
        """
        lane_section = self.get_lane_section(road_id, s)
        if lane_section is None:
            return []

        lane_ids = []

        # 左側のレーン（正のID）
        if lane_section.left_lanes:
            lane_ids.extend([lane.id for lane in lane_section.left_lanes])

        # 右側のレーン（負のID）
        if lane_section.right_lanes:
            lane_ids.extend([lane.id for lane in lane_section.right_lanes])

        return sorted(lane_ids)

    def get_road_length(self, road_id: int) -> float:
        """
        Roadの長さを取得

        Args:
            road_id: Road ID

        Returns:
            Roadの長さ（メートル）、見つからない場合は0.0
        """
        road = self.get_road(road_id)
        if road is None:
            return 0.0
        return road.length

    def get_lane_width(self, road_id: int, lane_id: int, s: float) -> float:
        """
        指定した位置でのレーン幅を取得

        Args:
            road_id: Road ID
            lane_id: Lane ID
            s: Road座標系のs値

        Returns:
            レーン幅（メートル）、見つからない場合は3.5
        """
        lane = self.get_lane(road_id, lane_id, s)
        if lane is None:
            return 3.5  # デフォルト値

        # 幅の情報を取得（多項式で定義されている場合がある）
        if hasattr(lane, 'width') and lane.width:
            # 最初の幅定義を使用（簡略化）
            width_entry = lane.width[0] if isinstance(lane.width, list) else lane.width
            if hasattr(width_entry, 'a'):
                return width_entry.a
            return width_entry

        return 3.5  # デフォルト値

    def list_roads(self) -> List[Dict]:
        """
        すべてのRoadの情報をリスト化

        Returns:
            Roadの情報を含む辞書のリスト
        """
        roads = []
        for road in self.xodr.roads:
            roads.append({
                'id': road.id,
                'length': road.length,
                'junction': road.junction,
                'name': getattr(road, 'name', ''),
            })
        return roads

    def is_junction(self, road_id: int) -> bool:
        """
        指定したRoadが交差点（Junction）かどうかを判定

        Args:
            road_id: Road ID

        Returns:
            交差点の場合True
        """
        road = self.get_road(road_id)
        if road is None:
            return False
        return road.junction != -1

    def get_waypoint_info(self, waypoint: carla.Waypoint) -> Dict:
        """
        CARLAのWaypointから詳細情報を取得

        Args:
            waypoint: CARLAのWaypointオブジェクト

        Returns:
            Waypoint情報を含む辞書
        """
        location = waypoint.transform.location
        rotation = waypoint.transform.rotation

        return {
            'road_id': waypoint.road_id,
            'lane_id': waypoint.lane_id,
            's': waypoint.s,
            'location': (location.x, location.y, location.z),
            'rotation': (rotation.pitch, rotation.yaw, rotation.roll),
            'lane_width': waypoint.lane_width,
            'is_junction': waypoint.is_junction,
            'lane_type': str(waypoint.lane_type),
        }
