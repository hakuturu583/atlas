# Docker Swarm Deployment Guide

このドキュメントでは、ATLAS（CARLA + シナリオ実行 + VLA）をDocker Swarmで分散実行する方法を説明します。

## 概要

Docker Swarmを使用することで、以下のメリットがあります：

- **リソース分離**: CARLA（CPU/GPU）、VLA（GPU）、シナリオ実行（CPU）を別々のコンテナで実行
- **スケーラビリティ**: 複数ホストでの分散実行が可能
- **高可用性**: サービスの自動再起動とヘルスチェック
- **ネットワーク管理**: Overlay networkによるサービス間通信

## アーキテクチャ

```
┌──────────────────────────────────────────────────────┐
│              Docker Swarm Cluster                     │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌────────────┐    ┌──────────────┐    ┌─────────┐ │
│  │   CARLA    │    │   Scenario   │    │   VLA   │ │
│  │  Server    │◄───│  Execution   │◄───│  Model  │ │
│  │            │    │              │    │         │ │
│  │ Port: 2000 │    │  Python API  │    │ gRPC    │ │
│  │            │    │              │    │ :50051  │ │
│  └────────────┘    └──────────────┘    └─────────┘ │
│       │                    │                  │     │
│       └────────────────────┴──────────────────┘     │
│              atlas-network (overlay)                │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## 前提条件

### システム要件

- **OS**: Ubuntu 20.04+ / Debian 11+
- **Docker**: 20.10+
- **Docker Compose**: v2.0+
- **GPU**: NVIDIA GPU（Alpamayo使用時）
- **メモリ**: 16GB以上推奨
- **CPU**: 8コア以上推奨

### NVIDIA Docker対応（GPU使用時）

```bash
# NVIDIA Container Toolkitのインストール
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 動作確認
docker run --rm --gpus all nvidia/cuda:12.1.0-runtime-ubuntu22.04 nvidia-smi
```

## クイックスタート

### 1. デプロイ

```bash
# ダミーVLAモデルでデプロイ
bash scripts/deploy_swarm.sh

# Alpamayoモデルも含めてデプロイ
bash scripts/deploy_swarm.sh --with-alpamayo
```

デプロイには5-10分かかります（イメージのビルド、Swarmの初期化、サービスの起動）。

### 2. サービス状態の確認

```bash
# スタック全体の確認
docker stack services atlas

# 特定のサービスのログ確認
docker service logs -f atlas_carla
docker service logs -f atlas_scenario
docker service logs -f atlas_ad-stack-dummy
```

### 3. シナリオの実行

```bash
# シナリオコンテナ内でPythonスクリプトを実行
docker exec -it $(docker ps -qf "name=atlas_scenario") bash -c "
cd /app
python examples/agent_controller_callback.py
"

# または、ホストから直接実行
CONTAINER_ID=$(docker ps -qf "name=atlas_scenario")
docker cp scenarios/my_scenario.py ${CONTAINER_ID}:/app/scenarios/
docker exec -it ${CONTAINER_ID} python /app/scenarios/my_scenario.py
```

### 4. クリーンアップ

```bash
# スタックのみ削除（ボリュームとイメージは保持）
bash scripts/teardown_swarm.sh

# ボリュームも削除（データが消えます）
bash scripts/teardown_swarm.sh --remove-volumes

# 完全クリーンアップ（すべて削除）
bash scripts/teardown_swarm.sh --full-cleanup
```

## 詳細な使い方

### デプロイオプション

```bash
# オプション一覧
bash scripts/deploy_swarm.sh --help

# カスタムスタック名
bash scripts/deploy_swarm.sh --stack-name my-atlas

# カスタムレジストリポート
bash scripts/deploy_swarm.sh --registry-port 5001
```

### サービスのスケーリング

```bash
# シナリオ実行コンテナを3つに増やす
docker service scale atlas_scenario=3

# 元に戻す
docker service scale atlas_scenario=1
```

### サービスの更新

```bash
# イメージを再ビルドして更新
docker build -t atlas-scenario:latest -f docker/Dockerfile.scenario .
docker tag atlas-scenario:latest localhost:5000/atlas-scenario:latest
docker push localhost:5000/atlas-scenario:latest

# サービスを更新（ローリングアップデート）
docker service update --image localhost:5000/atlas-scenario:latest atlas_scenario
```

### ログの確認

```bash
# リアルタイムログ
docker service logs -f atlas_scenario

