#!/bin/bash
# Cleanup Colosseum PostgreSQL deployment
set -euo pipefail

QUADLET_DIR="${HOME}/.config/containers/systemd"

if [ "$(id -u)" = "0" ]; then
    QUADLET_DIR="/etc/containers/systemd"
fi

echo "🏛️  Colosseum PostgreSQL Cleanup"
echo "=================================="
echo ""
echo "⚠️  This will remove:"
echo "   - PostgreSQL container and service"
echo "   - Database volume (ALL DATA WILL BE LOST)"
echo "   - Network configuration"
echo "   - Quadlet files"
echo ""
read -p "Are you sure? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Stop and disable services
echo "🛑 Stopping services..."
systemctl --user stop colosseum-postgres.service || true
systemctl --user disable colosseum-postgres.service || true

# Remove quadlet files
echo "🗑️  Removing quadlet files..."
rm -f "${QUADLET_DIR}/colosseum-network.network"
rm -f "${QUADLET_DIR}/colosseum-postgres-data.volume"
rm -f "${QUADLET_DIR}/colosseum-postgres.container"

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl --user daemon-reload

# Remove container
echo "📦 Removing container..."
podman rm -f colosseum-postgres || true

# Remove volume
echo "💾 Removing data volume..."
podman volume rm -f colosseum-postgres-data || true

# Remove network
echo "🌐 Removing network..."
podman network rm -f colosseum || true

# Optional: Remove secret
read -p "Remove database password secret? (yes/no): " -r
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "🔐 Removing secret..."
    podman secret rm colosseum-db-password || true
fi

echo ""
echo "✅ Cleanup complete!"
