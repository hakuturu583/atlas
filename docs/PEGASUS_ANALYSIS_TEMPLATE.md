# PEGASUS分析テンプレート

## 目的

PEGASUS 6 Layerに基づいた**完全な**シナリオ分析。すべての実装パラメータを含める。

---

## Layer 1: Road-level (道路レベル)

**目的**: 道路の構造、トポロジー、ジオメトリ

```json
{
  "layer_1_road": {
    "description": "市街地T字路/十字路交差点",
    "expected_values": {
      "road_type": ["urban_intersection", "T_junction", "crossroad"],
      "lane_count": [2, 3],
      "lane_width": {"min": 3.0, "max": 3.5, "unit": "m"},
      "intersection_width": {"min": 6.0, "max": 10.0, "unit": "m"},
      "road_length": {"min": 100.0, "max": 200.0, "unit": "m"}
    },
    "carla_mapping": {
      "map": "Town10HD_Opt",
      "road_features": ["intersection", "multi_lane"],
      "spawn_area": "intersection_approach"
    }
  }
}
```

### 含めるべきパラメータ

- **road_type**: 道路タイプ（highway, urban, rural, intersection）
- **topology**: トポロジー（straight, curve, T_junction, crossroad）
- **lane_count**: レーン数
- **lane_width**: レーン幅
- **intersection_width**: 交差点の幅（該当する場合）
- **road_length**: 道路の長さ
- **curvature**: カーブ半径（該当する場合）

---

## Layer 2: Traffic Infrastructure (交通インフラ)

**目的**: 信号機、標識、道路標示

```json
{
  "layer_2_infrastructure": {
    "description": "信号機なし、一時停止標識あり",
    "expected_values": {
      "traffic_signals": false,
      "stop_signs": true,
      "stop_sign_locations": ["side_road_entry"],
      "road_markings": ["stop_line", "crosswalk"],
      "speed_limit": {"value": 50, "unit": "km/h"}
    },
    "carla_mapping": {
      "use_traffic_lights": false,
      "stop_sign_detection": true,
      "road_marking_detection": true
    }
  }
}
```

### 含めるべきパラメータ

- **traffic_signals**: 信号機の有無
- **signal_timing**: 信号のタイミング（赤/黄/青の時間）
- **stop_signs**: 一時停止標識の有無
- **speed_limit**: 速度制限
- **road_markings**: 道路標示（stop_line, crosswalk, lane_marking）

---

## Layer 3: Temporary Manipulation (一時的操作)

**目的**: 工事、障害物、視界遮蔽

```json
{
  "layer_3_temporary": {
    "description": "建物・駐車車両による視界遮蔽",
    "expected_values": {
      "occlusion_type": ["building", "parked_vehicle"],
      "occlusion_distance": {"min": 10.0, "max": 20.0, "unit": "m"},
      "occlusion_height": {"min": 1.5, "max": 3.0, "unit": "m"},
      "visibility_range": {"min": 5.0, "max": 15.0, "unit": "m"}
    },
    "carla_mapping": {
      "static_obstacles": ["building_corner"],
      "parked_vehicles": true,
      "parked_vehicle_count": {"min": 1, "max": 3}
    }
  }
}
```

### 含めるべきパラメータ

- **occlusion_type**: 遮蔽物のタイプ（building, parked_vehicle, construction）
- **occlusion_distance**: 遮蔽物までの距離
- **visibility_range**: 視界範囲
- **road_condition**: 道路状態（construction, obstacles）

---

## Layer 4: Moving Objects (移動物体) ⭐ 最重要

**目的**: 車両、歩行者、自転車、マニューバー

```json
{
  "layer_4_objects": {
    "description": "2台の車両（自車と飛び出し車両）",
    "expected_values": {
      "ego_vehicle": {
        "type": "vehicle",
        "vehicle_type": ["sedan", "suv"],
        "initial_speed": {"min": 40.0, "max": 50.0, "unit": "km/h"},
        "target_speed": {"min": 40.0, "max": 50.0, "unit": "km/h"},
        "distance_to_intersection": {"min": 40.0, "max": 60.0, "unit": "m"},
        "lane": "right_lane",
        "maneuver": "straight_driving",
        "behavior": "cautious"
      },
      "oncoming_vehicle": {
        "type": "vehicle",
        "vehicle_type": ["sedan", "hatchback"],
        "initial_state": "stopped",
        "initial_position": "side_road_hidden",
        "trigger_distance": {"min": 20.0, "max": 35.0, "unit": "m"},
        "trigger_condition": "ego_distance_to_intersection",
        "acceleration": {"min": 3.0, "max": 5.0, "unit": "m/s²"},
        "target_speed": {"min": 25.0, "max": 35.0, "unit": "km/h"},
        "maneuver": "sudden_entry",
        "behavior": "aggressive"
      }
    },
    "carla_mapping": {
      "ego_vehicle": {
        "vehicle_type": "vehicle.taxi.ford",
        "is_autonomous_stack": true
      },
      "oncoming_vehicle": {
        "vehicle_type": "vehicle.audi.a2",
        "is_autonomous_stack": false
      }
    }
  }
}
```

