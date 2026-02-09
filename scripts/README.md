# ATLAS Scripts

このディレクトリには、ATLASプロジェクトで使用するスクリプトが含まれています。

## auto_launch_sandbox.py ⭐ 推奨

**自動起動スクリプト - 起動を完全に保証します**

UUIDの自動生成、CARLA接続確認、コンテナ起動確認まで自動的に行い、起動が成功したことをプログラムで保証します。

### 特徴

- ✅ UUIDを自動生成
- ✅ CARLA接続確認（localhost:2000）
- ✅ ワークスペースディレクトリ自動作成
- ✅ コンテナ起動待機
- ✅ 起動成功を検証
- ✅ 詳細なエラーメッセージ

### 使い方

```bash
# 最もシンプル（すべて自動）
uv run python scripts/auto_launch_sandbox.py

# または Makeコマンド
make sandbox-auto

# UUID指定で起動
uv run python scripts/auto_launch_sandbox.py --uuid my-scenario-001

# CARLAチェックをスキップ（テスト用）
uv run python scripts/auto_launch_sandbox.py --no-check-carla

# タイムアウト指定
uv run python scripts/auto_launch_sandbox.py --timeout 180

# 詳細ログ表示
uv run python scripts/auto_launch_sandbox.py --verbose
```

### 出力例

```
======================================================================
🚀 CARLA Sandbox Automatic Launcher
======================================================================

📋 Configuration:
   CARLA Server: localhost:2000
   UUID: (auto-generate)
   Check CARLA: True
   Wait for ready: True
   Timeout: 120s

🔄 Launching sandbox...

======================================================================
✅ Sandbox launched successfully!
======================================================================

📦 Sandbox Information:
   UUID: a6975212-17ee-418e-934d-9387a504be98
   Container: carla-scenario-a6975212-17ee-418e-934d-9387a504be98
   Workspace: sandbox/workspace/a6975212-17ee-418e-934d-9387a504be98
   Status: Running

   CARLA: Connected ✓

💡 Next Steps:
   - Check status: uv run python scripts/launch_sandbox.py status --uuid a6975212-17ee-418e-934d-9387a504be98
   - View output: ls -lh sandbox/workspace/a6975212-17ee-418e-934d-9387a504be98/output/
   - Stop sandbox: uv run python scripts/launch_sandbox.py stop --uuid a6975212-17ee-418e-934d-9387a504be98
```

## launch_sandbox.py

PythonからCARLA Sandboxを管理するCLIツールです。

### 機能

- 新しいSandboxの起動（UUID自動生成）
- 既存のSandboxの再起動（UUID指定）
- Sandboxの停止・削除
- Sandboxワークスペースの一覧表示
- Sandbox状態の確認

### 使い方

#### 方法1: uvコマンドで実行（推奨）

```bash
# 新しいSandboxを起動
uv run python scripts/launch_sandbox.py launch

# 既存のSandboxを起動
uv run python scripts/launch_sandbox.py launch --uuid 550e8400-e29b-41d4-a716-446655440000

# Sandbox一覧を表示
uv run python scripts/launch_sandbox.py list

# Sandbox状態を確認
uv run python scripts/launch_sandbox.py status --uuid 550e8400-e29b-41d4-a716-446655440000

# Sandboxを停止
uv run python scripts/launch_sandbox.py stop --uuid 550e8400-e29b-41d4-a716-446655440000

# Sandboxを停止してワークスペースも削除
uv run python scripts/launch_sandbox.py stop --uuid 550e8400-e29b-41d4-a716-446655440000 --clean

# すべてのSandboxを停止
uv run python scripts/launch_sandbox.py stop-all

# ワークスペースを削除
uv run python scripts/launch_sandbox.py clean --uuid 550e8400-e29b-41d4-a716-446655440000
```

#### 方法2: シェルスクリプトラッパー経由で実行

```bash
# 新しいSandboxを起動
./scripts/launch-sandbox.sh launch

# 既存のSandboxを起動
./scripts/launch-sandbox.sh launch --uuid 550e8400-e29b-41d4-a716-446655440000

# Sandbox一覧を表示
./scripts/launch-sandbox.sh list

# その他のコマンドも同様
./scripts/launch-sandbox.sh --help
```

#### 方法3: Makeコマンドで実行（最も簡単）

```bash
# 新しいSandboxを起動
make sandbox-launch

# 既存のSandboxを起動
make sandbox-launch UUID=550e8400-e29b-41d4-a716-446655440000

# Sandbox一覧を表示
make sandbox-list

# Sandbox状態を確認
make sandbox-status UUID=550e8400-e29b-41d4-a716-446655440000

# Sandboxを停止
make sandbox-stop UUID=550e8400-e29b-41d4-a716-446655440000

# すべてのSandboxを停止
make sandbox-stop-all

# ワークスペースを削除
make sandbox-clean UUID=550e8400-e29b-41d4-a716-446655440000
```

