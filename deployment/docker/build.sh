#!/bin/bash
# Build Colosseum container images
set -euo pipefail

REGISTRY="${REGISTRY:-ghcr.io}"
REPO="${REPO:-davdunc/colosseum}"
TAG="${TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"

echo "🏛️  Building Colosseum Container Images"
echo "========================================"
echo "Registry:  $REGISTRY"
echo "Repo:      $REPO"
echo "Tag:       $TAG"
echo "Platform:  $PLATFORM"
echo ""

cd "$(dirname "$0")/../.."

# Determine build tool
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

# Build curator image (standard)
echo ""
echo "📦 Building curator image (Dockerfile)..."
$BUILD_CMD build \
    --platform "$PLATFORM" \
    -t "$REGISTRY/$REPO-curator:$TAG" \
    -f deployment/docker/Dockerfile \
    .

echo "✅ Built: $REGISTRY/$REPO-curator:$TAG"

# Build curator image (Fedora/Podman)
echo ""
echo "📦 Building curator image (Containerfile)..."
$BUILD_CMD build \
    --platform "$PLATFORM" \
    -t "$REGISTRY/$REPO-curator:$TAG-fedora" \
    -f deployment/docker/Containerfile \
    .

echo "✅ Built: $REGISTRY/$REPO-curator:$TAG-fedora"

# Build bootable container (if requested)
if [ "${BUILD_BOOTC:-false}" = "true" ]; then
    echo ""
    echo "📦 Building bootable container..."
    $BUILD_CMD build \
        --platform "$PLATFORM" \
        -t "$REGISTRY/$REPO-bootc:$TAG" \
        -f deployment/docker/Containerfile.bootc \
        .

    echo "✅ Built: $REGISTRY/$REPO-bootc:$TAG"
fi

echo ""
echo "✅ Build complete!"
echo ""
echo "📝 Next steps:"
echo "   Test:  $BUILD_CMD run --rm $REGISTRY/$REPO-curator:$TAG"
echo "   Push:  $BUILD_CMD push $REGISTRY/$REPO-curator:$TAG"
echo ""
echo "🔖 Tagged images:"
$BUILD_CMD images | grep "$REPO"
