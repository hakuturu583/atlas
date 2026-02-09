---
name: rerun-carla-sdk
description: This skill should be used when the user asks to "visualize with Rerun", "create rrd file", "record CARLA logs", "use rerun_carla_sdk", or mentions "rerun可視化", ".rrd", "ログ記録". Supports CARLA simulation visualization and logging using rerun_carla_sdk.
---

# Rerun CARLA SDK

このスキルは、rerun_carla_sdkを使ったCARLAシミュレーションの可視化とログ記録をサポートします。

## 📚 必須リファレンス

**Rerun CARLA SDK Repository**: https://github.com/hakuturu583/rerun_carla_sdk

このリポジトリを**必ず参照**してからコードを書いてください。

## 🎯 rerun_carla_sdkとは

CARLAシミュレーターとRerun SDKを統合し、リアルタイムで3D可視化を行うC++ライブラリです。

### 主要機能

- **道路境界の可視化**: OpenDRIVE形式から道路境界をLineStrip3Dとして描画
- **車両の可視化**: 青色のバウンディングボックスで表示
- **歩行者の可視化**: 緑色のバウンディングボックスで表示
- **カメラ視錐台表示**: スペクテータカメラの視野と姿勢を表示
- **.rrdファイル記録**: セッションを後で再生可能な形式で保存

## 📦 インストール

### conanfile.txtに追加

```
[requires]
libcarla/0.10.0
rerun_carla_sdk/0.1.0
rerun_cpp_sdk/0.21.0
boost/1.84.0
```

### CMakeLists.txtに追加

```cmake
find_package(rerun_carla_sdk REQUIRED)
target_link_libraries(carla_scenario
    PRIVATE
    rerun_carla_sdk::rerun_carla_sdk
)
```

## 🔧 基本的な使い方

### 1. 最小限の例（ライブビューアのみ）

```cpp
#include <rerun_carla_sdk.hpp>

int main() {
    // CARLAに接続してRerunビューアを起動
    rerun_carla_sdk::CarlaRerunVisualizer visualizer(
        "localhost",  // CARLAホスト
        2000,         // CARLAポート
        "my_app"      // アプリID
    );

    visualizer.initialize();
    visualizer.run(20.0);  // 20Hzで更新

    return 0;
}
```

### 2. .rrdファイルに記録（ビューア付き）

```cpp
rerun_carla_sdk::CarlaRerunVisualizer visualizer(
    "localhost", 2000, "my_app",
    "/workspace/output/recording.rrd",  // 保存先
    true  // ビューア表示
);

visualizer.initialize();
visualizer.run(20.0);
```

### 3. ヘッドレスモード（ビューアなし）

```cpp
rerun_carla_sdk::CarlaRerunVisualizer visualizer(
    "localhost", 2000, "my_app",
    "/workspace/output/recording.rrd",  // 保存先
    false  // ビューア非表示
);

visualizer.initialize();
visualizer.run(20.0);
```

### 4. 動的設定

```cpp
rerun_carla_sdk::CarlaRerunVisualizer visualizer("localhost", 2000, "my_app");

// 記録パスを設定（initialize前に実行）
visualizer.set_recording_path("/workspace/output/my_scenario.rrd");

// ビューア表示を無効化
visualizer.set_spawn_viewer(false);

visualizer.initialize();
visualizer.run(20.0);
```

## 📋 CarlaRerunVisualizerクラス

### コンストラクタ

```cpp
CarlaRerunVisualizer(
    const std::string& host,              // CARLAホスト
    uint16_t port,                        // CARLAポート
    const std::string& app_id,            // アプリケーションID
    const std::string& recording_path = "",  // .rrdファイルパス（オプション）
    bool spawn_viewer = true              // ビューア起動フラグ
);
```

### 主要メソッド

| メソッド | 説明 |
|---------|------|
| `initialize()` | CARLAサーバーに接続しRerun記録を設定 |
| `update()` | 1フレーム分の可視化を更新 |
| `run(double hz)` | 指定レート（Hz）で連続更新ループを実行 |
| `shutdown()` | クリーンアップと終了処理 |
| `is_running()` | 実行状態を確認 |
| `stop()` | 停止フラグを設定 |

### 設定メソッド

| メソッド | 説明 |
|---------|------|
| `set_recording_path(string)` | 記録ファイルパス設定（initialize前に実行） |
| `set_spawn_viewer(bool)` | ビューア起動設定（initialize前に実行） |

## 🎨 可視化コンポーネント

### ActorVisualizer

車両・歩行者のバウンディングボックス可視化

```cpp
#include <rerun_carla_sdk_detail/actor_visualizer.h>

// 内部的にCarlaRerunVisualizerが使用
// - 車両: 青色のバウンディングボックス
// - 歩行者: 緑色のバウンディングボックス
```

