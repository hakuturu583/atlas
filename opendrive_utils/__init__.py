"""
OpenDRIVE Utilities for CARLA Scenario Generation

CARLAのOpenDRIVEファイルを解析し、座標系変換やスポーン位置計算を簡単に行うためのライブラリ。

主要機能:
- OpenDRIVEファイルの読み込みと解析（pyxodr使用）
- 世界座標系とRoad/レーン座標系の相互変換
- レーン座標からNPCスポーン位置（Transform）の計算
- 交差点、信号機、停止線などの高度な機能
"""

from .parser import OpenDriveMap
from .coordinate_transform import (
    CoordinateTransformer,
    WorldCoord,
    RoadCoord,
    LaneCoord,
)
from .spawn_helper import SpawnHelper
from .advanced_features import (
    AdvancedFeatures,
    TrafficSignal,
    StopLine,
    Junction,
    JunctionConnection,
)

__version__ = "0.1.0"

__all__ = [
    "OpenDriveMap",
    "CoordinateTransformer",
    "WorldCoord",
    "RoadCoord",
    "LaneCoord",
    "SpawnHelper",
    "AdvancedFeatures",
    "TrafficSignal",
    "StopLine",
    "Junction",
    "JunctionConnection",
]
