# VLA Docker Setup

VLAモデルをDockerコンテナで実行するための設定

## ディレクトリ構造

```
docker/
├── Dockerfile.base        # 共通ベースイメージ（自動生成）
├── Dockerfile.dummy       # ダミーVLAモデル用（自動生成）
├── Dockerfile.alpamayo    # Alpamayo-R1-10B用（自動生成）
├── docker-compose.yml     # Docker Compose設定
├── build.sh               # ビルドスクリプト
└── README.md              # このファイル

configs/vla/
├── base.yaml              # 共通Docker設定
├── dummy.yaml             # ダミーモデル設定
└── alpamayo.yaml          # Alpamayoモデル設定

templates/
└── Dockerfile.jinja2      # Dockerfileテンプレート
```

**注意**: Dockerfile.* は `scripts/generate_dockerfiles.py` により自動生成されます。
手動で編集せず、`configs/vla/*.yaml` を編集してください。

## クイックスタート

### 1. イメージのビルド

```bash
# ダミーモデルのみ
./docker/build.sh

# Alpamayoモデルも含める
./docker/build.sh --with-alpamayo
```

### 2. ダミーVLAサービスの起動

```bash
cd docker
docker-compose up vla-dummy
```

### 3. Alpamayo VLAサービスの起動

```bash
cd docker
docker-compose --profile alpamayo up vla-alpamayo
```

## 使用方法

### ヘルスチェック

```bash
# gRPCヘルスプローブ
docker exec atlas-vla-dummy /bin/grpc_health_probe -addr=:50051

# または curl（gRPC Webが有効な場合）
# curl localhost:50051
```

### Python クライアントでテスト

```python
import grpc
from generated.grpc_pb2 import ad_stack_pb2, ad_stack_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
stub = ad_stack_pb2_grpc.VLAServiceStub(channel)

# ヘルスチェック
health_request = ad_stack_pb2.HealthCheckRequest(service_name="VLAService")
health_response = stub.HealthCheck(health_request)

print(f"Status: {health_response.status}")
print(f"Model: {health_response.model_name}")
print(f"Initialization: {health_response.initialization_progress:.1%}")
print(f"Stage: {health_response.initialization_stage}")
```

## 環境変数

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `VLA_MODEL` | モデルタイプ ("dummy", "alpamayo") | "dummy" |
| `VLA_PORT` | gRPCポート | 50051 |
| `VLA_MAX_WORKERS` | 最大ワーカー数 | 10 |
| `HF_HOME` | HuggingFaceキャッシュディレクトリ | "/app/.cache/huggingface" |

## トラブルシューティング

### ビルドエラー

```bash
# キャッシュをクリアして再ビルド
docker build --no-cache -t atlas-vla-base:latest -f docker/Dockerfile.base .
```

### コンテナが起動しない

```bash
# ログ確認
docker logs atlas-vla-dummy

# インタラクティブモードで起動
docker run -it --rm -p 50051:50051 atlas-vla-dummy:latest bash
```

### GPU認識されない（Alpamayo）

```bash
# nvidia-dockerランタイム確認
docker run --rm --gpus all nvidia/cuda:12.1.0-runtime-ubuntu22.04 nvidia-smi
```

## カスタマイズ

### 独自VLAモデルの追加

テンプレートシステムを使用して新しいVLAモデルを追加できます。

**Step 1**: モデル実装を作成

```python
# ad_stack/models/my_model.py
from .base import VLAModelBase

class MyVLAModel(VLAModelBase):
    def __init__(self):
        super().__init__(model_name="MyVLA", version="1.0.0")

    def initialize(self) -> bool:
        # 初期化処理
        self.initialization_status.is_ready = True
        return True

    def predict(self, sensor_bundle):
        # 推論処理
        return vla_output
```

**Step 2**: Hydra設定ファイルを作成

```yaml
# configs/vla/my_model.yaml
defaults:
  - base
  - _self_

name: my_model

# カスタムベースイメージ（必要な場合）
# base_image: python:3.10-slim

# 追加の依存関係
dependencies:
  custom:
    - my-package>=1.0.0

# ファイルコピー
copy_paths:
  - src: ad_stack/models/my_model.py
    dst: /app/ad_stack/models/my_model.py

# 環境変数
environment:
  VLA_MODEL: my_model
```

**Step 3**: Dockerfileを生成

```bash
uv run python scripts/generate_dockerfiles.py
```

**Step 4**: docker-compose.ymlにサービス追加

```yaml
services:
  vla-mymodel:
    build:
      context: ..
      dockerfile: docker/Dockerfile.my_model
    image: atlas-vla-mymodel:latest
    container_name: atlas-vla-mymodel
    ports:
      - "50053:50051"
    environment:
      - VLA_MODEL=my_model
    networks:
      - atlas-network
```

**Step 5**: ビルド・実行

```bash
docker build -t atlas-vla-mymodel:latest -f docker/Dockerfile.my_model .
docker-compose up vla-mymodel
```
