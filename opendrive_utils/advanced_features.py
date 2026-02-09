"""
OpenDRIVE高度な機能

交差点、信号機、停止線などのOpenDRIVE属性を考慮した座標計算を提供します。
"""

import carla
import math
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from .parser import OpenDriveMap
from .coordinate_transform import CoordinateTransformer, LaneCoord, RoadCoord
from .spawn_helper import SpawnHelper


@dataclass
class TrafficSignal:
    """信号機情報"""
    id: str
    road_id: int
    s: float  # 道路上の位置
    t: float  # 横方向オフセット
    orientation: str  # '+' or '-' (進行方向)
    signal_type: str  # 信号の種類（例: "1000001" = 通常の信号機）
    subtype: str
    dynamic: bool  # 動的信号かどうか
    country: str

    def __str__(self) -> str:
        return f"TrafficSignal(id={self.id}, road_id={self.road_id}, s={self.s:.2f}m, type={self.signal_type})"


@dataclass
class StopLine:
    """停止線情報"""
    road_id: int
    lane_id: int
    s: float  # 道路上の位置
    width: float  # 幅
    signal_id: Optional[str] = None  # 対応する信号機ID

    def __str__(self) -> str:
        return f"StopLine(road_id={self.road_id}, lane_id={self.lane_id}, s={self.s:.2f}m)"


@dataclass
class JunctionConnection:
    """交差点内の接続情報"""
    id: int
    incoming_road: int
    connecting_road: int
    contact_point: str  # 'start' or 'end'
    lane_links: List[Tuple[int, int]]  # (from_lane, to_lane)のリスト

    def __str__(self) -> str:
        return f"JunctionConnection(incoming={self.incoming_road} → connecting={self.connecting_road})"


@dataclass
class Junction:
    """交差点情報"""
    id: int
    name: str
    connections: List[JunctionConnection]

    def __str__(self) -> str:
        return f"Junction(id={self.id}, name={self.name}, connections={len(self.connections)})"


