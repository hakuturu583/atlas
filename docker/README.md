# VLA Docker Setup

VLAモデルをDockerコンテナで実行するための設定

## ディレクトリ構造

```
docker/
├── Dockerfile.base        # 共通ベースイメージ
├── Dockerfile.dummy       # ダミーVLAモデル用
├── Dockerfile.alpamayo    # Alpamayo-R1-10B用
├── docker-compose.yml     # Docker Compose設定
├── requirements-base.txt  # 共通依存関係
├── requirements-alpamayo.txt  # Alpamayo依存関係
├── build.sh               # ビルドスクリプト
└── README.md              # このファイル
```

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

1. `ad_stack/models/my_model.py`を作成
2. `VLAModelBase`を継承
3. `initialize()`, `predict()`を実装
4. `Dockerfile.mymodel`を作成
5. `docker-compose.yml`にサービス追加

例:
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