### CameraVisualizer

カメラ視錐台の可視化

```cpp
#include <rerun_carla_sdk_detail/camera_visualizer.h>

// 内部的にCarlaRerunVisualizerが使用
// - スペクテータカメラの位置・姿勢を表示
// - FOV、解像度の設定が可能
```

### RoadVisualizer

道路境界の可視化

```cpp
#include <rerun_carla_sdk_detail/road_visualizer.h>

// 内部的にCarlaRerunVisualizerが使用
// - OpenDRIVE形式から道路境界を抽出
// - LineStrip3Dとして描画
```

## 🔄 型変換関数（types.h）

CARLA型とRerun型の相互変換

```cpp
#include <rerun_carla_sdk_detail/types.h>

// CARLA Rotation → Quaternion
auto quaternion = rerun_carla_sdk::rotation_to_quaternion(rotation);
// 戻り値: std::array<float, 4>（[x, y, z, w]）

// CARLA Location → Position3D
auto position = rerun_carla_sdk::location_to_position3d(location);

// CARLA Transform → Rerun Transform3D
auto transform = rerun_carla_sdk::transform_to_rerun(carla_transform);
```

## 💡 実装パターン

### パターン1: 基本的なシナリオ記録

```cpp
#include <rerun_carla_sdk.hpp>
#include <carla/client/Client.h>
#include <carla/client/World.h>
#include <carla/client/Vehicle.h>
#include <csignal>

// グローバル変数（シグナルハンドラ用）
rerun_carla_sdk::CarlaRerunVisualizer* g_visualizer = nullptr;

void signal_handler(int signal) {
    if (g_visualizer) {
        std::cout << "\nShutting down gracefully..." << std::endl;
        g_visualizer->stop();
    }
}

int main(int argc, char* argv[]) {
    try {
        // シグナルハンドラ設定
        std::signal(SIGINT, signal_handler);
        std::signal(SIGTERM, signal_handler);

        // Visualizer初期化
        rerun_carla_sdk::CarlaRerunVisualizer visualizer(
            "localhost", 2000, "carla_scenario",
            "/workspace/output/scenario.rrd",
            true  // ビューア表示
        );
        g_visualizer = &visualizer;

        visualizer.initialize();

        // CARLAクライアント接続
        carla::client::Client client("localhost", 2000);
        client.SetTimeout(std::chrono::seconds(10));
        auto world = client.GetWorld();

        // シナリオ実行（車両スポーン、制御など）
        // ...

        // 可視化ループ（20Hz）
        visualizer.run(20.0);

        visualizer.shutdown();

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
```

### パターン2: マニュアル更新ループ

```cpp
#include <rerun_carla_sdk.hpp>
#include <thread>
#include <chrono>

int main() {
    rerun_carla_sdk::CarlaRerunVisualizer visualizer(
        "localhost", 2000, "manual_loop",
        "/workspace/output/manual.rrd"
    );

    visualizer.initialize();

    // 自分でループを制御
    for (int i = 0; i < 100 && visualizer.is_running(); ++i) {
        // シナリオロジック
        // ...

        // 可視化を更新
        visualizer.update();

        // 20Hz相当の待機
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    visualizer.shutdown();
    return 0;
}
```

### パターン3: 複数シナリオのバッチ記録

```cpp
#include <rerun_carla_sdk.hpp>
#include <vector>
#include <string>

void run_scenario(const std::string& scenario_name, double duration_sec) {
    std::string output_path = "/workspace/output/" + scenario_name + ".rrd";

    // ヘッドレスモードで記録
    rerun_carla_sdk::CarlaRerunVisualizer visualizer(
        "localhost", 2000, scenario_name,
        output_path,
        false  // ビューアなし
    );

    visualizer.initialize();

    // 指定時間実行
    auto start = std::chrono::steady_clock::now();
    while (visualizer.is_running()) {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration<double>(now - start).count();

        if (elapsed > duration_sec) {
            break;
        }

        visualizer.update();
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    visualizer.shutdown();
    std::cout << "Scenario '" << scenario_name << "' saved to " << output_path << std::endl;
}

int main() {
    std::vector<std::string> scenarios = {
        "straight_driving",
        "curve_driving",
        "lane_change",
        "intersection"
    };

    for (const auto& scenario : scenarios) {
        std::cout << "Running scenario: " << scenario << std::endl;
        run_scenario(scenario, 10.0);  // 各シナリオ10秒
    }

    return 0;
}
```

## 🔍 .rrdファイルの再生

記録したファイルはRerunビューアで再生できます：

```bash
# ホストマシンで実行
rerun /path/to/recording.rrd

# または、ブラウザで開く
rerun --web /path/to/recording.rrd
```

