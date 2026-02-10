"""
SafetyMetrics: 自動運転システム評価のための安全性メトリクス

TTC、急ブレーキ、急加速など、自動運転システムの評価や
意味論的カバレッジ計算に使われるイベントを自動検出します。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import carla


@dataclass
class MetricsEvent:
    """メトリクスイベント（閾値違反など）"""

    frame: int
    timestamp: float
    event_type: str
    vehicle_id: int
    value: float
    threshold: float
    description: str
    location: Optional[Tuple[float, float, float]] = None


@dataclass
class MetricsConfig:
    """メトリクス計算の設定"""

    # TTC (Time To Collision) 閾値 [秒]
    ttc_threshold: float = 3.0

    # 急ブレーキ閾値 [m/s^2]
    sudden_braking_threshold: float = 5.0

    # 急加速閾値 [m/s^2]
    sudden_acceleration_threshold: float = 4.0

    # 横方向加速度閾値 [m/s^2]
    lateral_acceleration_threshold: float = 3.0

    # ジャーク閾値 [m/s^3]
    jerk_threshold: float = 10.0

    # 最小車間距離閾値 [m]
    min_distance_threshold: float = 2.0

    # 速度違反マージン [km/h]
    speed_violation_margin: float = 10.0


class SafetyMetrics:
    """自動運転システムの安全性メトリクス計算クラス"""

    def __init__(
        self,
        scenario_uuid: str,
        config: Optional[MetricsConfig] = None,
    ):
        """
        Args:
            scenario_uuid: シナリオUUID
            config: メトリクス設定
        """
        self.scenario_uuid = scenario_uuid
        self.config = config or MetricsConfig()

        # メトリクスデータ
        self.events: List[MetricsEvent] = []
        self.ttc_history: Dict[int, List[float]] = {}  # vehicle_id -> TTC履歴
        self.speed_history: Dict[int, List[float]] = {}  # vehicle_id -> 速度履歴
        self.acceleration_history: Dict[int, List[float]] = {}  # vehicle_id -> 加速度履歴
        self.min_distances: Dict[int, float] = {}  # vehicle_id -> 最小車間距離

        # 前回のフレームデータ（差分計算用）
        self._prev_velocity: Dict[int, carla.Vector3D] = {}
        self._prev_acceleration: Dict[int, float] = {}

    def update(
        self,
        frame: int,
        timestamp: float,
        vehicle: carla.Vehicle,
        world: carla.World,
    ):
        """
        1フレーム分のメトリクスを更新

        Args:
            frame: 現在のフレーム番号
            timestamp: タイムスタンプ
            vehicle: 対象車両
            world: CARLAワールド
        """
        vehicle_id = vehicle.id

        # 初期化
        if vehicle_id not in self.ttc_history:
            self.ttc_history[vehicle_id] = []
        if vehicle_id not in self.speed_history:
            self.speed_history[vehicle_id] = []
        if vehicle_id not in self.acceleration_history:
            self.acceleration_history[vehicle_id] = []
        if vehicle_id not in self.min_distances:
            self.min_distances[vehicle_id] = float("inf")

        # 現在の状態を取得
        velocity = vehicle.get_velocity()
        speed = self._calculate_speed(velocity)
        location = vehicle.get_location()

        # 速度履歴に追加
        self.speed_history[vehicle_id].append(speed)

        # 加速度を計算
        acceleration = self._calculate_acceleration(vehicle_id, velocity, timestamp)
        if acceleration is not None:
            self.acceleration_history[vehicle_id].append(acceleration)

            # 急ブレーキ検出（負の加速度 = 減速）
            if acceleration < -self.config.sudden_braking_threshold:
                self.events.append(
                    MetricsEvent(
                        frame=frame,
                        timestamp=timestamp,
                        event_type="sudden_braking",
                        vehicle_id=vehicle_id,
                        value=abs(acceleration),
                        threshold=self.config.sudden_braking_threshold,
                        description=f"急ブレーキ検出: {abs(acceleration):.2f} m/s²",
                        location=(location.x, location.y, location.z),
                    )
                )

            # 急加速検出
            if acceleration > self.config.sudden_acceleration_threshold:
                self.events.append(
                    MetricsEvent(
                        frame=frame,
                        timestamp=timestamp,
                        event_type="sudden_acceleration",
                        vehicle_id=vehicle_id,
                        value=acceleration,
                        threshold=self.config.sudden_acceleration_threshold,
                        description=f"急加速検出: {acceleration:.2f} m/s²",
                        location=(location.x, location.y, location.z),
                    )
                )

            # ジャーク検出
            jerk = self._calculate_jerk(vehicle_id, acceleration)
            if jerk is not None and abs(jerk) > self.config.jerk_threshold:
                self.events.append(
                    MetricsEvent(
                        frame=frame,
                        timestamp=timestamp,
                        event_type="high_jerk",
                        vehicle_id=vehicle_id,
                        value=abs(jerk),
                        threshold=self.config.jerk_threshold,
                        description=f"高ジャーク検出: {abs(jerk):.2f} m/s³",
                        location=(location.x, location.y, location.z),
                    )
                )

        # TTC計算（前方車両）
        ttc = self._calculate_ttc(vehicle, world)
        if ttc is not None:
            self.ttc_history[vehicle_id].append(ttc)

            # TTC閾値違反検出
            if ttc < self.config.ttc_threshold:
                self.events.append(
                    MetricsEvent(
                        frame=frame,
                        timestamp=timestamp,
                        event_type="low_ttc",
                        vehicle_id=vehicle_id,
                        value=ttc,
                        threshold=self.config.ttc_threshold,
                        description=f"TTC閾値違反: {ttc:.2f}秒",
                        location=(location.x, location.y, location.z),
                    )
                )

        # 最小車間距離を更新
        min_distance = self._calculate_min_distance_to_leading(vehicle, world)
        if min_distance is not None:
            if min_distance < self.min_distances[vehicle_id]:
                self.min_distances[vehicle_id] = min_distance

            # 最小車間距離閾値違反検出
            if min_distance < self.config.min_distance_threshold:
                self.events.append(
                    MetricsEvent(
                        frame=frame,
                        timestamp=timestamp,
                        event_type="min_distance_violation",
                        vehicle_id=vehicle_id,
                        value=min_distance,
                        threshold=self.config.min_distance_threshold,
                        description=f"最小車間距離違反: {min_distance:.2f}m",
                        location=(location.x, location.y, location.z),
                    )
                )

        # 前回データを保存
        self._prev_velocity[vehicle_id] = velocity

    def _calculate_speed(self, velocity: carla.Vector3D) -> float:
        """速度を計算 [m/s]"""
        import math

        return math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)

    def _calculate_acceleration(
        self,
        vehicle_id: int,
        current_velocity: carla.Vector3D,
        timestamp: float,
        dt: float = 0.05,
    ) -> Optional[float]:
        """
        加速度を計算 [m/s^2]

        Args:
            vehicle_id: 車両ID
            current_velocity: 現在の速度ベクトル
            timestamp: タイムスタンプ
            dt: 時間差分（デフォルト: 0.05秒 = 20 FPS）
        """
        if vehicle_id not in self._prev_velocity:
            return None

        prev_velocity = self._prev_velocity[vehicle_id]
        current_speed = self._calculate_speed(current_velocity)
        prev_speed = self._calculate_speed(prev_velocity)

        # 縦方向加速度（速度の変化率）
        acceleration = (current_speed - prev_speed) / dt
        return acceleration

    def _calculate_jerk(
        self,
        vehicle_id: int,
        current_acceleration: float,
        dt: float = 0.05,
    ) -> Optional[float]:
        """
        ジャーク（加速度の変化率）を計算 [m/s^3]

        Args:
            vehicle_id: 車両ID
            current_acceleration: 現在の加速度
            dt: 時間差分
        """
        if vehicle_id not in self._prev_acceleration:
            self._prev_acceleration[vehicle_id] = current_acceleration
            return None

        prev_acceleration = self._prev_acceleration[vehicle_id]
        jerk = (current_acceleration - prev_acceleration) / dt
        self._prev_acceleration[vehicle_id] = current_acceleration
        return jerk

    def _calculate_ttc(
        self, vehicle: carla.Vehicle, world: carla.World
    ) -> Optional[float]:
        """
        TTC (Time To Collision) を計算 [秒]

        前方車両との相対速度と距離から衝突時間を計算します。

        Returns:
            TTC [秒]、前方車両がいない場合はNone
        """
        # 前方車両を検出
        leading_vehicle = self._get_leading_vehicle(vehicle, world)
        if leading_vehicle is None:
            return None

        # 相対速度を計算
        ego_velocity = vehicle.get_velocity()
        lead_velocity = leading_vehicle.get_velocity()

        ego_speed = self._calculate_speed(ego_velocity)
        lead_speed = self._calculate_speed(lead_velocity)

        relative_speed = ego_speed - lead_speed

        # 前方車両が速い、または同じ速度の場合はTTCは無限大
        if relative_speed <= 0:
            return None

        # 距離を計算
        ego_location = vehicle.get_location()
        lead_location = leading_vehicle.get_location()
        distance = ego_location.distance(lead_location)

        # TTC = 距離 / 相対速度
        ttc = distance / relative_speed
        return ttc

    def _calculate_min_distance_to_leading(
        self, vehicle: carla.Vehicle, world: carla.World
    ) -> Optional[float]:
        """前方車両との最小距離を計算 [m]"""
        leading_vehicle = self._get_leading_vehicle(vehicle, world)
        if leading_vehicle is None:
            return None

        ego_location = vehicle.get_location()
        lead_location = leading_vehicle.get_location()
        distance = ego_location.distance(lead_location)
        return distance

    def _get_leading_vehicle(
        self, vehicle: carla.Vehicle, world: carla.World, search_distance: float = 50.0
    ) -> Optional[carla.Vehicle]:
        """
        前方車両を検出

        Args:
            vehicle: 対象車両
            world: CARLAワールド
            search_distance: 検索距離 [m]

        Returns:
            前方車両、いない場合はNone
        """
        import math

        ego_location = vehicle.get_location()
        ego_transform = vehicle.get_transform()
        ego_forward = ego_transform.get_forward_vector()

        # 全車両をスキャン
        all_vehicles = world.get_actors().filter("vehicle.*")
        leading_vehicle = None
        min_distance = float("inf")

        for other_vehicle in all_vehicles:
            if other_vehicle.id == vehicle.id:
                continue

            other_location = other_vehicle.get_location()
            distance = ego_location.distance(other_location)

            # 検索距離内かチェック
            if distance > search_distance:
                continue

            # 前方にいるかチェック
            to_other = other_location - ego_location
            dot_product = (
                ego_forward.x * to_other.x
                + ego_forward.y * to_other.y
                + ego_forward.z * to_other.z
            )

            # 前方（dot > 0）かつ最も近い車両
            if dot_product > 0 and distance < min_distance:
                min_distance = distance
                leading_vehicle = other_vehicle

        return leading_vehicle

    def finalize(self) -> str:
        """
        メトリクスをファイナライズしてJSONファイルに保存

        Returns:
            保存されたファイルのパス
        """
        output_dir = Path("data/logs/metrics")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{self.scenario_uuid}_metrics.json"

        # サマリーを計算
        summary = self._calculate_summary()

        # JSON形式で保存
        data = {
            "scenario_uuid": self.scenario_uuid,
            "config": {
                "ttc_threshold": self.config.ttc_threshold,
                "sudden_braking_threshold": self.config.sudden_braking_threshold,
                "sudden_acceleration_threshold": self.config.sudden_acceleration_threshold,
                "lateral_acceleration_threshold": self.config.lateral_acceleration_threshold,
                "jerk_threshold": self.config.jerk_threshold,
                "min_distance_threshold": self.config.min_distance_threshold,
                "speed_violation_margin": self.config.speed_violation_margin,
            },
            "summary": summary,
            "events": [
                {
                    "frame": event.frame,
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "vehicle_id": event.vehicle_id,
                    "value": event.value,
                    "threshold": event.threshold,
                    "description": event.description,
                    "location": event.location,
                }
                for event in self.events
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def _calculate_summary(self) -> dict:
        """サマリー統計を計算"""
        event_counts = {}
        for event in self.events:
            event_type = event.event_type
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        # 最小TTCを計算
        min_ttc_per_vehicle = {}
        for vehicle_id, ttc_list in self.ttc_history.items():
            if ttc_list:
                min_ttc_per_vehicle[vehicle_id] = min(ttc_list)

        return {
            "total_events": len(self.events),
            "event_counts": event_counts,
            "min_ttc_per_vehicle": min_ttc_per_vehicle,
            "min_distances": self.min_distances,
        }

    def print_summary(self):
        """サマリーをコンソールに出力"""
        summary = self._calculate_summary()

        print("\n" + "=" * 60)
        print(f"  Safety Metrics Summary: {self.scenario_uuid}")
        print("=" * 60)

        print(f"\n【イベント統計】")
        print(f"  総イベント数: {summary['total_events']}")
        if summary["event_counts"]:
            for event_type, count in summary["event_counts"].items():
                print(f"    - {event_type}: {count}")
        else:
            print("    (イベントなし)")

        print(f"\n【最小TTC】")
        if summary["min_ttc_per_vehicle"]:
            for vehicle_id, min_ttc in summary["min_ttc_per_vehicle"].items():
                print(f"    Vehicle {vehicle_id}: {min_ttc:.2f}秒")
        else:
            print("    (データなし)")

        print(f"\n【最小車間距離】")
        if summary["min_distances"]:
            for vehicle_id, min_dist in summary["min_distances"].items():
                if min_dist != float("inf"):
                    print(f"    Vehicle {vehicle_id}: {min_dist:.2f}m")
        else:
            print("    (データなし)")

        print("=" * 60 + "\n")

    def get_events_by_type(self, event_type: str) -> List[MetricsEvent]:
        """特定タイプのイベントを取得"""
        return [event for event in self.events if event.event_type == event_type]

    def get_semantic_coverage(self) -> dict:
        """
        意味論的カバレッジを計算

        Returns:
            カバレッジ辞書（各イベントタイプの発生有無）
        """
        coverage = {
            "sudden_braking": False,
            "sudden_acceleration": False,
            "high_jerk": False,
            "low_ttc": False,
            "min_distance_violation": False,
        }

        for event in self.events:
            if event.event_type in coverage:
                coverage[event.event_type] = True

        return coverage
