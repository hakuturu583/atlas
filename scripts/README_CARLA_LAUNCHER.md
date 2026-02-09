# CARLA Launcher

CARLAシミュレーターを起動・停止・管理するためのCLIツールです。

## 概要

**重要**: このツールは**carla Pythonパッケージに依存しません**。`CarlaUnreal.sh`シェルスクリプトを直接実行します。

## インストール

carla Pythonパッケージは不要です。以下のコマンドで依存関係をインストール:

```bash
make install
# または
uv sync
```

## 基本的な使い方

### CARLA起動

```bash
# デフォルト設定で起動
make carla-launch
# または
uv run python scripts/carla_launcher.py launch

# カスタムポートで起動
make carla-launch PORT=2001
# または
uv run python scripts/carla_launcher.py launch --port 2001

# 特定のマップで起動
make carla-launch MAP=Town04
# または
uv run python scripts/carla_launcher.py launch --map Town04

# ポートとマップを両方指定
make carla-launch PORT=2001 MAP=Town04
# または
uv run python scripts/carla_launcher.py launch --port 2001 --map Town04
```

### CARLA停止

```bash
# CARLA停止
make carla-stop
# または
uv run python scripts/carla_launcher.py stop
```

### 状態確認

```bash
# 基本的な状態確認
make carla-status
# または
uv run python scripts/carla_launcher.py status

# 詳細な状態確認（設定情報含む）
uv run python scripts/carla_launcher.py status -v
```

### 設定変更

```bash
# CARLAインストールパスを設定
make carla-config PATH=/opt/carla-simulator
# または
uv run python scripts/carla_launcher.py config --carla-path /opt/carla-simulator

# デフォルトポートを変更
make carla-config PORT=2001
# または
uv run python scripts/carla_launcher.py config --port 2001

# デフォルトマップを変更
make carla-config MAP=Town10HD
# または
uv run python scripts/carla_launcher.py config --map Town10HD

# 複数の設定を同時に変更
uv run python scripts/carla_launcher.py config \
    --carla-path /opt/carla-simulator \
    --port 2001 \
    --map Town10HD \
    --quality Low \
    --additional-args "-RenderOffScreen -nosound -nullrhi"

# 品質レベルを変更
make carla-config QUALITY=Low
# または
uv run python scripts/carla_launcher.py config --quality Low

# 追加引数を設定
uv run python scripts/carla_launcher.py config --additional-args "-RenderOffScreen -nosound"

# タイムアウトを変更
make carla-config TIMEOUT=120
# または
uv run python scripts/carla_launcher.py config --timeout 120
```

## 設定ファイル

設定は`data/carla_settings.json`に保存されます。

### デフォルト設定

```json
{
  "carla_path": "/opt/carla",
  "executable_name": "CarlaUnreal.sh",
  "default_port": 2000,
  "default_map": "Town10HD",
  "quality_level": "Low",
  "additional_args": "-RenderOffScreen -nosound -nullrhi",
  "timeout": 60,
  "auto_start": false
}
```

### 設定項目の説明

| 項目 | 説明 | デフォルト | 例 |
|------|------|-----------|-----|
| `carla_path` | CARLAインストールディレクトリ | `/opt/carla` | `/opt/carla-simulator` |
| `executable_name` | 実行ファイル名 | `CarlaUnreal.sh` | `CarlaUE4.exe` (Windows) |
| `default_port` | デフォルトRPCポート | `2000` | `2001` |
| `default_map` | デフォルトマップ名 | `Town10HD` | `Town04` |
| `quality_level` | グラフィック品質 | `Low` | `Low`, `Medium`, `Epic` |
| `additional_args` | 追加の起動引数 | `-RenderOffScreen -nosound -nullrhi` | `-windowed -ResX=1280` |
| `timeout` | 起動タイムアウト（秒） | `60` | `120` |
| `auto_start` | 自動起動 | `false` | `true` |

## 起動引数の詳細

### 基本引数

- `-carla-rpc-port=<PORT>`: RPCポート番号
- `-carla-world=<MAP>`: マップ名（例: `Town10HD`, `Town04`, `Town01`, `Town02`）
- `-quality-level=<LEVEL>`: 品質レベル（`Low`, `Medium`, `Epic`）

### ヘッドレスモード用引数（推奨）

- `-RenderOffScreen`: オフスクリーンレンダリング
- `-nosound`: サウンド無効化
- `-nullrhi`: NullRHI（レンダリング完全無効）
- `-opengl`: OpenGL使用（Vulkanの代わり）

### その他の有用な引数

- `-windowed`: ウィンドウモード
- `-ResX=<WIDTH> -ResY=<HEIGHT>`: 解像度設定
- `-benchmark`: ベンチマークモード
- `-fps=<FPS>`: FPS固定

## 使用例

### 例1: デフォルト設定で起動

```bash
# 設定を確認
make carla-status

# 起動
make carla-launch

# 出力例:
# 🚗 Launching CARLA...
# Starting CARLA...
# ✓ CARLAを起動しました (PID: 12345)
#   Host: localhost
#   Port: 2000
#   PID: 12345
#   Command: /opt/carla/CarlaUnreal.sh -carla-rpc-port=2000 ...
```

### 例2: カスタム設定で起動

