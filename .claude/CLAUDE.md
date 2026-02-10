# ATLAS Project - Claude Code Instructions

このプロジェクトは **ATLAS** (Analytic Transparent LAnguage-driven Scenario generator for CARLA) です。

## 📋 目次

1. [プロジェクト概要](#プロジェクト概要)
2. [アーキテクチャ](#アーキテクチャ)
3. [ディレクトリ構造](#ディレクトリ構造)
4. [スキル](#スキル)
5. [スクリプトとツール](#スクリプトとツール)
6. [開発ワークフロー](#開発ワークフロー)
7. [起動・停止](#起動停止)
8. [トラブルシューティング](#トラブルシューティング)
9. [コーディング規約](#コーディング規約)

---

## プロジェクト概要

### 目的

CARLAシミュレーター用のシナリオ生成・管理ツールで、自然言語からシナリオを生成し、可視化・実行・分析を行います。

### 主要機能

1. **2ペインUI**
   - 左ペイン: Webアプリケーション（FastAPI + htmx）
   - 右ペイン: Claude Codeターミナル（xterm.js + WebSocket）

2. **Claude Code統合**
   - atlas-plugin スキルによる画面遷移とシナリオ管理
   - WebSocket経由でターミナル統合

3. **Python実装**
   - CARLA Python APIを使ったシナリオ実装
   - imageioによる動画記録

4. **rerun.io可視化**
   - 3D可視化ビューア内蔵
   - .rrdファイルによるログ記録

### 技術スタック

- **バックエンド**: Python 3.10+, FastAPI, uvicorn
- **フロントエンド**: htmx, Tailwind CSS, xterm.js
- **パッケージ管理**: uv (Pythonパッケージマネージャー)
- **通信**: WebSocket (Terminal, UI)

---

## アーキテクチャ

### システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                     ブラウザ (localhost:8000)                │
├───────────────────────────┬─────────────────────────────────┤
│  左ペイン (Webアプリ)      │  右ペイン (Claude Code)          │
│  - htmx でHTMLフラグメント │  - xterm.js ターミナル           │
│  - Tailwind CSS           │  - PTY経由でClaude Code実行      │
└───────────────┬───────────┴────────────┬────────────────────┘
                │ WebSocket              │ WebSocket
                │ (UI State)             │ (Terminal I/O)
┌───────────────▼────────────────────────▼────────────────────┐
│              FastAPI Application (port 8000)                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ app/routers/                                        │    │
│  │  - views.py      : HTML テンプレートレンダリング    │    │
│  │  - api.py        : REST API エンドポイント          │    │
│  │  - websocket.py  : WebSocket (Terminal, UI State)   │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ app/services/                                       │    │
│  │  - ui_state_manager.py   : UI状態管理              │    │
│  │  - scenario_manager.py   : シナリオ管理            │    │
│  │  - carla_manager.py      : CARLA起動管理           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│         Claude Code (右ペイン内で実行)                       │
│  - Working directory: /home/masaya/workspace/atlas           │
│  - .claude/atlas-plugin スキル自動読み込み                   │
│  - settings.local.json 権限適用                              │
└─────────────────────────────────────────────────────────────┘
```

### データフロー

1. **UI操作フロー**:
   ```
   ユーザー → ブラウザ(htmx) → FastAPI → UIStateManager → WebSocket → ブラウザ更新
   ```

2. **Claude Code操作フロー**:
   ```
   Claude Code → スキル実行 → FastAPI経由でUI更新
   ```

3. **ターミナル通信フロー**:
   ```
   ブラウザ(xterm.js) → WebSocket → PTY → Claude Code → PTY → WebSocket → ブラウザ
   ```

---

## ディレクトリ構造

### 重要: working directoryについて

- **Claude Codeのworking directory**: `/home/masaya/workspace/atlas/`
  - これがプロジェクトルートであり、Claude Codeはここで動作します
  - すべてのファイル操作はこのディレクトリを基準に行われます
  - `.claude/`配下の設定が自動的に読み込まれます

### 詳細構造

```
atlas/                              ← プロジェクトルート（working directory）
├── app/                            ← FastAPIアプリケーション
│   ├── main.py                     ← メインアプリ（FastAPIインスタンス）
│   ├── routers/                    ← APIルーター
│   │   ├── views.py                ← 画面レンダリング（Jinja2）
│   │   ├── api.py                  ← REST API エンドポイント
│   │   └── websocket.py            ← WebSocket通信（ターミナル、UI状態）
│   ├── services/                   ← ビジネスロジック
│   │   ├── ui_state_manager.py     ← UI状態管理（pub/sub）
│   │   └── scenario_manager.py     ← シナリオ管理
│   ├── models/                     ← データモデル（Pydantic）
│   │   ├── ui_state.py             ← UI状態モデル
│   │   └── scenario.py             ← シナリオモデル
│   ├── templates/                  ← Jinja2テンプレート
│   │   ├── app.html                ← 2ペインメインUI
│   │   └── views/                  ← 各画面テンプレート
│   │       ├── home.html
│   │       ├── scenario_list.html
│   │       ├── scenario_analysis.html
│   │       └── rerun_viewer.html
│   └── static/                     ← 静的ファイル
│       ├── css/
│       │   └── xterm.css           ← xterm.jsスタイル
│       └── js/
│           ├── xterm.js            ← xterm.jsライブラリ
│           └── xterm-addon-fit.js  ← xterm.js Fit addon
│
├── sandbox/                        ← Dockerサンドボックス環境
│   ├── Dockerfile                  ← コンテナ定義（conan/gcc11ベース）
│   ├── docker-compose.yml          ← Docker Compose設定（UUID対応）
│   ├── conanfile.txt               ← C++依存関係（libcarla, rerun_sdk）
│   ├── CMakeLists.txt              ← CMakeビルド設定
│   ├── src/
│   │   └── main.cpp                ← C++シナリオ実装（全シナリオ共有）
│   ├── workspace/                  ← シナリオごとのワークスペース
│   │   ├── {scenario-uuid-1}/      ← シナリオ1のワークスペース
│   │   │   ├── build/              ← ビルド成果物
│   │   │   └── output/             ← .rrdファイル出力先
│   │   ├── {scenario-uuid-2}/      ← シナリオ2のワークスペース
│   │   │   ├── build/
│   │   │   └── output/
│   │   └── .gitkeep
│   ├── output/                     ← レガシー出力（非推奨）
│   ├── build/                      ← レガシービルド（非推奨）
│   ├── run.sh                      ← サンドボックス起動スクリプト
│   ├── shutdown.sh                 ← サンドボックスシャットダウン
│   ├── Makefile                    ← サンドボックスMakefile
│   └── README.md                   ← サンドボックスドキュメント
│
├── .claude/                        ← Claude Code設定
│   ├── CLAUDE.md                   ← このファイル（プロジェクト指示）
│   ├── skills/                     ← スキル（Claude Codeが自動読み込み）
│   │   ├── scenario-writer/
│   │   │   └── SKILL.md            ← シナリオ自動生成スキル
│   │   ├── scenario-manager/
│   │   │   └── SKILL.md            ← シナリオ管理スキル
│   │   ├── pegasus-analyzer/
│   │   │   └── SKILL.md            ← PEGASUS分析スキル
│   │   ├── carla-launcher/
│   │   │   └── SKILL.md            ← CARLA起動管理スキル
│   │   ├── carla-python-scenario/
│   │   │   └── SKILL.md            ← Python APIスキル
│   │   ├── cleanup/
│   │   │   └── SKILL.md            ← クリーンアップスキル
│   │   ├── scenario-breakdown/
│   │   │   └── SKILL.md            ← シナリオブレークダウンスキル
│   │   ├── rerun-carla-sdk/
│   │   │   └── SKILL.md            ← Rerun可視化スキル
│   │   ├── fiftyone-integration/
│   │   │   └── SKILL.md            ← FiftyOne統合スキル
│   │   └── test-simple/
│   │       └── SKILL.md            ← テストスキル
│   ├── atlas-plugin/               ← プラグイン（スキルのソース）
│   │   ├── plugin.json             ← プラグイン定義
│   │   ├── commands/               ← スラッシュコマンド
│   │   │   └── view.md             ← /view コマンド
│   │   └── skills/                 ← スキルのソース（.claude/skills/にコピー済み）
│   │       ├── scenario-writer/
│   │       ├── scenario-manager/
│   │       └── ... (10個のスキル)
│   └── settings.local.json         ← 権限設定（Bash許可リスト）
│
├── agent_controller/               ← CARLA Traffic Manager Wrapper（🆕）
│   ├── __init__.py                 ← パッケージエントリポイント
│   ├── traffic_manager_wrapper.py  ← Traffic Managerラッパー
│   ├── behaviors.py                ← 高レベル振る舞い（レーンチェンジ、カットインなど）
│   ├── stamp_logger.py             ← STAMP状態遷移ロガー
│   ├── command_tracker.py          ← ユーザー指示追跡
│   └── README.md                   ← パッケージドキュメント
│
├── scripts/                        ← ユーティリティスクリプト
│   ├── launch_sandbox.py           ← Sandbox起動・管理CLI
│   ├── launch-sandbox.sh           ← シェルラッパースクリプト
│   ├── example_usage.py            ← SandboxManager使用例
│   └── README.md                   ← スクリプトドキュメント
│
├── data/                           ← データストレージ
│   ├── scenarios/                  ← シナリオファイル（JSON/YAML）
│   ├── rerun/                      ← RRDファイル（rerun.io）
│   └── logs/                       ← ログファイル（🆕）
│       ├── stamp/                  ← STAMP状態遷移ログ
│       └── commands/               ← コマンド追跡ログ
│
├── pyproject.toml                  ← プロジェクト設定（uv）
├── Makefile                        ← ビルド・実行タスク
├── run.sh                          ← 本番起動スクリプト
├── run_dev.sh                      ← 開発起動スクリプト（--reload）
├── shutdown.sh                     ← システムシャットダウンスクリプト
└── README.md                       ← プロジェクトドキュメント
```

---

## スキル

**重要**: スキルは `.claude/skills/<skill-name>/SKILL.md` として配置されています。

### scenario-writer
   - UI画面を切り替える
   - パラメータ:
     - `view`: 画面名 ("home", "scenario_list", "scenario_analysis", "rerun_viewer")
   - 戻り値: 切り替え結果メッセージ
   - 例:
     ```python
     change_view(view="scenario_list")
     # → "画面を scenario_list に切り替えました。"
     ```

2. **get_current_view()**
   - 現在表示中の画面を取得
   - パラメータ: なし
   - 戻り値: 現在の画面名
   - 例:
     ```python
     get_current_view()
     # → "current_view: home"
     ```

3. **list_scenarios()**
   - 保存されているシナリオの一覧を取得
   - パラメータ: なし
   - 戻り値: シナリオリスト
   - 例:
     ```python
     list_scenarios()
     # → "シナリオリスト (3件):
     #    - scenario_001: 市街地走行テスト
     #    - scenario_002: 高速道路合流
     #    - scenario_003: 交差点右折"
     ```

4. **get_scenario(scenario_id: str)**
   - 特定のシナリオの詳細を取得
   - パラメータ:
     - `scenario_id`: シナリオID
   - 戻り値: シナリオ詳細情報
   - 例:
     ```python
     get_scenario(scenario_id="scenario_001")
     # → "シナリオ詳細: {...}"
     ```

5. **generate_abstract_scenario(prompt: str)**
   - ユーザーの自然言語要件から抽象シナリオを生成
   - パラメータ:
     - `prompt`: 自然言語要件
   - 戻り値: 抽象シナリオ（JSON）
   - 例:
     ```python
     generate_abstract_scenario(prompt="高速道路で合流するシナリオ")
     # → 抽象シナリオJSON
     ```

6. **generate_logical_scenario(abstract_scenario: dict)**
   - 抽象シナリオから論理シナリオを生成
   - パラメータ:
     - `abstract_scenario`: 抽象シナリオのJSON表現
   - 戻り値: 論理シナリオ（JSON、OpenDRIVE非依存）
   - 例:
     ```python
     generate_logical_scenario(abstract_scenario={...})
     # → 論理シナリオJSON
     ```

7. **generate_concrete_scenario(logical_scenario: dict, carla_map: str)**
   - 論理シナリオから具体シナリオとJSONパラメータを生成
   - パラメータ:
     - `logical_scenario`: 論理シナリオのJSON表現
     - `carla_map`: CARLAマップ名（デフォルト: Town04）
   - 戻り値: 具体シナリオとJSONパラメータ
   - 例:
     ```python
     generate_concrete_scenario(logical_scenario={...}, carla_map="Town04")
     # → 具体シナリオ + JSONパラメータ
     ```

8. **launch_scenario_with_retry(cpp_code: str, config_json: str, scenario_uuid: str, max_retries: int)**
   - C++コードをビルド・実行（自動リトライ機能付き）
   - パラメータ:
     - `cpp_code`: C++ソースコード
     - `config_json`: JSONパラメータ
     - `scenario_uuid`: シナリオUUID
     - `max_retries`: 最大リトライ回数（デフォルト: 5）
   - 戻り値: 実行結果（成功/失敗、エラー履歴）
   - 例:
     ```python
     launch_scenario_with_retry(cpp_code="...", config_json="...", scenario_uuid="uuid-123")
     # → {"success": True, "attempt": 2, "uuid": "uuid-123", ...}
     ```

9. **save_scenario_trace(trace: dict)**
   - シナリオのトレース情報をJSONファイルに保存
   - パラメータ:
     - `trace`: ScenarioTraceのJSON表現
   - 戻り値: 保存されたファイルのパス
   - 例:
     ```python
     save_scenario_trace(trace={...})
     # → "data/scenarios/uuid-123.json"
     ```

### スラッシュコマンド

#### /view

画面切り替えコマンド（`.claude/atlas-plugin/commands/view.md`）

```markdown
/view <view_name>
```

使用例:
```
/view home              # ホーム画面
/view scenario_list     # シナリオ一覧
/view scenario_analysis # 分析画面
/view rerun_viewer      # Rerunビューア
```

### スキル

**重要**: スキルは `.claude/skills/<skill-name>/SKILL.md` として配置されています。

#### scenario-writer

シナリオライタースキル（`.claude/skills/scenario-writer/SKILL.md`）

**トリガーワード**: "シナリオ生成", "scenario generation", "create scenario", "シナリオ作成", "新しいシナリオ"

自然言語要件からCARLAシナリオを自動生成する包括的なエージェント。

**主要機能**:
1. **PEGASUS 6 Layer分析**: 要件をPEGASUSフレームワークで構造化
2. **抽象シナリオ生成**: 自然言語から構造化されたシナリオ記述を作成
3. **論理シナリオ生成**: パラメータ空間を定義
4. **Python実装**: CARLA Python APIを使ったシナリオスクリプトを生成
5. **自動実行・デバッグ**: エラー検出と自動修正（最大5回リトライ）
6. **トレース記録**: 抽象→論理→実装の階層関係をJSONに保存
7. **可視化**: imageioで動画（.mp4）を記録

**ワークフロー**:
```
Phase 0: PEGASUS 6 Layer分析
  ↓
Phase 1: 抽象シナリオ生成
  ↓
Phase 2: 論理シナリオ生成（パラメータ空間定義）
  ↓
Phase 3: Python実装生成
  ↓
Phase 4: 実行・デバッグループ（最大5回）
  ↓
Phase 5: トレース保存
```

**制約事項**:
- すべての車両はCARLA Traffic Managerで制御
- opendrive_utilsライブラリで精密なスポーン位置を計算
- スペクターカメラで動画記録（imageio使用）
- ファイル名: `{logical_uuid}_{parameter_uuid}.mp4`

#### scenario-manager

シナリオ管理スキル（`.claude/skills/scenario-manager/SKILL.md`）

**トリガーワード**: "list scenarios", "シナリオ一覧", "シナリオ管理"

シナリオのCRUD操作（作成、読み取り、更新、削除）をサポート。

**主要機能**:
- シナリオ一覧の表示
- シナリオの作成・編集・削除
- scripts/scenario_manager.pyとの連携

#### pegasus-analyzer

PEGASUS分析スキル（`.claude/skills/pegasus-analyzer/SKILL.md`）

**トリガーワード**: "pegasus", "シナリオ分析", "6 layer", "要件整理"

ユーザーの自然言語要件をPEGASUS 6 Layerの観点から分析。

**PEGASUS 6 Layer**:
1. **Layer 1**: Road-level（道路タイプ、トポロジー）
2. **Layer 2**: Traffic Infrastructure（信号機、標識）
3. **Layer 3**: Temporary Manipulation（工事、事故）
4. **Layer 4**: Moving Objects（車両、歩行者、マニューバー）
5. **Layer 5**: Environment（天候、時間帯、路面状態）
6. **Layer 6**: Digital Information（V2X、センサー）

#### carla-launcher

CARLA起動管理スキル（`.claude/skills/carla-launcher/SKILL.md`）

**トリガーワード**: "start CARLA", "carla起動", "launch CARLA server"

CARLAシミュレーターの起動・停止・管理を自動化。

**主要機能**:
- CARLAサーバーの起動（`CarlaUnreal.sh`実行）
- 設定管理（ポート、マップ、品質レベル）
- 状態確認とプロセス管理

**使用例**:
```bash
# デフォルト設定で起動
uv run python scripts/carla_launcher.py launch

# カスタム設定で起動
uv run python scripts/carla_launcher.py launch --port 2001 --map Town04
```

#### carla-python-scenario

CARLA Python APIスキル（`.claude/skills/carla-python-scenario/SKILL.md`）

**トリガーワード**: "carla python", "python実装", "CARLA Python API"

CARLA Python APIを使ったシナリオ開発をサポート。

**主要機能**:
- 車両・センサーのスポーン
- Traffic Managerによる車両制御
- 同期モード設定
- imageioによる動画記録

#### cleanup

クリーンアップスキル（`.claude/skills/cleanup/SKILL.md`）

**トリガーワード**: "cleanup", "削除", "クリーンアップ", "シナリオ削除"

シナリオ関連ファイルを一括削除。

**削除対象**:
- シナリオJSON（抽象/論理/パラメータ/実行トレース）
- Pythonスクリプト（`scenarios/*.py`）
- 動画ファイル（`data/videos/*.mp4`）
- RRDファイル（`data/rerun/*.rrd`）
- Embeddingファイル
- FiftyOneデータセット
- Sandboxワークスペース（オプション）

**使用例**:
```bash
# ドライラン（確認のみ）
uv run python scripts/cleanup_all.py

# 実際に削除
uv run python scripts/cleanup_all.py --force
```

#### scenario-breakdown

シナリオブレークダウンスキル（`.claude/skills/scenario-breakdown/SKILL.md`）

**トリガーワード**: "scenario breakdown", "シナリオマトリクス", "複数シナリオ生成"

PEGASUS 6 Layerのパラメータを組み合わせて、1つの要件から複数のシナリオバリエーションを生成。

**主要機能**:
- PEGASUS Layer 4, 5のパラメータをマトリクス展開
- 組み合わせ爆発を避けた効率的なサンプリング
- 各バリエーションごとに抽象・論理シナリオを生成

#### rerun-carla-sdk

Rerun可視化スキル（`.claude/skills/rerun-carla-sdk/SKILL.md`）

**トリガーワード**: "rerun carla", "rerun sdk", "可視化", ".rrd"

rerun_carla_sdkを使ったCARLAシミュレーションの可視化とログ記録。

**主要機能**:
- 車両・歩行者のバウンディングボックス可視化
- 道路境界の可視化
- カメラ視錐台表示
- .rrdファイル記録（ライブビューア、ヘッドレスモード）

#### fiftyone-integration

FiftyOne統合スキル（`.claude/skills/fiftyone-integration/SKILL.md`）

**トリガーワード**: "FiftyOne", "embedding計算", "FiftyOneに登録"

FiftyOneデータセットへのシナリオ動画登録とembedding計算。

**主要機能**:
- シナリオ動画のFiftyOneデータセット登録
- CLIPモデルによるembedding計算
- 類似シナリオの検索

#### test-simple

テストスキル（`.claude/skills/test-simple/SKILL.md`）

**トリガーワード**: "test-simple", "テストスキル"

スキル読み込み機構のデバッグ用シンプルなテストスキル。

---

## スクリプトとツール

### シナリオ管理 (scenario_manager.py)

**概要**: シナリオの階層構造（抽象→論理→パラメータ→実行）を管理するツール

**階層構造**:
```
抽象シナリオ (Abstract)
  - どんな場所でどんな物体が登場するか
  ↓ 1:N
論理シナリオ (Logical)
  - パラメータの定義と分布
  ↓ 1:N
パラメータ (Parameters)
  - サンプリングされた具体値
  ↓ 1:1
実行 (Execution)
  - 実行結果
```

**使用例**:

```python
from scripts.scenario_manager import ScenarioManager

manager = ScenarioManager()

# 1. 抽象シナリオを作成
abstract_uuid = manager.create_abstract_scenario(
    name="交差点信号機シナリオ",
    description="市街地の交差点で信号機に従って停止・発進する",
    original_prompt="信号機が赤から青に変わったら車両が発進するシナリオ",
    environment={
        "location_type": "urban_intersection",
        "features": ["traffic_light", "road", "buildings"]
    },
    actors=[
        {
            "id": "ego_vehicle",
            "type": "vehicle",
            "role": "自動運転車両"
        },
        {
            "id": "traffic_light",
            "type": "traffic_signal",
            "role": "交差点の信号機"
        }
    ],
    scenario_type="traffic_light_compliance"
)

# 2. 論理シナリオを作成（パラメータ空間を定義）
logical_uuid = manager.create_logical_scenario(
    parent_abstract_uuid=abstract_uuid,
    name="交差点信号機シナリオ",
    description="パラメータ空間の定義",
    parameter_space={
        "ego_vehicle": {
            "initial_speed": {
                "type": "float",
                "unit": "km/h",
                "distribution": "uniform",
                "min": 20.0,
                "max": 40.0
            },
            "distance_to_light": {
                "type": "float",
                "unit": "m",
                "distribution": "uniform",
                "min": 30.0,
                "max": 70.0
            }
        },
        "traffic_light": {
            "red_duration": {
                "type": "float",
                "unit": "s",
                "distribution": "uniform",
                "min": 3.0,
                "max": 7.0
            }
        },
        "camera": {
            "offset_x": {
                "type": "float",
                "unit": "m",
                "distribution": "constant",
                "value": -6.0
            },
            "offset_z": {
                "type": "float",
                "unit": "m",
                "distribution": "constant",
                "value": 3.0
            },
            "pitch": {
                "type": "float",
                "unit": "deg",
                "distribution": "constant",
                "value": -20.0
            }
        }
    }
)

# 3. パラメータをサンプリング（複数回可能）
param_uuid_1 = manager.sample_parameters(
    logical_uuid=logical_uuid,
    carla_config={
        "host": "localhost",
        "port": 2000,
        "map": "Town10HD_Opt",
        "vehicle_type": "vehicle.taxi.ford"
    },
    seed=42  # 再現性のため
)

param_uuid_2 = manager.sample_parameters(
    logical_uuid=logical_uuid,
    carla_config={
        "host": "localhost",
        "port": 2000,
        "map": "Town10HD_Opt",
        "vehicle_type": "vehicle.taxi.ford"
    }
)

# 4. パラメータを取得
params = manager.get_parameters(logical_uuid, param_uuid_1)
print(f"サンプリングされた速度: {params['sampled_values']['ego_vehicle']['initial_speed']} km/h")

# 5. 全パラメータをリスト
all_params = manager.list_parameters(logical_uuid)
print(f"パラメータセット数: {len(all_params)}")

# 6. 実行トレースを記録
manager.create_execution_trace(
    logical_uuid=logical_uuid,
    parameter_uuid=param_uuid_1,
    python_file=f"scenarios/{logical_uuid}.py",
    command=f"uv run python scenarios/{logical_uuid}.py --params ...",
    exit_code=0,
    status="success"
)
```

**CLIコマンド**:

```bash
# 抽象シナリオ一覧
uv run python scripts/scenario_manager.py list-abstract

# 論理シナリオ一覧
uv run python scripts/scenario_manager.py list-logical

# 特定の抽象シナリオの論理シナリオ一覧
uv run python scripts/scenario_manager.py list-logical <abstract_uuid>

# パラメータ一覧
uv run python scripts/scenario_manager.py list-params <logical_uuid>
```

**ファイル構造**:
```
data/scenarios/
├── abstract_{uuid}.json                      # 抽象シナリオ
├── logical_{uuid}.json                       # 論理シナリオ
├── logical_{uuid}_parameters.json            # パラメータ集合（複数セット）
└── execution_{logical_uuid}_{params_uuid}.json  # 実行トレース
```

**サポートする分布**:
- `constant`: 固定値
- `uniform`: 一様分布（min, max）
- `normal`: 正規分布（mean, std）
- `choice`: 選択肢からランダム選択（choices）

---

### シナリオクリーンアップ (cleanup_scenarios.py)

**概要**: シナリオとログデータを安全に削除するツール

**使用例**:

```bash
# 1. すべてのシナリオを確認（ドライラン）
uv run python scripts/cleanup_scenarios.py --all

# 2. すべてのシナリオを削除（実際に削除）
uv run python scripts/cleanup_scenarios.py --all --force

# 3. 特定の抽象シナリオとその子孫を削除
uv run python scripts/cleanup_scenarios.py --abstract-uuid <uuid>

# 4. 特定の論理シナリオとその関連ファイルを削除
uv run python scripts/cleanup_scenarios.py --logical-uuid <uuid>

# 5. 30日より古いシナリオを削除
uv run python scripts/cleanup_scenarios.py --older-than-days 30

# 6. 強制削除（--forceオプション）
uv run python scripts/cleanup_scenarios.py --logical-uuid <uuid> --force
```

**削除対象**:
- 抽象シナリオJSON
- 論理シナリオJSON
- パラメータJSON
- 実行トレースJSON
- Pythonスクリプト (`scenarios/*.py`)
- 動画ファイル (`data/videos/*.mp4`)
- RRDファイル (`data/rerun/*.rrd`)

**安全機能**:
- デフォルトはドライラン（`--force`なしでは削除しない）
- 削除前にファイルリストとサイズを表示
- 関連ファイルを自動検出（トレーサビリティ考慮）

**出力例**:
```
=== 削除対象ファイル ===

【logical】
  - data/scenarios/logical_abc123.json (2.5KB)
  小計: 2.5KB

【parameters】
  - data/scenarios/logical_abc123_parameters.json (5.2KB)
  小計: 5.2KB

【videos】
  - data/videos/abc123_def456.mp4 (50.0MB)
  小計: 50.0MB

=== 合計: 3ファイル, 50.0MB ===

ℹ️  ドライランモード: ファイルは削除されません
   実際に削除するには --force オプションを使用してください
```

---

### その他のツール

#### list_vehicles.py
**概要**: CARLAで利用可能な車両の一覧を表示

```bash
uv run python scripts/list_vehicles.py
```

#### analyze_scenarios.py
**概要**: シナリオのトレーサビリティを分析（要更新：新形式対応予定）

```bash
# 全体のサマリー
uv run python scripts/analyze_scenarios.py

# 特定のシナリオの系譜
uv run python scripts/analyze_scenarios.py <logical_uuid>
```

---

## agent_controllerパッケージ

### 概要

**agent_controller**は、CARLA Traffic Managerをラップした高レベルAPIパッケージです。テストケースでよくあるシナリオ（レーンチェンジ、カットイン、タイミング突入など）を簡単に記述でき、STAMP状態遷移ロガーとユーザー指示追跡機能を統合しています。

### 主要機能

1. **高レベルAPI**
   - レーンチェンジ: 左右へのレーンチェンジ
   - カットイン: 前方車両への割り込み
   - タイミング突入: 特定地点への時間指定到達
   - 追従走行: 前方車両を一定距離で追従
   - 停止: 車両の停止

2. **STAMPロギング**
   - STAMP理論に基づいた状態遷移の記録
   - 制御アクション（accelerate, brake, lane_changeなど）の記録
   - 車両の位置・速度・状態の記録
   - JSONファイルで保存（`data/logs/stamp/`）

3. **ユーザー指示追跡**
   - ユーザーからの指示（コマンド）を記録
   - 指示の完遂状態を追跡（pending → in_progress → completed/failed）
   - 実行メトリクス（実行時間、移動距離など）の記録
   - JSONファイルで保存（`data/logs/commands/`）

4. **安全性メトリクス** 🆕
   - TTC (Time To Collision): 前方車両への衝突時間
   - 急ブレーキ検出: 減速度が閾値を超えた場合
   - 急加速検出: 加速度が閾値を超えた場合
   - 横方向加速度: レーンチェンジ時の横加速度
   - ジャーク: 加速度の変化率
   - 最小車間距離: 前方車両との最小距離
   - 意味論的カバレッジ: イベント発生有無に基づくカバレッジ
   - JSONファイルで保存（`data/logs/metrics/`）

5. **将来のカバレッジ計測**
   - NPCロジックを統一し、実行パスを記録
   - 将来的にカバレッジ計測の基盤を提供

### 基本的な使い方（推奨: トリガー関数ベース）🆕

トリガー関数を使うと、world.tick()やフレーム管理が不要になり、シナリオを宣言的に記述できます。

```python
from agent_controller import AgentController
from opendrive_utils import OpenDriveMap, SpawnHelper, LaneCoord

with AgentController(scenario_uuid="my_scenario") as controller:
    # 車両設定を定義
    ego_config = VehicleConfig(
        auto_lane_change=False,
        distance_to_leading=5.0,
        speed_percentage=80.0,
    )

    # 車両をスポーン（自動登録）
    lane_coord_1 = LaneCoord(road_id=10, lane_id=-1, s=50.0)
    ego_vehicle, ego_id = controller.spawn_vehicle_from_lane(
        "vehicle.tesla.model3",
        lane_coord_1,
        config=ego_config,
    )

    # プリセットを使ってNPC車両をスポーン
    lane_coord_2 = LaneCoord(road_id=10, lane_id=-1, s=80.0)
    npc_vehicle, npc_id = controller.spawn_vehicle_from_lane(
        "vehicle.tesla.model3",
        lane_coord_2,
        config=CAUTIOUS_DRIVER,  # 慎重なドライバー
    )

    # トリガー関数でシナリオを定義（フレーム管理不要！）
    controller.register_callback(
        controller.when_timestep_equals(100),
        lambda: controller.lane_change(ego_id, direction="left")
    )

    controller.register_callback(
        controller.when_timestep_equals(200),
        lambda: controller.cut_in(ego_id, target_vehicle_id=npc_id)
    )

    controller.register_callback(
        controller.when_timestep_equals(350),
        lambda: controller.follow(ego_id, target_vehicle_id=npc_id)
    )

    controller.register_callback(
        controller.when_timestep_equals(550),
        lambda: controller.stop(ego_id)
    )

    # 高度なトリガー: 車両間距離が10m以下になったら警告（リピート）
    controller.register_callback(
        controller.when_distance_between(ego_id, npc_id, 10.0, operator="less"),
        lambda: print("⚠ Too close!"),
        one_shot=False
    )

    # シミュレーション実行（world.tick()は自動呼び出し）
    controller.run_simulation(total_frames=600)

    # 車両は自動的に破棄される（明示的な破棄は不要）

# コンテキストマネージャを抜けると自動的に:
# - スポーンした車両が破棄される
# - ログがファイナライズ・保存される
# - サマリーが出力される
# - 同期モードが元に戻される
# - クリーンアップが実行される
```

**重要**: `spawn_vehicle()`や`spawn_vehicle_from_lane()`でスポーンした車両は、`auto_destroy=True`（デフォルト）の場合、コンテキストマネージャを抜けると自動的に破棄されます。明示的な`destroy_vehicle()`呼び出しは不要です。

### 利用可能なトリガー関数

- `when_timestep_equals(frame)` - 特定フレームに到達
- `when_timestep_greater_than(frame)` - フレームが指定値を超える
- `when_vehicle_at_location(vehicle_id, location, threshold)` - 車両が位置に到達
- `when_distance_between(vehicle_id1, vehicle_id2, distance, operator)` - 車両間距離が条件を満たす
- `when_speed_greater_than(vehicle_id, speed)` - 速度が閾値を超える
- `when_speed_less_than(vehicle_id, speed)` - 速度が閾値を下回る
```

### on_tickコールバックパターン

毎フレーム実行されるコールバックを使う方法：

```python
with AgentController(scenario_uuid="my_scenario") as controller:
    # 車両をスポーン・登録
    ego_id = controller.register_vehicle(vehicle)
    npc_id = controller.register_vehicle(npc_vehicle)

    # 毎フレーム呼ばれるコールバック
    def on_tick(frame: int):
        if frame == 100:
            controller.lane_change(ego_id, direction="left")
        elif frame == 200:
            controller.cut_in(ego_id, target_vehicle_id=npc_id)
        elif frame == 350:
            controller.follow(ego_id, target_vehicle_id=npc_id)
        elif frame == 550:
            controller.stop(ego_id)

    # シミュレーション実行
    controller.run_simulation(total_frames=600, on_tick=on_tick)
```

### 接続管理機能（🆕）

AgentControllerは、CARLAサーバーへの接続を自動的に管理します。

```python
with AgentController(
    scenario_uuid="my_scenario",
    max_retries=3,       # 接続失敗時の最大リトライ回数
    retry_delay=2.0,     # リトライ間の待機時間（秒）
) as controller:
    # 接続確認
    if controller.is_alive():
        print("✓ Server is alive")

    # 接続が切れた場合の再接続
    if not controller.check_connection():
        print("Connection lost. Reconnecting...")
        if controller.reconnect():
            print("✓ Reconnected successfully")
```

### 安全性メトリクス機能（🆕）

TTC、急ブレーキ、急加速などの自動運転評価指標を自動計算します。

```python
from agent_controller import AgentController, MetricsConfig

# メトリクス設定をカスタマイズ
metrics_config = MetricsConfig(
    ttc_threshold=3.0,                    # TTC閾値: 3秒以下で警告
    sudden_braking_threshold=5.0,         # 急ブレーキ: 5 m/s²以上で検出
    sudden_acceleration_threshold=4.0,    # 急加速: 4 m/s²以上で検出
    lateral_acceleration_threshold=3.0,   # 横方向加速度: 3 m/s²以上で検出
    jerk_threshold=10.0,                  # ジャーク: 10 m/s³以上で検出
    min_distance_threshold=2.0,           # 最小車間距離: 2m以下で警告
)

# メトリクス計算を有効化
with AgentController(
    scenario_uuid="my_scenario",
    enable_metrics=True,           # メトリクス有効化
    metrics_config=metrics_config, # カスタム設定
) as controller:
    # シナリオ実行...
    controller.run_simulation(total_frames=600)

# コンテキストマネージャを抜けると自動的に:
# - メトリクスログが data/logs/metrics/ に保存される
# - STAMPログが data/logs/stamp/ に保存される
# - コマンドログが data/logs/commands/ に保存される
```

#### 計算されるメトリクス

- **TTC**: 前方車両への衝突時間（秒）
- **急ブレーキ**: 減速度が閾値を超えた場合（m/s²）
- **急加速**: 加速度が閾値を超えた場合（m/s²）
- **横方向加速度**: レーンチェンジ時の横加速度（m/s²）
- **ジャーク**: 加速度の変化率（m/s³）
- **最小車間距離**: 前方車両との最小距離（m）

### 低レベルAPI（上級者向け）

より細かい制御が必要な場合は、低レベルAPIを直接使用できます。

```python
import carla
from agent_controller import (
    TrafficManagerWrapper,
    STAMPLogger,
    CommandTracker,
    LaneChangeBehavior,
)

# 手動でCARLA接続
client = carla.Client('localhost', 2000)
client.set_timeout(10.0)
world = client.get_world()

# ロガー初期化
stamp_logger = STAMPLogger(scenario_uuid="my_scenario")
command_tracker = CommandTracker(scenario_uuid="my_scenario")

# Traffic Manager Wrapper初期化
tm_wrapper = TrafficManagerWrapper(
    client=client,
    port=8000,
    stamp_logger=stamp_logger,
    command_tracker=command_tracker,
)

# 車両登録と振る舞い実行
# ...

# 手動でクリーンアップ
stamp_logger.finalize()
command_tracker.finalize()
tm_wrapper.cleanup()
```

### 利用可能なBehavior

| Behavior | 説明 | 主要パラメータ |
|----------|------|---------------|
| `LaneChangeBehavior` | レーンチェンジ | `direction` ("left"/"right"), `duration_frames` |
| `CutInBehavior` | カットイン | `target_vehicle_id`, `gap_distance`, `speed_boost` |
| `TimedApproachBehavior` | タイミング突入 | `target_location`, `target_time`, `ignore_traffic` |
| `FollowBehavior` | 追従走行 | `target_vehicle_id`, `distance`, `duration_frames` |
| `StopBehavior` | 停止 | `duration_frames` |

### 機能追加の方法

agent_controllerに必要な機能が不足している場合：

1. **新しいBehaviorクラスを追加**
   - `agent_controller/behaviors.py`に実装
   - `Behavior`基底クラスを継承
   - `execute()`メソッドを実装

2. **Gitワークフローに従う**
   ```bash
   # ブランチ作成
   git checkout -b feature/agent-controller-new-behavior

   # 実装
   # ...

   # コミット＆プッシュ
   git add agent_controller/
   git commit -m "Add new behavior to agent_controller"
   git push origin feature/agent-controller-new-behavior

   # PR作成
   gh pr create --title "Add new behavior" --body "..."
   ```

3. **マージ後に使用**
   - PRがマージされてから、シナリオスクリプトで新機能を使用

### ログ出力

#### STAMP状態遷移ログ

```json
{
  "scenario_uuid": "uuid-123",
  "start_time": "2025-01-01T12:00:00",
  "state_transitions": [
    {
      "timestamp": 1234567890.0,
      "frame": 100,
      "vehicle_id": 42,
      "from_state": "idle",
      "to_state": "driving",
      "control_action": "accelerate",
      "location": {"x": 100.0, "y": 50.0, "z": 0.5},
      "velocity": {"x": 5.0, "y": 0.0, "z": 0.0}
    }
  ],
  "control_actions": [...]
}
```

#### コマンド追跡ログ

```json
{
  "scenario_uuid": "uuid-123",
  "commands": [
    {
      "command_id": "cmd_0001",
      "description": "Lane change to left",
      "status": "completed",
      "success": true,
      "metrics": {
        "duration_seconds": 4.0,
        "duration_frames": 80,
        "distance_traveled": 50.0
      }
    }
  ],
  "summary": {
    "total_commands": 5,
    "completed": 4,
    "success_rate": 0.8
  }
}
```

#### メトリクスログ 🆕

```json
{
  "scenario_uuid": "uuid-123",
  "config": {
    "ttc_threshold": 3.0,
    "sudden_braking_threshold": 5.0,
    "sudden_acceleration_threshold": 4.0,
    "lateral_acceleration_threshold": 3.0,
    "jerk_threshold": 10.0,
    "min_distance_threshold": 2.0,
    "speed_violation_margin": 10.0
  },
  "summary": {
    "total_events": 12,
    "event_counts": {
      "sudden_braking": 3,
      "low_ttc": 5,
      "sudden_acceleration": 2,
      "high_jerk": 2
    },
    "min_ttc_per_vehicle": {
      "42": 2.1,
      "43": 2.8
    },
    "min_distances": {
      "42": 1.5,
      "43": 2.3
    }
  },
  "events": [
    {
      "frame": 150,
      "timestamp": 1234567890.0,
      "event_type": "sudden_braking",
      "vehicle_id": 42,
      "value": 6.2,
      "threshold": 5.0,
      "description": "急ブレーキ検出: 6.20 m/s²",
      "location": [100.5, 50.2, 0.3]
    }
  ]
}
```

### 参考資料

- **詳細ドキュメント**: `agent_controller/README.md`
- **使用例（推奨・最新）**: `examples/agent_controller_callback.py` - コールバックを使った最もシンプルな例 🆕
- **使用例（シンプル）**: `examples/agent_controller_simple.py` - AgentControllerの基本的な使い方
- **使用例（詳細）**: `examples/agent_controller_example.py` - すべての機能を使った例
- **使用例（メトリクス）**: `examples/agent_controller_metrics.py` - 安全性メトリクスの使い方 🆕
- **APIリファレンス**: 各モジュールのdocstring参照

---

## 開発ワークフロー

### 1. 初期セットアップ

```bash
# 依存関係のインストール
make install

# または
uv sync
```

### 2. 開発サーバーの起動

```bash
# 開発モード（auto-reload有効）
make dev

# または
./run_dev.sh
```

アプリケーションは http://localhost:8000 で起動します。

### 3. コード変更時の動作

#### FastAPIコード変更

`app/`配下のPythonコードを変更すると、uvicornが自動的にリロードします。

**変更対象**:
- `app/routers/*.py` - ルーター
- `app/services/*.py` - サービス
- `app/models/*.py` - モデル
- `app/templates/*.html` - テンプレート

#### フロントエンド変更

- HTMLテンプレート: 自動リロード
- CSS/JS: ブラウザのキャッシュクリア後にリロード

#### Sandbox C++コード変更

```bash
# 新しいシナリオで実行
cd sandbox
vim src/main.cpp
make run  # 新しいUUIDで自動的にビルド・実行される

# 既存のシナリオで再実行
make run UUID=550e8400-e29b-41d4-a716-446655440000

# シナリオ一覧を確認
make list-scenarios
```

**重要**: 各シナリオは独立したビルド成果物と出力ディレクトリを持つため、複数のシナリオを並行して実行・管理できます。

#### PythonからSandbox起動

```bash
# CLIツールで起動
uv run python scripts/launch_sandbox.py launch

# または Makeコマンド
make sandbox-launch

# Pythonコードから
from app.services import sandbox_manager
uuid, result = sandbox_manager.launch_sandbox()
```

詳細は `scripts/README.md` を参照してください。

### 4. デバッグ

#### ログ確認

```bash
# FastAPIログ（コンソール出力）
# run_dev.shで起動した場合、ターミナルに表示される

# Sandboxログ
cd sandbox
docker-compose logs -f
```

#### ブレークポイント

```python
# app/routers/views.py など

def some_function():
    import pdb; pdb.set_trace()  # ブレークポイント
    # ...
```

### 5. テスト

```bash
# テスト実行
make test

# または
uv run pytest
```

---

## 起動・停止

### 起動

#### すべて起動

```bash
# 開発モード
make dev

# Sandbox
make sandbox
```

#### 個別起動

```bash
# Flaskアプリのみ
./run_dev.sh

# Sandboxのみ（新しいUUID）
cd sandbox && ./run.sh

# Sandboxのみ（既存のシナリオ）
cd sandbox && ./run.sh 550e8400-e29b-41d4-a716-446655440000
```

### 停止

#### すべて停止

```bash
# 基本シャットダウン
make shutdown

# または
./shutdown.sh
```

#### 個別停止

```bash
# Flaskアプリのみ
make shutdown-flask

# 特定のシナリオを停止
cd sandbox
./shutdown.sh 550e8400-e29b-41d4-a716-446655440000

# またはMakeを使用
cd sandbox
make shutdown UUID=550e8400-e29b-41d4-a716-446655440000

# すべてのシナリオを停止
cd sandbox
./shutdown.sh -a
# または
make shutdown-all
```

#### 完全クリーンアップ

```bash
# すべてのシナリオ + Dockerイメージも削除
cd sandbox
./shutdown.sh -a -v -i
# または
make shutdown-full

# 特定のシナリオのワークスペースを削除
cd sandbox
./shutdown.sh 550e8400-e29b-41d4-a716-446655440000 -v
# または
make clean-scenario UUID=550e8400-e29b-41d4-a716-446655440000
```

#### シナリオ管理

```bash
# 既存のシナリオ一覧を表示
cd sandbox
make list-scenarios

# 出力例:
# === Scenario Workspaces ===
# Found 2 scenario(s):
#
#   UUID: 550e8400-e29b-41d4-a716-446655440000
#     Build:  128M
#     Output: 45M (3 files)
#
#   UUID: 6ba7b810-9dad-11d1-80b4-00c04fd430c8
#     Build:  132M
#     Output: 52M (5 files)
```

### システム状態確認

```bash
make status
```

出力例:
```
=== ATLAS System Status ===

Flask Application (port 8000):
  ✓ Running (PID: 12345)

CARLA Server:
  ✗ Not running
```

---

## トラブルシューティング

### 1. ポート8000が使用中

```bash
# ポートを使用しているプロセスを確認
lsof -ti:8000

# プロセスを停止
./shutdown.sh --flask-only

# または手動で停止
kill $(lsof -ti:8000)
```

### 2. Sandboxコンテナが起動しない

```bash
# ログ確認
cd sandbox
docker-compose logs

# 完全クリーンアップして再ビルド
make clean
make rebuild
```

### 4. Claude Codeが.claude設定を読み込まない

**確認事項**:
1. working directoryが正しいか確認
   ```bash
   # Claude Code内で
   pwd  # /home/masaya/workspace/atlas であること
   ```

2. .claudeディレクトリが存在するか
   ```bash
   ls -la .claude/
   ```

3. ウェルカムメッセージを確認
   ```
   === Claude Code Terminal ===
   Connected successfully!
   Working directory: /home/masaya/workspace/atlas
   ✓ .claude directory detected
   ✓ atlas-plugin will be loaded
   ✓ settings.local.json will be applied
   ```

### 5. xterm.jsが読み込まれない

```bash
# 静的ファイルの確認
ls -lh app/static/js/

# ブラウザのコンソールでエラー確認
# ブラウザで F12 → Console
```

### 6. WebSocketが切断される

```bash
# ログ確認
# FastAPIのコンソール出力を確認

# ポート確認
netstat -an | grep 8000

# 再起動
make shutdown
make dev
```

---

## コーディング規約

### Python（FastAPI）

1. **スタイル**: PEP 8に準拠
   ```python
   # Good
   def get_scenario_by_id(scenario_id: str) -> Scenario:
       """シナリオをIDで取得する"""
       return scenario_manager.get(scenario_id)

   # Bad
   def getScenarioById(scenarioId):
       return scenario_manager.get(scenarioId)
   ```

2. **型ヒント**: 必須
   ```python
   from typing import List, Optional

   def list_scenarios() -> List[Scenario]:
       ...

   def get_scenario(scenario_id: str) -> Optional[Scenario]:
       ...
   ```

3. **docstring**: Google形式
   ```python
   def change_view(view: str) -> dict:
       """UI画面を切り替える

       Args:
           view: 画面名 ("home", "scenario_list", etc.)

       Returns:
           切り替え結果を含む辞書

       Raises:
           ValueError: 無効な画面名の場合
       """
   ```

### C++（Sandbox）

1. **スタイル**: Google C++ Style Guide
   ```cpp
   // Good
   class CarlaScenario {
   public:
       CarlaScenario(const std::string& host, uint16_t port);
       void run();

   private:
       std::string host_;
       uint16_t port_;
   };

   // Bad
   class carla_scenario {
       string m_host;
       int m_port;
   };
   ```

2. **コメント**: Doxygenスタイル
   ```cpp
   /**
    * @brief CARLAシナリオを実行する
    * @param host CARLAサーバーのホスト
    * @param port CARLAサーバーのポート
    */
   void runScenario(const std::string& host, uint16_t port);
   ```

### HTML/Jinja2

1. **インデント**: 2スペース
   ```html
   <div class="container">
     <h1>{{ title }}</h1>
     <p>{{ description }}</p>
   </div>
   ```

2. **htmx属性**: データ属性として記述
   ```html
   <button
       hx-get="/views/scenario_list"
       hx-target="#main-content"
       hx-swap="innerHTML">
       シナリオ一覧
   </button>
   ```

---

## 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `SCENARIO_UUID` | シナリオを識別するUUID | default |
| `CARLA_HOST` | CARLAサーバーのホスト | localhost |
| `CARLA_PORT` | CARLAサーバーのポート | 2000 |
| `OUTPUT_DIR` | 出力ディレクトリ（Sandbox） | /workspace/output |
| `RERUN_FLUSH_TIMEOUT` | Rerunのフラッシュタイムアウト | 2000 |
| `USER_ID` | Dockerコンテナ内のユーザーID | 1000 |
| `GROUP_ID` | Dockerコンテナ内のグループID | 1000 |

**重要**: `SCENARIO_UUID`は各シナリオを一意に識別するために使用されます。`run.sh`で自動生成されるか、引数として明示的に指定できます。

---

## 権限設定（settings.local.json）

`.claude/settings.local.json`には、Claude Codeが実行可能なBashコマンドの許可リストが含まれています。

```json
{
  "permissions": {
    "allow": [
      "Bash(chmod:*)",
      "Bash(tree:*)",
      "Bash(uv sync:*)",
      "Bash(uv run python:*)",
      "Bash(./run_dev.sh:*)",
      "Bash(lsof:*)",
      "Bash(pgrep:*)",
      "Bash(curl:*)",
      "Bash(make:*)",
      "Bash(./shutdown.sh:*)",
      "Bash(ls:*)"
    ]
  }
}
```

新しいコマンドを追加する場合は、このファイルを編集してください。

---

## 参考資料

### 内部ドキュメント

- `README.md` - プロジェクト概要
- `ARCHITECTURE.md` - アーキテクチャ詳細
- `sandbox/README.md` - Sandboxドキュメント

### 外部リンク

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [htmx Documentation](https://htmx.org/docs/)
- [CARLA Documentation](https://carla.readthedocs.io/)
- [Rerun SDK Documentation](https://www.rerun.io/docs)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [xterm.js Documentation](https://xtermjs.org/)
- [Conan Documentation](https://docs.conan.io/)

---

## クイックリファレンス

### よく使うコマンド

```bash
# 開発開始
make dev

# 状態確認
make status

# テスト
make test

# Sandbox起動（新しいシナリオ）
cd sandbox && make run

# Sandbox起動（既存のシナリオ）
cd sandbox && make run UUID=550e8400-e29b-41d4-a716-446655440000

# シナリオ一覧
cd sandbox && make list-scenarios

# 特定のシナリオを停止
cd sandbox && make shutdown UUID=550e8400-e29b-41d4-a716-446655440000

# すべてのシナリオを停止
cd sandbox && make shutdown-all

# 完全クリーンアップ
cd sandbox && make shutdown-full

# PythonからSandbox起動
uv run python scripts/launch_sandbox.py launch

# または Makeコマンド
make sandbox-launch
make sandbox-list
```

### スキル実行例

スキルは自然言語で呼び出せます：

```
シナリオを生成して        # scenario-writerスキルを起動
シナリオ一覧を見せて      # scenario-managerスキルを起動
CARLAを起動して          # carla-launcherスキルを起動
```

---

**このドキュメントはClaude Codeがプロジェクトを理解するための完全なガイドです。**
**質問があれば、このファイルを参照してください。**
