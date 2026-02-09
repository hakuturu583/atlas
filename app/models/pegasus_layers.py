"""PEGASUS 6 Layer シナリオモデル

PEGASUS (Project for Establishing Generally Accepted Quality Criteria, Tools and Methods
as well as Scenarios for the Safety Validation of Highly Automated Vehicles) の
6層シナリオモデルをdataclassで表現。

参考: ISO 34501, ISO 34502, PEGASUS Method
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ========================================
# Layer 1: Road-level（道路レベル）
# ========================================

class RoadType(str, Enum):
    """道路タイプ"""
    HIGHWAY = "highway"              # 高速道路
    URBAN = "urban"                  # 市街地
    RURAL = "rural"                  # 郊外
    PARKING = "parking"              # 駐車場
    TUNNEL = "tunnel"                # トンネル
    BRIDGE = "bridge"                # 橋


class RoadTopology(str, Enum):
    """道路トポロジー"""
    STRAIGHT = "straight"            # 直線
    CURVE = "curve"                  # カーブ
    JUNCTION = "junction"            # 交差点
    T_JUNCTION = "t_junction"        # T字路
    ROUNDABOUT = "roundabout"        # ロータリー
    MERGE = "merge"                  # 合流
    SPLIT = "split"                  # 分岐


@dataclass
class RoadLevel:
    """Layer 1: 道路レベル"""
    road_type: RoadType
    topology: RoadTopology
    num_lanes: int
    lane_width: float  # m
    curvature: Optional[float] = None  # 1/m（カーブの場合）
    elevation: Optional[float] = None  # 勾配 (%)
    superelevation: Optional[float] = None  # カント (%)
    friction_coefficient: float = 0.8  # 路面摩擦係数
    metadata: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Layer 2: Traffic Infrastructure（交通インフラ）
# ========================================

class TrafficSignType(str, Enum):
    """交通標識タイプ"""
    STOP = "stop"
    YIELD = "yield"
    SPEED_LIMIT = "speed_limit"
    NO_ENTRY = "no_entry"
    ONE_WAY = "one_way"
    PARKING = "parking"
    PEDESTRIAN_CROSSING = "pedestrian_crossing"


class TrafficLightState(str, Enum):
    """信号機の状態"""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    RED_YELLOW = "red_yellow"
    OFF = "off"
    FLASHING_YELLOW = "flashing_yellow"


@dataclass
class TrafficLight:
    """信号機"""
    id: str
    state: TrafficLightState
    cycle_time: Optional[float] = None  # 周期 (s)
    red_duration: Optional[float] = None  # 赤信号の継続時間 (s)
    yellow_duration: Optional[float] = None  # 黄信号の継続時間 (s)
    green_duration: Optional[float] = None  # 青信号の継続時間 (s)
    position: Optional[tuple[float, float, float]] = None  # (x, y, z)


@dataclass
class TrafficSign:
    """交通標識"""
    id: str
    sign_type: TrafficSignType
    value: Optional[str] = None  # 例: 速度制限値
    position: Optional[tuple[float, float, float]] = None


@dataclass
class RoadMarking:
    """路面標示"""
    id: str
    marking_type: str  # "solid_line", "dashed_line", "stop_line", "crosswalk"
    color: str = "white"
    width: Optional[float] = None  # m


@dataclass
class TrafficInfrastructure:
    """Layer 2: 交通インフラ"""
    traffic_lights: List[TrafficLight] = field(default_factory=list)
    traffic_signs: List[TrafficSign] = field(default_factory=list)
    road_markings: List[RoadMarking] = field(default_factory=list)
    crosswalks: List[str] = field(default_factory=list)  # 横断歩道ID
    barriers: List[str] = field(default_factory=list)  # ガードレールなど
    metadata: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Layer 3: Temporary Manipulation（一時的な変更）
# ========================================

class ManipulationType(str, Enum):
    """一時的な変更のタイプ"""
    CONSTRUCTION = "construction"      # 工事
    ACCIDENT = "accident"              # 事故
    ROADBLOCK = "roadblock"            # 道路封鎖
    DETOUR = "detour"                  # 迂回路
    LANE_CLOSURE = "lane_closure"      # レーン閉鎖
    TEMPORARY_SIGN = "temporary_sign"  # 仮設標識


@dataclass
class TemporaryManipulation:
    """Layer 3: 一時的な変更"""
    manipulation_type: ManipulationType
    description: str
    location: Optional[tuple[float, float]] = None  # (x, y)
    duration: Optional[float] = None  # 継続時間 (s)
    affected_lanes: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Layer 4: Moving Objects（移動物体）
# ========================================

class ObjectType(str, Enum):
    """移動物体のタイプ"""
    VEHICLE = "vehicle"
    PEDESTRIAN = "pedestrian"
    BICYCLE = "bicycle"
    MOTORCYCLE = "motorcycle"
    TRUCK = "truck"
    BUS = "bus"
    ANIMAL = "animal"


class ManeuverType(str, Enum):
    """マニューバータイプ"""
    FOLLOW_LANE = "follow_lane"              # レーン追従
    LANE_CHANGE_LEFT = "lane_change_left"    # 左車線変更
    LANE_CHANGE_RIGHT = "lane_change_right"  # 右車線変更
    TURN_LEFT = "turn_left"                  # 左折
    TURN_RIGHT = "turn_right"                # 右折
    STRAIGHT = "straight"                    # 直進
    OVERTAKE = "overtake"                    # 追い越し
    MERGE = "merge"                          # 合流
    STOP = "stop"                            # 停止
    ACCELERATION = "acceleration"            # 加速
    DECELERATION = "deceleration"            # 減速
    PARKING = "parking"                      # 駐車
    U_TURN = "u_turn"                        # Uターン


@dataclass
class InitialState:
    """移動物体の初期状態"""
    position: tuple[float, float, float]  # (x, y, z) または (s, d, h) (Frenet)
    velocity: float  # m/s
    acceleration: float = 0.0  # m/s^2
    heading: float = 0.0  # rad
    lane_id: Optional[int] = None


@dataclass
class MovingObject:
    """Layer 4: 移動物体"""
    id: str
    object_type: ObjectType
    initial_state: InitialState
    maneuver: ManeuverType
    target_velocity: Optional[float] = None  # 目標速度 (m/s)
    trajectory: Optional[List[tuple[float, float, float]]] = None
    is_autonomous: bool = False  # 自動運転車両かどうか
    metadata: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Layer 5: Environment Conditions（環境条件）
# ========================================

class WeatherCondition(str, Enum):
    """天候"""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    SNOW = "snow"
    FOG = "fog"
    THUNDERSTORM = "thunderstorm"


class TimeOfDay(str, Enum):
    """時間帯"""
    DAWN = "dawn"        # 明け方
    MORNING = "morning"  # 朝
    NOON = "noon"        # 昼
    AFTERNOON = "afternoon"  # 午後
    DUSK = "dusk"        # 夕暮れ
    NIGHT = "night"      # 夜


class RoadSurface(str, Enum):
    """路面状態"""
    DRY = "dry"
    WET = "wet"
    ICY = "icy"
    SNOWY = "snowy"
    MUDDY = "muddy"


@dataclass
class EnvironmentConditions:
    """Layer 5: 環境条件"""
    weather: WeatherCondition
    time_of_day: TimeOfDay
    road_surface: RoadSurface
    visibility: float = 1000.0  # 視程 (m)
    temperature: float = 20.0  # 気温 (℃)
    wind_speed: float = 0.0  # 風速 (m/s)
    precipitation: float = 0.0  # 降水量 (mm/h)
    sun_altitude: Optional[float] = None  # 太陽高度 (deg)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ========================================
# Layer 6: Digital Information（デジタル情報）
# ========================================

class CommunicationType(str, Enum):
    """通信タイプ"""
    V2V = "v2v"      # Vehicle-to-Vehicle
    V2I = "v2i"      # Vehicle-to-Infrastructure
    V2P = "v2p"      # Vehicle-to-Pedestrian
    V2X = "v2x"      # Vehicle-to-Everything


@dataclass
class V2XMessage:
    """V2X通信メッセージ"""
    message_type: str  # "CAM", "DENM", "SPAT", "MAP"
    sender_id: str
    timestamp: float
    content: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HDMapInfo:
    """HDマップ情報"""
    map_provider: str
    map_version: str
    accuracy: float  # 精度 (m)
    features: List[str] = field(default_factory=list)


@dataclass
class SensorConfiguration:
    """センサー設定"""
    sensor_type: str  # "camera", "lidar", "radar", "ultrasonic", "gps", "imu"
    range: Optional[float] = None  # 検知範囲 (m)
    fov: Optional[float] = None  # 視野角 (deg)
    resolution: Optional[tuple[int, int]] = None
    frequency: Optional[float] = None  # Hz


@dataclass
class DigitalInformation:
    """Layer 6: デジタル情報"""
    v2x_enabled: bool = False
    v2x_messages: List[V2XMessage] = field(default_factory=list)
    hd_map: Optional[HDMapInfo] = None
    sensors: List[SensorConfiguration] = field(default_factory=list)
    localization_accuracy: float = 0.1  # 自己位置推定精度 (m)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ========================================
# PEGASUS Scenario（6層を統合）
# ========================================

@dataclass
class PegasusScenario:
    """PEGASUS 6層シナリオの完全な定義"""
    scenario_id: str
    name: str
    description: str

    # 6 Layers
    layer1_road: RoadLevel
    layer2_infrastructure: TrafficInfrastructure
    layer3_manipulation: List[TemporaryManipulation] = field(default_factory=list)
    layer4_objects: List[MovingObject] = field(default_factory=list)
    layer5_environment: EnvironmentConditions = field(default_factory=lambda: EnvironmentConditions(
        weather=WeatherCondition.CLEAR,
        time_of_day=TimeOfDay.NOON,
        road_surface=RoadSurface.DRY
    ))
    layer6_digital: DigitalInformation = field(default_factory=DigitalInformation)

    # メタデータ
    criticality_level: Optional[int] = None  # 1-5 (5が最も危険)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "layer1_road": {
                "road_type": self.layer1_road.road_type.value,
                "topology": self.layer1_road.topology.value,
                "num_lanes": self.layer1_road.num_lanes,
                "lane_width": self.layer1_road.lane_width,
                "curvature": self.layer1_road.curvature,
                "elevation": self.layer1_road.elevation,
                "friction_coefficient": self.layer1_road.friction_coefficient,
            },
            "layer2_infrastructure": {
                "traffic_lights": [
                    {
                        "id": tl.id,
                        "state": tl.state.value,
                        "cycle_time": tl.cycle_time,
                        "red_duration": tl.red_duration,
                        "yellow_duration": tl.yellow_duration,
                        "green_duration": tl.green_duration,
                    }
                    for tl in self.layer2_infrastructure.traffic_lights
                ],
                "traffic_signs": [
                    {"id": ts.id, "sign_type": ts.sign_type.value, "value": ts.value}
                    for ts in self.layer2_infrastructure.traffic_signs
                ],
            },
            "layer3_manipulation": [
                {
                    "manipulation_type": tm.manipulation_type.value,
                    "description": tm.description,
                    "location": tm.location,
                    "duration": tm.duration,
                }
                for tm in self.layer3_manipulation
            ],
            "layer4_objects": [
                {
                    "id": obj.id,
                    "object_type": obj.object_type.value,
                    "initial_state": {
                        "position": obj.initial_state.position,
                        "velocity": obj.initial_state.velocity,
                        "acceleration": obj.initial_state.acceleration,
                        "heading": obj.initial_state.heading,
                    },
                    "maneuver": obj.maneuver.value,
                    "is_autonomous": obj.is_autonomous,
                }
                for obj in self.layer4_objects
            ],
            "layer5_environment": {
                "weather": self.layer5_environment.weather.value,
                "time_of_day": self.layer5_environment.time_of_day.value,
                "road_surface": self.layer5_environment.road_surface.value,
                "visibility": self.layer5_environment.visibility,
                "temperature": self.layer5_environment.temperature,
            },
            "layer6_digital": {
                "v2x_enabled": self.layer6_digital.v2x_enabled,
                "hd_map": {
                    "map_provider": self.layer6_digital.hd_map.map_provider,
                    "map_version": self.layer6_digital.hd_map.map_version,
                    "accuracy": self.layer6_digital.hd_map.accuracy,
                } if self.layer6_digital.hd_map else None,
                "localization_accuracy": self.layer6_digital.localization_accuracy,
            },
            "criticality_level": self.criticality_level,
            "tags": self.tags,
            "metadata": self.metadata,
        }