```bash
# ポート2001、Town04マップで起動
make carla-launch PORT=2001 MAP=Town04

# 出力例:
# 🚗 Launching CARLA...
# Starting CARLA...
# ✓ CARLAを起動しました (PID: 12346)
#   Host: localhost
#   Port: 2001
#   PID: 12346
#   Command: /opt/carla/CarlaUnreal.sh -carla-rpc-port=2001 -carla-world=Town04 ...
```

### 例3: 設定を変更してから起動

```bash
# CARLAパスを設定
make carla-config PATH=/opt/carla-simulator

# 起動
make carla-launch

# 出力例:
# ⚙️  Updating CARLA settings...
# ✓ Settings updated:
#   carla_path: /opt/carla-simulator
```

### 例4: 状態確認と停止

```bash
# 状態確認
make carla-status

# 出力例:
# === CARLA Status ===
# Status: Running
# PID: 12345
# Host: localhost
# Port: 2000
# Memory: 1234.5 MB
# CPU: 25.0%

# 停止
make carla-stop

# 出力例:
# 🛑 Stopping CARLA...
# Stopping CARLA...
# ✓ CARLAを停止しました (PID: 12345)
```

## Pythonコードからの利用

```python
from app.services.carla_manager import get_carla_manager
import asyncio

async def main():
    # マネージャー取得
    manager = get_carla_manager()

    # 起動
    result = await manager.launch_carla(port=2000, map_name="Town04")
    if result["success"]:
        print(f"CARLA started: PID={result['pid']}, Port={result['port']}")
    else:
        print(f"Failed to start CARLA: {result['message']}")

    # 状態確認
    status = manager.get_status()
    if status["running"]:
        print(f"CARLA is running: PID={status['pid']}")
        print(f"Memory: {status['memory_mb']:.1f} MB")
        print(f"CPU: {status['cpu_percent']:.1f}%")
    else:
        print("CARLA is not running")

    # 停止
    result = manager.stop_carla()
    if result["success"]:
        print("CARLA stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

## トラブルシューティング

### 起動がタイムアウトする

**症状**: `CARLAの起動がタイムアウトしました (60秒)`

**解決策**:
```bash
# タイムアウトを増やす
make carla-config TIMEOUT=120

# 再起動
make carla-launch
```

### 実行ファイルが見つからない

**症状**: `CARLA実行ファイルが見つかりません: /opt/carla/CarlaUnreal.sh`

**解決策**:
```bash
# 設定を確認
uv run python scripts/carla_launcher.py status -v

# 正しいパスを設定
make carla-config PATH=/correct/path/to/carla

# 実行権限を確認
chmod +x /correct/path/to/carla/CarlaUnreal.sh
```

### ポートが既に使用中

**症状**: ポート2000が既に使用されている

**解決策**:
```bash
# 既存のプロセスを確認
lsof -i:2000

# 別のポートで起動
make carla-launch PORT=2001

# またはデフォルトポートを変更
make carla-config PORT=2001
make carla-launch
```

### プロセスが残っている

**症状**: 停止後もプロセスが残っている

**解決策**:
```bash
# 強制停止
pkill -9 -f CarlaUnreal

# 確認
ps aux | grep CarlaUnreal

# 再起動
make carla-launch
```

### メモリ不足

**症状**: CARLAが起動しない、またはクラッシュする

**解決策**:
```bash
# ヘッドレスモードで起動（推奨）
make carla-config ARGS="-RenderOffScreen -nosound -nullrhi"
make carla-launch

# 品質を下げる
make carla-config QUALITY=Low
make carla-launch
```

## システム統合

### status コマンド

```bash
make status
```

出力例:
```
=== ATLAS System Status ===

Flask Application (port 8000):
  ✓ Running (PID: 12345)

MCP Server:
  ✓ Running (PID: 67890)

CARLA Server:
  ✓ Running

Sandbox Containers:
  carla-sandbox  Up 10 minutes
```

## 実装の詳細

### アーキテクチャ

```
scripts/carla_launcher.py (CLI)
    ↓
app/services/carla_manager.py (CarlaManager)
    ↓
app/models/carla_settings.py (CarlaSettings)
    ↓
subprocess.Popen (CarlaUnreal.sh実行)
```

### 主要機能

1. **carla Pythonパッケージ不要**: シェルスクリプトを直接実行
2. **ポート監視**: ソケット接続でCARLA起動を検出
3. **プロセスグループ管理**: 子プロセスも含めて終了
4. **設定永続化**: JSON形式で設定を保存

## 注意事項

1. **CARLA 0.9.15以降**: CarlaUnreal.shが存在するバージョンを使用
2. **Linux専用**: 現在の実装はLinux（CarlaUnreal.sh）を想定
   - Windows版は`executable_name`を`CarlaUE4.exe`に変更
3. **実行権限**: シェルスクリプトに実行権限が必要
4. **GPU**: ヘッドレスモードで起動する場合は`-nullrhi`を使用

## 参考資料

- [CARLA Command-line Options](https://carla.readthedocs.io/en/latest/adv_commandline_options/)
- [CARLA Maps](https://carla.readthedocs.io/en/latest/core_map/)
- [CARLA Python API](https://carla.readthedocs.io/en/latest/python_api/)