## ⚠️ 注意事項

### 必須確認事項

1. **CARLAサーバーが起動しているか**
   ```bash
   # 別ターミナルで
   ./CarlaUE4.sh
   ```

2. **ホストネットワーク設定**
   - Sandboxは `network_mode: host` でCARLAに接続
   - `localhost:2000` で接続

3. **出力ディレクトリのパーミッション**
   - `/workspace/output/` に書き込み権限があるか確認
   - Dockerコンテナ内のユーザーIDに注意

4. **シグナルハンドラの設定**
   - Ctrl+C で正常終了するように `SIGINT`, `SIGTERM` を処理
   - `visualizer.stop()` を呼んでクリーンアップ

### ヘッドレスモードの利点

- バッチ処理に最適
- リソース消費を削減
- CI/CDパイプラインでの自動化が容易

### ビューアモードの利点

- リアルタイムでシミュレーション状態を確認
- デバッグが容易
- 視覚的なフィードバックが得られる

## 🛠️ デバッグ方法

### ログ出力

```cpp
#include <iostream>

std::cout << "Initializing visualizer..." << std::endl;
visualizer.initialize();

std::cout << "Starting run loop at 20Hz..." << std::endl;
visualizer.run(20.0);

std::cout << "Shutting down..." << std::endl;
visualizer.shutdown();
```

### エラーハンドリング

```cpp
try {
    visualizer.initialize();
    visualizer.run(20.0);
    visualizer.shutdown();
} catch (const carla::client::TimeoutException& e) {
    std::cerr << "CARLA connection timeout: " << e.what() << std::endl;
    return 1;
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << std::endl;
    return 1;
}
```

### 記録ファイルの確認

```bash
# .rrdファイルが生成されたか確認
ls -lh /workspace/output/*.rrd

# Rerunで確認
rerun /workspace/output/scenario.rrd
```

## 🔗 参考リンク