class AdvancedFeatures:
    """
    OpenDRIVEの高度な機能を提供するクラス

    交差点、信号機、停止線などの情報を解析し、
    シナリオ記述で使いやすいAPIを提供します。
    """

    def __init__(self, opendrive_map: OpenDriveMap):
        """
        Args:
            opendrive_map: OpenDriveMapオブジェクト
        """
        self.od_map = opendrive_map
        self.transformer = CoordinateTransformer(opendrive_map)
        self.spawn_helper = SpawnHelper(opendrive_map)

        # XMLをパース
        self.xml_root = ET.fromstring(opendrive_map.opendrive_content)

        # キャッシュ
        self._signals_cache: Optional[List[TrafficSignal]] = None
        self._junctions_cache: Optional[Dict[int, Junction]] = None
        self._stop_lines_cache: Optional[List[StopLine]] = None

    def get_traffic_signals(self) -> List[TrafficSignal]:
        """
        すべての信号機情報を取得

        Returns:
            TrafficSignalのリスト
        """
        if self._signals_cache is not None:
            return self._signals_cache

        signals = []

        # すべての道路を走査
        for road_elem in self.xml_root.findall('.//road'):
            road_id = int(road_elem.get('id'))

            # 信号機を探す
            for signal_elem in road_elem.findall('.//signals/signal'):
                signal = TrafficSignal(
                    id=signal_elem.get('id', ''),
                    road_id=road_id,
                    s=float(signal_elem.get('s', 0.0)),
                    t=float(signal_elem.get('t', 0.0)),
                    orientation=signal_elem.get('orientation', '+'),
                    signal_type=signal_elem.get('type', ''),
                    subtype=signal_elem.get('subtype', ''),
                    dynamic=signal_elem.get('dynamic', 'no') == 'yes',
                    country=signal_elem.get('country', 'OpenDRIVE'),
                )
                signals.append(signal)

        self._signals_cache = signals
        return signals

    def get_signals_on_road(self, road_id: int) -> List[TrafficSignal]:
        """
        指定した道路上のすべての信号機を取得

        Args:
            road_id: Road ID

        Returns:
            TrafficSignalのリスト
        """
        all_signals = self.get_traffic_signals()
        return [s for s in all_signals if s.road_id == road_id]

    def get_nearest_signal(
        self,
        lane_coord: LaneCoord,
        max_distance: float = 100.0
    ) -> Optional[TrafficSignal]:
        """
        指定したレーン座標から最も近い信号機を取得

        Args:
            lane_coord: レーン座標
            max_distance: 最大検索距離（メートル）

        Returns:
            最も近いTrafficSignal、見つからない場合はNone
        """
        signals = self.get_signals_on_road(lane_coord.road_id)

        nearest_signal = None
        min_distance = float('inf')

        for signal in signals:
            # 同じ道路上で前方にある信号機のみ考慮
            if signal.s >= lane_coord.s:
                distance = signal.s - lane_coord.s
                if distance < min_distance and distance <= max_distance:
                    min_distance = distance
                    nearest_signal = signal

        return nearest_signal

    def get_signal_transform(self, signal: TrafficSignal) -> Optional[carla.Transform]:
        """
        信号機の世界座標Transformを取得

        Args:
            signal: TrafficSignal

        Returns:
            carla.Transform、計算できない場合はNone
        """
        road_coord = RoadCoord(
            road_id=signal.road_id,
            s=signal.s,
            t=signal.t
        )
        world_coord = self.transformer.road_to_world(road_coord)

        if world_coord is None:
            return None

        # 向きは道路の向きと同じ
        waypoint = self.od_map.carla_map.get_waypoint(
            world_coord.to_location(),
            project_to_road=True
        )

        if waypoint is None:
            return None

        # 信号機の向きを調整（orientationに基づく）
        rotation = waypoint.transform.rotation
        if signal.orientation == '-':
            # 逆向き
            rotation.yaw += 180.0

        return carla.Transform(world_coord.to_location(), rotation)

    def get_stop_lines(self) -> List[StopLine]:
        """
        すべての停止線情報を取得

        Returns:
            StopLineのリスト
        """
        if self._stop_lines_cache is not None:
            return self._stop_lines_cache

        stop_lines = []

        # 信号機と対応する停止線を推定
        signals = self.get_traffic_signals()

        for signal in signals:
            # 信号機の位置付近に停止線があると仮定
            # 通常、信号機の少し手前に停止線がある
            stop_line_offset = -5.0  # 5m手前

            # 信号機があるレーンを推定
            available_lanes = self.od_map.get_available_lanes(signal.road_id, signal.s)

            for lane_id in available_lanes:
                # 進行方向のレーンのみ
                if (signal.orientation == '+' and lane_id < 0) or \
                   (signal.orientation == '-' and lane_id > 0):
                    stop_line = StopLine(
                        road_id=signal.road_id,
                        lane_id=lane_id,
                        s=signal.s + stop_line_offset,
                        width=self.od_map.get_lane_width(signal.road_id, lane_id, signal.s),
                        signal_id=signal.id
                    )
                    stop_lines.append(stop_line)

        self._stop_lines_cache = stop_lines
        return stop_lines

    def get_stop_line_transform(self, stop_line: StopLine) -> Optional[carla.Transform]:
        """
        停止線の世界座標Transformを取得

        Args:
            stop_line: StopLine

        Returns:
            carla.Transform、計算できない場合はNone
        """
        lane_coord = LaneCoord(
            road_id=stop_line.road_id,
            lane_id=stop_line.lane_id,
            s=stop_line.s,
            offset=0.0
        )
        return self.spawn_helper.get_spawn_transform_from_lane(lane_coord)

    def get_junctions(self) -> Dict[int, Junction]:
        """
        すべての交差点情報を取得

        Returns:
            Junction IDをキーとした辞書
        """
        if self._junctions_cache is not None:
            return self._junctions_cache

        junctions = {}

        for junction_elem in self.xml_root.findall('.//junction'):
            junction_id = int(junction_elem.get('id'))
            junction_name = junction_elem.get('name', f'Junction_{junction_id}')

            connections = []
            for conn_elem in junction_elem.findall('connection'):
                conn_id = int(conn_elem.get('id'))
                incoming_road = int(conn_elem.get('incomingRoad'))
                connecting_road = int(conn_elem.get('connectingRoad'))
                contact_point = conn_elem.get('contactPoint', 'start')

                lane_links = []
                for link_elem in conn_elem.findall('laneLink'):
                    from_lane = int(link_elem.get('from'))
                    to_lane = int(link_elem.get('to'))
                    lane_links.append((from_lane, to_lane))

                connection = JunctionConnection(
                    id=conn_id,
                    incoming_road=incoming_road,
                    connecting_road=connecting_road,
                    contact_point=contact_point,
                    lane_links=lane_links
                )
                connections.append(connection)

            junction = Junction(
                id=junction_id,
                name=junction_name,
                connections=connections
            )
            junctions[junction_id] = junction

        self._junctions_cache = junctions
        return junctions

    def get_junction_by_road(self, road_id: int) -> Optional[Junction]:
        """
        指定した道路が属する交差点を取得

        Args:
            road_id: Road ID

        Returns:
            Junction、見つからない場合はNone
        """
        road = self.od_map.get_road(road_id)
        if road is None or road.junction == -1:
            return None

        junctions = self.get_junctions()
        return junctions.get(road.junction)

    def get_junction_entry_points(
        self,
        junction_id: int,
        incoming_road_id: int
    ) -> List[carla.Transform]:
        """
        交差点への流入点のスポーン位置を取得

        Args:
            junction_id: 交差点ID
            incoming_road_id: 流入道路のID

        Returns:
            carla.Transformのリスト
        """
        junctions = self.get_junctions()
        junction = junctions.get(junction_id)

        if junction is None:
            return []

        entry_transforms = []

        # この流入道路からの接続を探す
        for connection in junction.connections:
            if connection.incoming_road == incoming_road_id:
                # 接続道路の始点
                connecting_road_length = self.od_map.get_road_length(connection.connecting_road)

                if connection.contact_point == 'start':
                    s = 5.0  # 始点から少し入った位置
                else:
                    s = connecting_road_length - 5.0  # 終点から少し手前

                # 各レーンのスポーン位置
                for from_lane, to_lane in connection.lane_links:
                    lane_coord = LaneCoord(
                        road_id=connection.connecting_road,
                        lane_id=to_lane,
                        s=s,
                        offset=0.0
                    )
                    transform = self.spawn_helper.get_spawn_transform_from_lane(lane_coord)
                    if transform:
                        entry_transforms.append(transform)

        return entry_transforms

    def get_junction_exit_points(
        self,
        junction_id: int,
        outgoing_road_id: int
    ) -> List[carla.Transform]:
        """
        交差点からの流出点のスポーン位置を取得

        Args:
            junction_id: 交差点ID
            outgoing_road_id: 流出道路のID

        Returns:
            carla.Transformのリスト
        """
        junctions = self.get_junctions()
        junction = junctions.get(junction_id)

        if junction is None:
            return []

        exit_transforms = []

        # 流出道路の始点付近
        s = 10.0  # 始点から10m
        available_lanes = self.od_map.get_available_lanes(outgoing_road_id, s)

        for lane_id in available_lanes:
            lane_coord = LaneCoord(
                road_id=outgoing_road_id,
                lane_id=lane_id,
                s=s,
                offset=0.0
            )
            transform = self.spawn_helper.get_spawn_transform_from_lane(lane_coord)
            if transform:
                exit_transforms.append(transform)

        return exit_transforms

    def get_spawn_before_signal(
        self,
        signal: TrafficSignal,
        lane_id: int,
        distance_before: float = 10.0
    ) -> Optional[carla.Transform]:
        """
        信号機の手前にスポーン位置を計算

        Args:
            signal: TrafficSignal
            lane_id: レーンID
            distance_before: 信号機の何メートル手前か（デフォルト: 10m）

        Returns:
            carla.Transform、計算できない場合はNone
        """
        # 信号機の位置から手前にオフセット
        s = max(0.0, signal.s - distance_before)

        lane_coord = LaneCoord(
            road_id=signal.road_id,
            lane_id=lane_id,
            s=s,
            offset=0.0
        )

        return self.spawn_helper.get_spawn_transform_from_lane(lane_coord)

    def get_spawn_at_stop_line(
        self,
        stop_line: StopLine,
        offset_before: float = 2.0
    ) -> Optional[carla.Transform]:
        """
        停止線の手前にスポーン位置を計算

        Args:
            stop_line: StopLine
            offset_before: 停止線の何メートル手前か（デフォルト: 2m）

        Returns:
            carla.Transform、計算できない場合はNone
        """
        s = max(0.0, stop_line.s - offset_before)

        lane_coord = LaneCoord(
            road_id=stop_line.road_id,
            lane_id=stop_line.lane_id,
            s=s,
            offset=0.0
        )

        return self.spawn_helper.get_spawn_transform_from_lane(lane_coord)

    def find_path_through_junction(
        self,
        junction_id: int,
        incoming_road_id: int,
        outgoing_road_id: int
    ) -> Optional[List[int]]:
        """
        交差点内の経路（道路IDのリスト）を取得

        Args:
            junction_id: 交差点ID
            incoming_road_id: 流入道路ID
            outgoing_road_id: 流出道路ID

        Returns:
            道路IDのリスト、経路が見つからない場合はNone
        """
        junctions = self.get_junctions()
        junction = junctions.get(junction_id)

        if junction is None:
            return None

        # 流入道路からの接続を探す
        for connection in junction.connections:
            if connection.incoming_road == incoming_road_id:
                # 接続道路が流出道路に繋がっているか確認
                connecting_road = self.od_map.get_road(connection.connecting_road)
                if connecting_road:
                    # 接続道路の次の道路が流出道路かチェック
                    # （簡易実装: 直接繋がっていると仮定）
                    return [incoming_road_id, connection.connecting_road, outgoing_road_id]

        return None

    def get_junction_center_transform(self, junction_id: int) -> Optional[carla.Transform]:
        """
        交差点の中心位置のTransformを取得

        Args:
            junction_id: 交差点ID

        Returns:
            carla.Transform、計算できない場合はNone
        """
        junctions = self.get_junctions()
        junction = junctions.get(junction_id)

        if junction is None or not junction.connections:
            return None

        # すべての接続道路の中間点を計算
        all_locations = []

        for connection in junction.connections[:3]:  # 最初の3つの接続を使用
            road_length = self.od_map.get_road_length(connection.connecting_road)
            s = road_length / 2.0

            available_lanes = self.od_map.get_available_lanes(connection.connecting_road, s)
            if available_lanes:
                lane_coord = LaneCoord(
                    road_id=connection.connecting_road,
                    lane_id=available_lanes[0],
                    s=s,
                    offset=0.0
                )
                world_coord = self.transformer.lane_to_world(lane_coord)
                if world_coord:
                    all_locations.append(world_coord)

        if not all_locations:
            return None

        # 平均位置を計算
        avg_x = sum(loc.x for loc in all_locations) / len(all_locations)
        avg_y = sum(loc.y for loc in all_locations) / len(all_locations)
        avg_z = sum(loc.z for loc in all_locations) / len(all_locations)

        center_location = carla.Location(x=avg_x, y=avg_y, z=avg_z)

        # 向きは最初の接続道路の向きを使用
        waypoint = self.od_map.carla_map.get_waypoint(center_location, project_to_road=True)
        rotation = waypoint.transform.rotation if waypoint else carla.Rotation()

        return carla.Transform(center_location, rotation)

    def list_traffic_signals(self) -> None:
        """すべての信号機情報を表示（デバッグ用）"""
        signals = self.get_traffic_signals()
        print(f"=== 信号機一覧 ({len(signals)}件) ===")
        for signal in signals:
            print(f"  {signal}")

    def list_junctions(self) -> None:
        """すべての交差点情報を表示（デバッグ用）"""
        junctions = self.get_junctions()
        print(f"=== 交差点一覧 ({len(junctions)}件) ===")
        for junction in junctions.values():
            print(f"  {junction}")
            for conn in junction.connections:
                print(f"    {conn}")
