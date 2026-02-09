# UI設定とCARLA起動機能

右上の設定ボタンからCARLAの起動オプションを管理し、シナリオ実行時にCARLAを自動起動・終了できます。

## 設定UI

### アクセス方法

1. http://localhost:8000 にアクセス
2. 右ペイン（Claude Codeターミナル）の右上にある「⚙️ 設定」ボタンをクリック

### 設定項目

#### CARLAパス
- CARLAのインストールディレクトリ
- 例: `/home/user/CARLA_0.10.0`

#### デフォルトマップ
- シナリオ実行時に使用するCARLAマップ
- 選択肢: Town01, Town02, Town03, Town04, Town05, Town10HD_Opt

#### ポート
- CARLAサーバーのRPCポート
- デフォルト: 2000

#### 品質レベル
- レンダリング品質
- 選択肢: Low, Epic

#### オフスクリーンレンダリング
- `-RenderOffScreen` オプション
- ヘッドレス実行に必要

#### 起動時にCARLAを自動起動
- FastAPI起動時にCARLAを自動的に起動

### 設定の保存

設定は `data/carla_settings.json` に保存されます。

```json
{
  "carla_path": "/home/user/CARLA_0.10.0",
  "executable_name": "CarlaUE5.sh",
  "default_port": 2000,
  "default_map": "Town10HD_Opt",
  "quality_level": "Low",
  "additional_args": "-RenderOffScreen",
  "timeout": 60,
  "auto_start": false
}
```

## シナリオ実行スクリプト

### 基本的な使い方

```bash
./run_scenario.sh <logical-uuid> <parameter-uuid>
```

### CARLA自動起動・終了

```bash
# CARLAを起動してシナリオ実行後に停止
./run_scenario.sh <logical-uuid> <parameter-uuid> --start-carla --stop-carla
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--start-carla` | シナリオ実行前にCARLAを起動 | false |
| `--stop-carla` | シナリオ実行後にCARLAを停止 | false |
| `--carla-path PATH` | CARLAのパス | 設定ファイルから読み込み |
| `--carla-map MAP` | CARLAマップ | Town10HD_Opt |
| `--carla-port PORT` | CARLAポート | 2000 |

### 使用例

#### 例1: CARLA起動済みの場合

```bash
# CARLAが既に起動している場合（最もシンプル）
./run_scenario.sh ad353814-59cf-4911-9666-ed1c60268717 23991fb4-809d-45c7-9846-09bc226dfa7c
```

#### 例2: CARLAを自動起動・停止

```bash
# シナリオ実行前にCARLAを起動し、実行後に停止
./run_scenario.sh ad353814-59cf-4911-9666-ed1c60268717 23991fb4-809d-45c7-9846-09bc226dfa7c \
  --start-carla --stop-carla
```

#### 例3: カスタムCARLAパス

```bash
# カスタムCARLAパスを指定
./run_scenario.sh ad353814-59cf-4911-9666-ed1c60268717 23991fb4-809d-45c7-9846-09bc226dfa7c \
  --start-carla --stop-carla \
  --carla-path /custom/path/CARLA_0.10.0
```

#### 例4: カスタムマップとポート

```bash
# Town04マップをポート2001で起動
./run_scenario.sh ad353814-59cf-4911-9666-ed1c60268717 23991fb4-809d-45c7-9846-09bc226dfa7c \
  --start-carla --stop-carla \
  --carla-map Town04 \
  --carla-port 2001
```

## Claude Codeからの使い方

Claude Codeターミナル（右ペイン）で直接実行できます。

```bash
# 設定を確認
cat data/carla_settings.json | jq

# シナリオを実行（CARLA自動起動・停止）
./run_scenario.sh ad353814-59cf-4911-9666-ed1c60268717 23991fb4-809d-45c7-9846-09bc226dfa7c \
  --start-carla --stop-carla
```

### プロンプト例

Claude Codeに以下のように指示できます：

- 「設定ファイルのCARLAパスを確認して」
- 「シナリオad353814をCARLA自動起動で実行して」
- 「Town04マップでシナリオを実行して」

## ワークフロー例

### ワークフロー1: 手動CARLA管理

```bash
# 1. CARLAを手動で起動
cd /path/to/CARLA
./CarlaUE5.sh -RenderOffScreen

# 2. シナリオを実行
./run_scenario.sh <uuid> <uuid>

# 3. CARLAを手動で停止
pkill -f CarlaUE5
```

### ワークフロー2: 自動CARLA管理（推奨）

```bash
# 1回のコマンドで完結
./run_scenario.sh <uuid> <uuid> --start-carla --stop-carla
```

### ワークフロー3: 複数シナリオを連続実行

```bash
# CARLA起動
./run_scenario.sh <uuid1> <uuid1> --start-carla

# シナリオ2（CARLAは起動済み）
./run_scenario.sh <uuid2> <uuid2>

# シナリオ3（最後にCARLA停止）
./run_scenario.sh <uuid3> <uuid3> --stop-carla
```

## トラブルシューティング

### CARLAパスが設定されていない

```
Error: CARLAパスが設定されていません
```

**解決方法**:
1. Web UI（http://localhost:8000）の設定ボタンからCARLAパスを設定
2. または、コマンドラインで直接指定: `--carla-path /path/to/CARLA`

### CARLAが起動しない

```
Error: CARLAが起動しませんでした
```

**確認事項**:
1. CARLAパスが正しいか確認
2. CARLAの実行ファイル（`CarlaUE5.sh`）が存在するか確認
3. 十分なメモリがあるか確認（CARLA は 8GB以上推奨）

### ポートが既に使用されている

```
Warning: CARLAは既に起動しています
```

**解決方法**:
1. `--start-carla` オプションを外して実行
2. または、既存のCARLAプロセスを停止: `pkill -f CarlaUE5`

## 参考資料

- [CARLA Documentation](https://carla.readthedocs.io/)
- [CARLA Command-line Options](https://carla.readthedocs.io/en/latest/start_quickstart/#command-line-options)