### 含めるべきパラメータ（車両ごと）

- **type**: 物体タイプ（vehicle, pedestrian, bicycle）
- **vehicle_type**: 車両タイプ（sedan, suv, truck）
- **initial_speed**: 初速度
- **target_speed**: 目標速度
- **acceleration**: 加速度
- **deceleration**: 減速度
- **initial_position**: 初期位置（symbolic）
- **distance_to_X**: 特定地点までの距離
- **lane**: レーン
- **maneuver**: マニューバー（straight, lane_change, turn_left, turn_right, overtake, sudden_entry）
- **behavior**: 振る舞い（cautious, normal, aggressive）
- **trigger_condition**: トリガー条件
- **trigger_distance**: トリガー距離

---

## Layer 5: Environment (環境)

**目的**: 天候、時間帯、路面状態

```json
{
  "layer_5_environment": {
    "description": "晴天、昼間、乾燥路面",
    "expected_values": {
      "weather": {
        "presets": ["ClearNoon", "CloudyNoon"],
        "distribution": "choice"
      },
      "time_of_day": {
        "value": "noon",
        "sun_altitude_angle": {"min": 60.0, "max": 80.0, "unit": "deg"}
      },
      "road_condition": "dry",
      "visibility": {"min": 100.0, "max": 200.0, "unit": "m"},
      "precipitation": "none",
      "wind_speed": {"min": 0.0, "max": 5.0, "unit": "m/s"}
    },
    "carla_mapping": {
      "weather_preset": "ClearNoon",
      "cloudiness": {"min": 0, "max": 20},
      "precipitation": 0,
      "sun_altitude_angle": 70.0
    }
  }
}
```

### 含めるべきパラメータ

- **weather**: 天候（clear, cloudy, rainy, foggy）
- **weather_presets**: CARLAのプリセット
- **time_of_day**: 時間帯（dawn, noon, dusk, night）
- **sun_altitude_angle**: 太陽高度
- **road_condition**: 路面状態（dry, wet, icy）
- **visibility**: 視界距離
- **precipitation**: 降水（none, light, heavy）
- **wind_speed**: 風速

---

## Layer 6: Digital Information (デジタル情報)

**目的**: センサー、V2X通信、カメラ設定

```json
{
  "layer_6_digital": {
    "description": "センサーベース認識（カメラ、LiDAR）",
    "expected_values": {
      "camera": {
        "offset_x": {"min": -8.0, "max": -4.0, "unit": "m"},
        "offset_y": {"value": 0.0, "unit": "m"},
        "offset_z": {"min": 2.5, "max": 4.0, "unit": "m"},
        "pitch": {"min": -25.0, "max": -15.0, "unit": "deg"},
        "fov": {"min": 80, "max": 100, "unit": "deg"},
        "image_size_x": 1280,
        "image_size_y": 720
      },
      "lidar": {
        "enabled": false,
        "channels": 64,
        "range": {"min": 50.0, "max": 100.0, "unit": "m"}
      },
      "simulation": {
        "duration": {"min": 8.0, "max": 12.0, "unit": "s"},
        "fixed_delta_seconds": 0.05,
        "synchronous_mode": true,
        "frame_rate": 20
      },
      "recording": {
        "video_enabled": true,
        "video_format": "mp4",
        "video_fps": 20,
        "rerun_enabled": false
      }
    },
    "carla_mapping": {
      "camera_blueprint": "sensor.camera.rgb",
      "video_recorder": "imageio"
    }
  }
}
```

### 含めるべきパラメータ

- **camera**: カメラ設定（offset, pitch, fov, 解像度）
- **lidar**: LiDAR設定（channels, range）
- **radar**: レーダー設定（該当する場合）
- **simulation**: シミュレーション設定（duration, fixed_delta_seconds, synchronous_mode）
- **recording**: 記録設定（video, rerun）
- **v2x**: V2X通信（将来対応）

---

## Criticality (危険度評価)

```json
{
  "criticality": {
    "level": "high",
    "factors": ["occlusion", "sudden_maneuver", "collision_risk"],
    "ttc_threshold": {"min": 1.0, "max": 2.0, "unit": "s"},
    "min_distance_threshold": {"min": 2.0, "max": 5.0, "unit": "m"},
    "severity": "major"
  }
}
```

---

## 重要な原則

1. **すべての実装パラメータを含める**
   - 論理シナリオで使用するパラメータは、すべてPEGASUS分析に記載

2. **expected_valuesの形式**
   - 固定値: `{"value": 10.0, "unit": "m"}`
   - 範囲: `{"min": 5.0, "max": 15.0, "unit": "m"}`
   - 選択肢: `["option1", "option2"]`または`{"presets": [...], "distribution": "choice"}`

3. **carla_mappingの明示**
   - CARLAでの実装方法を具体的に記載
   - マップ名、ブループリント、設定値

4. **トレーサビリティ**
   - PEGASUS分析 → 論理シナリオ の対応が明確
   - 各パラメータの由来が追跡可能
