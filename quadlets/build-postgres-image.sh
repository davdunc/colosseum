#!/bin/bash
# Build custom PostgreSQL image with TimescaleDB and pgvector
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="${IMAGE_NAME:-localhost/colosseum-postgres:latest}"

echo "🏛️  Building Colosseum PostgreSQL Image"
echo "========================================"
echo "Image: $IMAGE_NAME"
echo ""

cd "$SCRIPT_DIR"

# Build with podman or docker
if command -v podman &> /dev/null; then
    BUILD_CMD="podman"
    echo "🔧 Using: Podman"
elif command -v docker &> /dev/null; then
    BUILD_CMD="docker"
    echo "🔧 Using: Docker"
else
    echo "❌ Neither podman nor docker found!"
    exit 1
fi

echo ""
echo "📦 Building image (this may take 5-10 minutes)..."
$BUILD_CMD build \
    --tag "$IMAGE_NAME" \
    -f Dockerfile.postgres \
    .

echo ""
echo "✅ Build complete!"
echo ""
echo "📝 Image details:"
$BUILD_CMD images "$IMAGE_NAME"
echo ""
echo "🔍 Verify extensions:"
echo "   $BUILD_CMD run --rm $IMAGE_NAME psql --version"
echo ""
echo "📋 Next steps:"
echo "   Update colosseum-postgres.container to use: $IMAGE_NAME"
echo "   Run: ./deploy.sh"
