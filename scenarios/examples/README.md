# シナリオ実装例

## 📋 基本シナリオ

### example_scenario.py
基本的なCARLAシナリオの例。

```bash
uv run python scenarios/examples/example_scenario.py
```

## 🎥 スペクターカメラと動画記録

### spectator_camera_example.py
ego車両の後方上にカメラを配置し、imageioで動画を記録する例。

**実装のポイント**:
- RGBカメラセンサーを車両の後方上に取り付け（x=-5.0, y=0.0, z=2.5）
- Pitch -15°で視点を調整
- imageioでMP4形式で保存

## 🚨 CARLA環境の制約

### 利用可能なマップ
- `Town10HD_Opt` （デフォルト推奨）
- `NishishinjukuMap`

### 利用可能な車両
- `vehicle.taxi.ford` （推奨）
- その他17台の車両

詳細: `uv run python scripts/list_vehicles.py`