- [Rerun CARLA SDK Repository](https://github.com/hakuturu583/rerun_carla_sdk)
- [Rerun Documentation](https://www.rerun.io/docs)
- [CARLA Documentation](https://carla.readthedocs.io/)
- [CARLA C++ Reference](https://carla-ue5.readthedocs.io/en/latest/ref_cpp/)

## 📂 関連ファイル

- `sandbox/src/main.cpp` - シナリオ実装ファイル
- `sandbox/output/` - .rrdファイル出力先
- `sandbox/conanfile.txt` - 依存関係（rerun_carla_sdk含む）
- `sandbox/CMakeLists.txt` - ビルド設定

## 🚀 クイックスタート

### 1. 依存関係の確認

```bash
cd sandbox
cat conanfile.txt | grep rerun_carla_sdk
# rerun_carla_sdk/0.1.0 があることを確認
```

### 2. main.cppに実装

```cpp
#include <rerun_carla_sdk.hpp>
#include <carla/client/Client.h>

int main(int argc, char* argv[]) {
    // Visualizer初期化
    rerun_carla_sdk::CarlaRerunVisualizer visualizer(
        "localhost", 2000, "my_scenario",
        "/workspace/output/scenario.rrd"
    );
    visualizer.initialize();

    // CARLAクライアント
    carla::client::Client client("localhost", 2000);
    auto world = client.GetWorld();

    // シナリオ実行
    // ...

    // 可視化ループ
    visualizer.run(20.0);
    visualizer.shutdown();

    return 0;
}
```

### 3. ビルド・実行

```bash
cd sandbox
make run
```

### 4. 結果確認

```bash
# .rrdファイルを確認
ls -lh output/*.rrd

# Rerunで再生
rerun output/scenario.rrd
```

## ⚠️ Rerun C++ SDK v0.21.0 使用上の注意

### よくあるビルドエラーと対処法

#### 1. Quaternion初期化エラー

**エラー**:
```
error: no matching constructor for 'rerun::components::PoseRotationQuat'
error: 'Rotation3D' is not a member of 'rerun::components'
```

**原因**: Rerun SDK v0.21.0では`Rotation3D`が廃止され、`PoseRotationQuat`を使用する必要がある

**修正**:
```cpp
// ❌ 間違い（古いAPI）
.with_rotations(rerun::components::Rotation3D::from_quaternion({x, y, z, w}))

// ❌ 間違い（直接初期化不可）
rerun::components::PoseRotationQuat(x, y, z, w)

// ✅ 正しい（v0.21.0）
rerun::datatypes::Quaternion quat;
quat.xyzw[0] = x;
quat.xyzw[1] = y;
quat.xyzw[2] = z;
quat.xyzw[3] = w;
rerun::components::PoseRotationQuat rotation(quat);

// Boxes3Dでの使用例
rec.log("entity",
    rerun::Boxes3D::from_half_sizes({{hx, hy, hz}})
        .with_centers({position})
        .with_quaternions({rotation})  // with_rotations ではなく with_quaternions
);
```

#### 2. rvalueアドレス取得エラー（Rerun関連）

**エラー**:
```
error: taking address of rvalue [-fpermissive]
rerun::Collection<rerun::components::Position3D>::borrow(&location_to_position3d(...), 1)
```

**原因**: 関数の戻り値（rvalue）のアドレスは取得できない

**修正**:
```cpp
// ❌ 間違い
rec.log("entity", rerun::Points3D(
    rerun::Collection<rerun::components::Position3D>::borrow(
        &location_to_position3d(location), 1
    )
));

// ✅ 正しい（一時変数に格納）
auto pos = location_to_position3d(location);
rec.log("entity", rerun::Points3D(
    rerun::Collection<rerun::components::Position3D>::borrow(&pos, 1)
));
```

#### 3. Points3D初期化エラー

**エラー**:
```
error: no matching function for call to 'rerun::Points3D::Points3D(<brace-enclosed initializer list>)'
```

**原因**: Points3Dの初期化方法がv0.21.0で変更

**修正**:
```cpp
// ❌ 間違い（古いAPI）
rec.log("entity", rerun::Points3D({{x, y, z}}));

// ✅ 正しい（v0.21.0 - Collection経由）
auto pos = rerun::components::Position3D(x, y, z);
rec.log("entity", rerun::Points3D(
    rerun::Collection<rerun::components::Position3D>::borrow(&pos, 1)
).with_colors({rerun::Rgba32(255, 0, 0, 255)}));
```

### v0.21.0のベストプラクティス

#### 位置のログ記録

```cpp
// Position3Dを作成
rerun::components::Position3D vehicle_pos(
    transform.location.x,
    transform.location.y,
    transform.location.z
);

// Points3Dでログ
rec.log("world/vehicle/position",
    rerun::Points3D(
        rerun::Collection<rerun::components::Position3D>::borrow(&vehicle_pos, 1)
    )
    .with_colors({rerun::Rgba32(0, 255, 0, 255)})
    .with_radii({0.5f})
);
```

#### バウンディングボックスのログ記録

```cpp
// Quaternionを作成
rerun::datatypes::Quaternion quat;
quat.xyzw[0] = x;
quat.xyzw[1] = y;
quat.xyzw[2] = z;
quat.xyzw[3] = w;
rerun::components::PoseRotationQuat rotation(quat);

// Position3Dを作成
rerun::components::Position3D center(cx, cy, cz);

// Boxes3Dでログ
rec.log("world/vehicle/bbox",
    rerun::Boxes3D::from_half_sizes({{half_x, half_y, half_z}})
        .with_centers({center})
        .with_quaternions({rotation})
        .with_colors({rerun::Rgba32(0, 120, 255, 255)})
);
```

#### 時刻設定

```cpp
// タイムスタンプを設定
rec.set_time_sequence("step", current_step);
rec.set_time_seconds("sim_time", current_time);

// その後にログ記録
rec.log("entity", ...);
```

### 型変換ヘルパー関数の実装例

```cpp
// CARLA Location → Rerun Position3D
rerun::components::Position3D location_to_position3d(const carla::geom::Location& loc) {
    return rerun::components::Position3D(
        static_cast<float>(loc.x),
        static_cast<float>(loc.y),
        static_cast<float>(loc.z)
    );
}

// CARLA Rotation → Rerun PoseRotationQuat
rerun::components::PoseRotationQuat rotation_to_quaternion(const carla::geom::Rotation& rot) {
    // Euler角度からQuaternionに変換
    float pitch = rot.pitch * M_PI / 180.0f;
    float yaw = rot.yaw * M_PI / 180.0f;
    float roll = rot.roll * M_PI / 180.0f;

    float cy = std::cos(yaw * 0.5f);
    float sy = std::sin(yaw * 0.5f);
    float cp = std::cos(pitch * 0.5f);
    float sp = std::sin(pitch * 0.5f);
    float cr = std::cos(roll * 0.5f);
    float sr = std::sin(roll * 0.5f);

    float w = cr * cp * cy + sr * sp * sy;
    float x = sr * cp * cy - cr * sp * sy;
    float y = cr * sp * cy + sr * cp * sy;
    float z = cr * cp * sy - sr * sp * cy;

    rerun::datatypes::Quaternion quat;
    quat.xyzw[0] = x;
    quat.xyzw[1] = y;
    quat.xyzw[2] = z;
    quat.xyzw[3] = w;

    return rerun::components::PoseRotationQuat(quat);
}
```

---

**このスキルを使用する際は、必ずRerun CARLA SDKのリポジトリを参照してから実装してください。**