# 最新100行
docker service logs --tail 100 atlas_scenario

# タイムスタンプ付き
docker service logs -t atlas_scenario
```

### ヘルスチェック

```bash
# gRPCヘルスプローブでVLAサービスの状態確認
docker exec $(docker ps -qf "name=atlas_ad-stack-dummy") /bin/grpc_health_probe -addr=:50051

# CARLAサーバーのポート確認
docker exec $(docker ps -qf "name=atlas_carla") bash -c "echo > /dev/tcp/localhost/2000 && echo 'CARLA is running'"
```

## トラブルシューティング

### サービスが起動しない

```bash
# サービスの詳細情報を確認
docker service ps atlas_carla --no-trunc

# コンテナのログを確認
docker service logs atlas_carla

# サービスを再起動
docker service update --force atlas_carla
```

### GPU認識されない

```bash
# ノードのGPU状態を確認
docker run --rm --gpus all nvidia/cuda:12.1.0-runtime-ubuntu22.04 nvidia-smi

# GPUラベルを確認
docker node inspect self | grep -A 5 Labels

# GPUラベルを再設定
docker node update --label-add gpu=true $(docker node ls -q)
```

### ネットワーク接続エラー

```bash
# Overlay networkを確認
docker network ls | grep atlas

# ネットワークの詳細を確認
docker network inspect atlas_atlas-network

# コンテナ間の接続テスト
docker exec $(docker ps -qf "name=atlas_scenario") ping -c 3 carla
```

### ボリュームの容量不足

```bash
# ボリュームの使用状況を確認
docker system df -v

# 不要なボリュームを削除
docker volume prune

# 特定のボリュームをバックアップして削除
docker run --rm -v atlas_scenario-logs:/data -v $(pwd):/backup alpine tar czf /backup/scenario-logs-backup.tar.gz /data
docker volume rm atlas_scenario-logs
```

## 複数ホストでの分散実行

### マネージャーノードでSwarmを初期化

```bash
# マネージャーノードで実行
docker swarm init --advertise-addr <MANAGER-IP>

# ワーカー参加用のトークンを表示
docker swarm join-token worker
```

### ワーカーノードをクラスタに追加

```bash
# ワーカーノードで実行（マネージャーノードで表示されたコマンドをコピペ）
docker swarm join --token <TOKEN> <MANAGER-IP>:2377
```

### ノードにラベルを付与

```bash
# GPUがあるノードにラベル付与
docker node update --label-add gpu=true <NODE-ID>

# CARLAを実行するノードにラベル付与
docker node update --label-add carla=true <NODE-ID>
```

### サービスの配置制約を設定

`docker-compose.stack.yml`で配置制約を追加：

```yaml
services:
  carla:
    deploy:
      placement:
        constraints:
          - node.labels.carla==true

  ad-stack-alpamayo:
    deploy:
      placement:
        constraints:
          - node.labels.gpu==true
```

## パフォーマンスチューニング

### リソース制限の調整

`docker-compose.stack.yml`でCPU/メモリ制限を調整：

```yaml
services:
  carla:
    deploy:
      resources:
        limits:
          cpus: "8"      # CPUコア数を増やす
          memory: 16G    # メモリを増やす
```

### レプリカ数の調整

```yaml
services:
  scenario:
    deploy:
      replicas: 3      # 並列実行数を増やす
```

### ネットワークMTUの最適化

```yaml
networks:
  atlas-network:
    driver: overlay
    driver_opts:
      com.docker.network.driver.mtu: 9000  # Jumbo frames
```

## セキュリティ

### プライベートレジストリの使用

```bash
# TLS付きプライベートレジストリを起動
docker run -d \
  --name registry \
  --restart=always \
  -p 5000:5000 \
  -v $(pwd)/certs:/certs \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key \
  registry:2
```

### シークレット管理

```bash
# HuggingFace tokenをシークレットとして保存
echo "your-hf-token" | docker secret create hf_token -

# docker-compose.stack.ymlで使用
services:
  ad-stack-alpamayo:
    secrets:
      - hf_token
    environment:
      - HF_TOKEN_FILE=/run/secrets/hf_token

secrets:
  hf_token:
    external: true
```

## 参考資料

- [Docker Swarm公式ドキュメント](https://docs.docker.com/engine/swarm/)
- [Docker Stack公式ドキュメント](https://docs.docker.com/engine/reference/commandline/stack/)
- [Overlay Network](https://docs.docker.com/network/overlay/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
