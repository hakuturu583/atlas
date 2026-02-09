---
name: carla-launcher
description: This skill should be used when the user asks to "start CARLA", "launch CARLA server", "run CARLA simulator", "check CARLA status", or mentions "carla起動", "CARLAサーバー". Manages CARLA simulator lifecycle and connection status.
  - carla launch
  - carla start
  - carla stop
  - carla status
  - start carla
  - stop carla
  - carla server
---

# CARLA Launcher Skill

このスキルは、CARLAシミュレーターを起動・停止・管理します。

## 概要

CARLAシミュレーターの`CarlaUnreal.sh`を実行し、サーバーを起動・停止します。
Python carlaパッケージには**依存せず**、シェルスクリプトを直接実行します。

## 主要機能

### 1. CARLA起動
```bash
# デフォルト設定で起動
uv run python scripts/carla_launcher.py launch

# カスタムポートで起動
uv run python scripts/carla_launcher.py launch --port 2001

# 特定のマップで起動
uv run python scripts/carla_launcher.py launch --map Town04
```

### 2. CARLA停止
```bash
uv run python scripts/carla_launcher.py stop
```

### 3. 状態確認
```bash
# 基本的な状態確認
uv run python scripts/carla_launcher.py status

# 詳細な状態確認（設定情報含む）
uv run python scripts/carla_launcher.py status -v
```

### 4. 設定変更
```bash
# CARLAインストールパスを設定
uv run python scripts/carla_launcher.py config --carla-path /opt/carla-simulator

# デフォルトポートとマップを変更
uv run python scripts/carla_launcher.py config --port 2001 --map Town10HD

# 追加引数を設定
uv run python scripts/carla_launcher.py config --additional-args "-RenderOffScreen -nosound"

# 品質レベルを変更
uv run python scripts/carla_launcher.py config --quality Low
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

### 設定項目

- **carla_path**: CARLAインストールディレクトリのパス
- **executable_name**: 実行シェルスクリプト名（Linux: `CarlaUnreal.sh`、Windows: `CarlaUE4.exe`）
- **default_port**: デフォルトのRPCポート番号（1024-65535）
- **default_map**: デフォルトで読み込むマップ名
- **quality_level**: グラフィック品質（`Low`, `Medium`, `Epic`）
- **additional_args**: 追加の起動引数（スペース区切り）
- **timeout**: 起動タイムアウト（秒）（5-300）
- **auto_start**: システム起動時に自動起動するか

## 起動引数の詳細

### 基本引数

- `-carla-rpc-port=<PORT>`: RPCポート番号
- `-carla-world=<MAP>`: マップ名（例: `Town10HD`, `Town04`）
- `-quality-level=<LEVEL>`: 品質レベル（`Low`, `Medium`, `Epic`）

### ヘッドレスモード用引数

- `-RenderOffScreen`: オフスクリーンレンダリング
- `-nosound`: サウンド無効化
- `-nullrhi`: NullRHI（レンダリング無効）
- `-opengl`: OpenGL使用（Vulkanの代わり）

### その他の有用な引数

- `-windowed`: ウィンドウモード
- `-ResX=<WIDTH> -ResY=<HEIGHT>`: 解像度設定
- `-benchmark`: ベンチマークモード
- `-fps=<FPS>`: FPS固定

## 使用例

### 例1: デフォルト設定で起動

```
ユーザー: CARLAを起動して

エージェント:
1. uv run python scripts/carla_launcher.py launch を実行
2. 起動成功を確認
3. PID、ホスト、ポート情報を表示
```

### 例2: カスタム設定で起動

```
ユーザー: CARLAをポート2001、Town04マップで起動して

エージェント:
1. uv run python scripts/carla_launcher.py launch --port 2001 --map Town04 を実行
2. 起動成功を確認
3. 接続情報を表示
```

### 例3: 設定を変更してから起動

```
ユーザー: CARLAのパスを /opt/carla-simulator に設定して起動して

エージェント:
1. uv run python scripts/carla_launcher.py config --carla-path /opt/carla-simulator を実行
2. 設定が更新されたことを確認
3. uv run python scripts/carla_launcher.py launch を実行
4. 起動成功を確認
```

### 例4: 状態確認と停止

```
ユーザー: CARLAの状態を確認して、起動していたら停止して

エージェント:
1. uv run python scripts/carla_launcher.py status を実行
2. 起動中の場合:
   - PID、ポート、メモリ使用量を表示
   - uv run python scripts/carla_launcher.py stop を実行
   - 停止成功を確認
3. 起動していない場合:
   - "CARLAは起動していません" と表示
```

## トラブルシューティング

### 起動がタイムアウトする

- `timeout`設定を増やす: `uv run python scripts/carla_launcher.py config --timeout 120`
- CARLAのパスが正しいか確認: `uv run python scripts/carla_launcher.py status -v`
- ログを確認（起動時の標準出力/エラー出力）

### 実行ファイルが見つからない

```bash
# 設定を確認
uv run python scripts/carla_launcher.py status -v

# CARLAパスを修正
uv run python scripts/carla_launcher.py config --carla-path /correct/path/to/carla
```

### ポートが既に使用中

```bash
# 既存のCARLAプロセスを確認
lsof -i:2000

# 別のポートで起動
uv run python scripts/carla_launcher.py launch --port 2001
```

### プロセスが残っている

```bash
# 強制停止
pkill -9 -f CarlaUnreal

# 再起動
uv run python scripts/carla_launcher.py launch
```

## Pythonコードからの利用

```python
from app.services.carla_manager import get_carla_manager
import asyncio

# マネージャー取得
manager = get_carla_manager()

# 起動
result = await manager.launch_carla(port=2000, map_name="Town04")
if result["success"]:
    print(f"CARLA started: PID={result['pid']}, Port={result['port']}")

# 状態確認
status = manager.get_status()
if status["running"]:
    print(f"CARLA is running: PID={status['pid']}")

# 停止
result = manager.stop_carla()
if result["success"]:
    print("CARLA stopped")
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

### 重要な特徴

1. **carla Pythonパッケージ不要**: シェルスクリプトを直接実行
2. **ポート監視**: ソケット接続でCARLA起動を検出
3. **プロセスグループ管理**: 子プロセスも含めて終了
4. **設定永続化**: JSON形式で設定を保存

## 注意事項

1. **CARLA 0.9.15以降**: CarlaUnreal.shが存在するバージョンを使用
2. **Linux専用**: 現在の実装はLinux（CarlaUnreal.sh）を想定
3. **権限**: シェルスクリプトに実行権限が必要
4. **GPU**: ヘッドレスモードで起動する場合は`-nullrhi`を使用

## 関連スキル

- **carla-cpp-scenario**: C++でのCARLAシナリオ実装
- **rerun-carla-sdk**: Rerunを使ったCARLA可視化
- **scenario-writer**: 自動シナリオ生成

## 参考資料

- [CARLA Command-line Options](https://carla.readthedocs.io/en/latest/adv_commandline_options/)
- [CARLA Maps and Scenarios](https://carla.readthedocs.io/en/latest/core_map/)
