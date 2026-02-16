#!/bin/bash
# VLA Dockerイメージのビルドスクリプト

set -e

cd "$(dirname "$0")/.."

echo "========================================="
echo "Building VLA Docker Images"
echo "========================================="

# 1. ベースイメージのビルド
echo ""
echo "Step 1/3: Building base image..."
docker build -t atlas-vla-base:latest -f docker/Dockerfile.base .

# 2. ダミーイメージのビルド
echo ""
echo "Step 2/3: Building dummy image..."
docker build -t atlas-vla-dummy:latest -f docker/Dockerfile.dummy .

# 3. Alpamayoイメージのビルド（オプション）
if [ "$1" == "--with-alpamayo" ]; then
    echo ""
    echo "Step 3/3: Building Alpamayo image..."
    docker build -t atlas-vla-alpamayo:latest -f docker/Dockerfile.alpamayo .
else
    echo ""
    echo "Step 3/3: Skipping Alpamayo image (use --with-alpamayo to build)"
fi

echo ""
echo "========================================="
echo "✓ Build completed"
echo "========================================="
echo ""
echo "To start the dummy VLA service:"
echo "  cd docker && docker-compose up vla-dummy"
echo ""
echo "To start the Alpamayo VLA service:"
echo "  cd docker && docker-compose --profile alpamayo up vla-alpamayo"
echo ""
