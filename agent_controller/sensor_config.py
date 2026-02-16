"""
SensorConfig - センサー配置の定義と管理

URDFファイルからセンサー配置を読み込み、CARLAセンサーとして利用可能にする。
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math


@dataclass
class SensorDefinition:
    """単一センサーの定義"""

    sensor_id: str  # センサー識別子（例: "CAM_FRONT"）
    sensor_type: str  # CARLAセンサータイプ（例: "sensor.camera.rgb"）

    # 位置・姿勢（自車座標系）
    x: float = 0.0  # 前方（m）
    y: float = 0.0  # 左方向（m）
    z: float = 0.0  # 上方向（m）
    roll: float = 0.0  # ロール（度）
    pitch: float = 0.0  # ピッチ（度）
    yaw: float = 0.0  # ヨー（度）

    # センサーパラメータ
    parameters: Dict[str, any] = field(default_factory=dict)

    def to_carla_transform(self) -> Tuple[float, float, float, float, float, float]:
        """CARLA Transform用のタプルを返す"""
        return (self.x, self.y, self.z, self.pitch, self.yaw, self.roll)


@dataclass
class SensorConfig:
    """センサー構成の定義"""

    name: str
    sensors: List[SensorDefinition] = field(default_factory=list)

    @classmethod
    def from_urdf(cls, urdf_path: str) -> "SensorConfig":
        """
        URDFファイルからセンサー構成を読み込む

        Args:
            urdf_path: URDFファイルのパス

        Returns:
            SensorConfig: センサー構成

        Raises:
            FileNotFoundError: URDFファイルが見つからない
            ValueError: URDF解析エラー
        """
        path = Path(urdf_path)
        if not path.exists():
            raise FileNotFoundError(f"URDF file not found: {urdf_path}")

        tree = ET.parse(urdf_path)
        root = tree.getroot()

        robot_name = root.get("name", "unknown")
        sensors = []

        # 各linkを走査してセンサーを抽出
        for link in root.findall("link"):
            for sensor_elem in link.findall("sensor"):
                sensor = cls._parse_sensor(sensor_elem)
                if sensor:
                    sensors.append(sensor)

        return cls(name=robot_name, sensors=sensors)

    @staticmethod
    def _parse_sensor(sensor_elem: ET.Element) -> Optional[SensorDefinition]:
        """XMLのsensor要素を解析してSensorDefinitionを生成"""
        sensor_id = sensor_elem.get("name")
        sensor_type = sensor_elem.get("type")

        if not sensor_id or not sensor_type:
            return None

        # 位置・姿勢の取得
        origin = sensor_elem.find("origin")
        x, y, z = 0.0, 0.0, 0.0
        roll, pitch, yaw = 0.0, 0.0, 0.0

        if origin is not None:
            xyz = origin.get("xyz", "0 0 0").split()
            x, y, z = map(float, xyz)

            rpy = origin.get("rpy", "0 0 0").split()
            roll, pitch, yaw = map(float, rpy)
            # ラジアンから度に変換
            roll = math.degrees(roll)
            pitch = math.degrees(pitch)
            yaw = math.degrees(yaw)

        # パラメータの取得
        parameters = {}

        # カメラパラメータ
        camera_elem = sensor_elem.find("camera")
        if camera_elem is not None:
            for child in camera_elem:
                parameters[child.tag] = _parse_value(child.text)

        # LiDARパラメータ
        lidar_elem = sensor_elem.find("lidar")
        if lidar_elem is not None:
            for child in lidar_elem:
                parameters[child.tag] = _parse_value(child.text)

        return SensorDefinition(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            x=x,
            y=y,
            z=z,
            roll=roll,
            pitch=pitch,
            yaw=yaw,
            parameters=parameters,
        )

    def get_sensor(self, sensor_id: str) -> Optional[SensorDefinition]:
        """センサーIDでセンサーを取得"""
        for sensor in self.sensors:
            if sensor.sensor_id == sensor_id:
                return sensor
        return None

    def __len__(self) -> int:
        return len(self.sensors)


def _parse_value(text: Optional[str]) -> any:
    """文字列を適切な型に変換"""
    if text is None:
        return None

    text = text.strip()

    # 数値変換を試みる
    try:
        if "." in text:
            return float(text)
        else:
            return int(text)
    except ValueError:
        return text


# ============================================================================
# プリセット定義
# ============================================================================

def load_preset(name: str) -> SensorConfig:
    """
    プリセット名からSensorConfigをロード

    Args:
        name: プリセット名（"nuscenes_cameras", "single_camera", "lidar_camera"）

    Returns:
        SensorConfig: センサー構成

    Raises:
        ValueError: 不明なプリセット名
    """
    preset_path = Path(__file__).parent.parent / "configs" / "sensors" / f"{name}.urdf"

    if not preset_path.exists():
        raise ValueError(
            f"Unknown preset: {name}. Available: nuscenes_cameras, single_camera, lidar_camera"
        )

    return SensorConfig.from_urdf(str(preset_path))


# プリセット定数（遅延ロード）
_NUSCENES_CAMERAS = None
_SINGLE_CAMERA = None
_LIDAR_CAMERA = None


def NUSCENES_CAMERAS() -> SensorConfig:
    """NuScenesカメラ配置（6台カメラ）"""
    global _NUSCENES_CAMERAS
    if _NUSCENES_CAMERAS is None:
        _NUSCENES_CAMERAS = load_preset("nuscenes_cameras")
    return _NUSCENES_CAMERAS


def SINGLE_CAMERA() -> SensorConfig:
    """シングルカメラ（デバッグ用）"""
    global _SINGLE_CAMERA
    if _SINGLE_CAMERA is None:
        _SINGLE_CAMERA = load_preset("single_camera")
    return _SINGLE_CAMERA


def LIDAR_CAMERA() -> SensorConfig:
    """LiDAR + カメラ"""
    global _LIDAR_CAMERA
    if _LIDAR_CAMERA is None:
        _LIDAR_CAMERA = load_preset("lidar_camera")
    return _LIDAR_CAMERA