### 出力例

#### launch

```bash
$ uv run python scripts/launch_sandbox.py launch
🚀 Launching sandbox...
   Generating new UUID...

📦 Sandbox UUID: 550e8400-e29b-41d4-a716-446655440000
   Workspace: sandbox/workspace/550e8400-e29b-41d4-a716-446655440000

✅ Sandbox launched successfully!
```

#### list

```bash
$ uv run python scripts/launch_sandbox.py list
📦 Found 2 sandbox(es):

🟢 UUID: 550e8400-e29b-41d4-a716-446655440000
   Status: running
   Container: carla-scenario-550e8400-e29b-41d4-a716-446655440000
   Build: 128M
   Output: 45M (3 files)
   Created: 2026-02-06 12:34:56

🔴 UUID: 6ba7b810-9dad-11d1-80b4-00c04fd430c8
   Status: stopped
   Container: carla-scenario-6ba7b810-9dad-11d1-80b4-00c04fd430c8
   Build: 132M
   Output: 52M (5 files)
   Created: 2026-02-05 18:22:10
```

#### status

```bash
$ uv run python scripts/launch_sandbox.py status --uuid 550e8400-e29b-41d4-a716-446655440000
🟢 Sandbox: 550e8400-e29b-41d4-a716-446655440000
   Status: running
   Container: carla-scenario-550e8400-e29b-41d4-a716-446655440000
   Workspace: sandbox/workspace/550e8400-e29b-41d4-a716-446655440000
   Build: 128M
   Output: 45M (3 files)
   Created: 2026-02-06 12:34:56
```

## Pythonコードから使用する

### 方法1: SandboxLauncher（推奨）- 起動を保証

```python
from app.services import sandbox_launcher

# シンプルな起動（すべて自動）
result = sandbox_launcher.launch_and_wait()

if result.success:
    print(f"✅ Success! UUID: {result.uuid}")
    print(f"   Container: {result.container_name}")
    print(f"   Workspace: {result.workspace_path}")
else:
    print(f"❌ Failed: {result.error_message}")

# カスタム設定で起動
result = sandbox_launcher.launch_with_validation(
    scenario_uuid="my-scenario-001",  # UUIDを指定
    check_carla=True,                 # CARLA接続確認
    wait_for_ready=True,              # 起動完了を待機
    timeout=180.0                     # タイムアウト（秒）
)

# エラーハンドリング
if not result.success:
    if result.carla_connected is False:
        print("CARLA server is not running")
    elif not result.container_running:
        print("Container failed to start")
```

### 方法2: SandboxManager（低レベルAPI）

```python
from app.services import sandbox_manager

# 新しいSandboxを起動
uuid, result = sandbox_manager.launch_sandbox()
print(f"Launched sandbox: {uuid}")

# Sandbox一覧を取得
sandboxes = sandbox_manager.list_sandboxes()
for sb in sandboxes:
    print(f"{sb.uuid}: {sb.status}")

# 特定のSandbox情報を取得
info = sandbox_manager.get_sandbox_info(uuid)
print(f"Status: {info.status}")
print(f"Output files: {info.output_files}")

# Sandboxを停止
result = sandbox_manager.stop_sandbox(uuid)
print(f"Stopped: {result.returncode == 0}")
```

### ScenarioManagerとの統合

```python
from app.services import sandbox_launcher, scenario_manager
from app.models.scenario import Scenario

# Sandboxを起動
result = sandbox_launcher.launch_and_wait()

if result.success:
    # シナリオを作成
    scenario = Scenario(
        id=f"scenario_{result.uuid[:8]}",
        name="My Scenario",
        description="Auto-launched scenario",
        sandbox_uuid=result.uuid,
        container_status="running" if result.container_running else "stopped",
        workspace_path=str(result.workspace_path)
    )

    # 保存
    scenario_manager.create_scenario(scenario)
    print(f"Created scenario: {scenario.id}")
```

## 環境要件

- Python 3.10+
- uv (パッケージマネージャー)
- Docker & Docker Compose
- CARLAサーバー（ポート2000で起動）

## トラブルシューティング

### 仮想環境が見つからない

```bash
Error: Virtual environment not found at /home/masaya/workspace/atlas/.venv
Please run: uv sync
```

**解決方法**:
```bash
uv sync
```

### Dockerが起動していない

```bash
❌ Failed to launch sandbox
...
Cannot connect to the Docker daemon
```

**解決方法**:
```bash
sudo systemctl start docker
# または
sudo service docker start
```

### CARLAサーバーが起動していない

Sandboxは起動しますが、シナリオ実行時にCARLAに接続できません。

**解決方法**:
```bash
# 別のターミナルでCARLAを起動
cd /path/to/carla
./CarlaUE4.sh
```
