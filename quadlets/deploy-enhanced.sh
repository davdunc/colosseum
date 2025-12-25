#!/bin/bash
# Enhanced deployment script with validation
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUADLET_DIR="${HOME}/.config/containers/systemd"
POSTGRES_IMAGE="${POSTGRES_IMAGE:-localhost/colosseum-postgres:latest}"

echo "🏛️  Colosseum Quadlet Deployment (Enhanced)"
echo "============================================="

# Check if running rootless
if [ "$(id -u)" = "0" ]; then
    echo "⚠️  Warning: Running as root. Rootless is recommended."
    QUADLET_DIR="/etc/containers/systemd"
fi

# Check for required tools
echo "🔍 Checking prerequisites..."
for cmd in podman systemctl openssl; do
    if ! command -v $cmd &> /dev/null; then
        echo "❌ Required command not found: $cmd"
        exit 1
    fi
    echo "   ✅ $cmd"
done

# Check if custom PostgreSQL image exists
echo ""
echo "🐘 Checking PostgreSQL image..."
if ! podman image exists "$POSTGRES_IMAGE"; then
    echo "⚠️  Custom PostgreSQL image not found: $POSTGRES_IMAGE"
    echo "   Building custom image with TimescaleDB + pgvector..."

    if [ -f "$SCRIPT_DIR/build-postgres-image.sh" ]; then
        "$SCRIPT_DIR/build-postgres-image.sh"
    else
        echo "❌ Build script not found. Please run: ./build-postgres-image.sh"
        exit 1
    fi
else
    echo "   ✅ Image found: $POSTGRES_IMAGE"
fi

# Create systemd directory
echo ""
echo "📁 Creating quadlet directory..."
mkdir -p "${QUADLET_DIR}"

# Create podman secret for database password
echo ""
echo "🔐 Setting up database password secret..."
if podman secret exists colosseum-db-password 2>/dev/null; then
    echo "   Secret already exists."
    read -p "   Recreate? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        podman secret rm colosseum-db-password
    else
        echo "   Using existing secret."
    fi
fi

if ! podman secret exists colosseum-db-password 2>/dev/null; then
    if [ -t 0 ]; then
        echo -n "   Enter PostgreSQL password (or press Enter for random): "
        read -s DB_PASSWORD
        echo
        if [ -z "$DB_PASSWORD" ]; then
            DB_PASSWORD=$(openssl rand -base64 32)
            echo "   Generated random password: $DB_PASSWORD"
            echo "   💾 SAVE THIS PASSWORD!"
        fi
    else
        DB_PASSWORD=$(openssl rand -base64 32)
        echo "   Generated random password (non-interactive)"
    fi

    echo -n "$DB_PASSWORD" | podman secret create colosseum-db-password -
    echo "   ✅ Secret created: colosseum-db-password"
fi

# Install quadlet files
echo ""
echo "📋 Installing quadlet files..."
cp -v "${SCRIPT_DIR}/colosseum-network.network" "${QUADLET_DIR}/"
cp -v "${SCRIPT_DIR}/colosseum-postgres-data.volume" "${QUADLET_DIR}/"

# Use enhanced PostgreSQL container configuration
if [ -f "${SCRIPT_DIR}/colosseum-postgres.container.new" ]; then
    echo "   Using enhanced PostgreSQL configuration..."
    cp -v "${SCRIPT_DIR}/colosseum-postgres.container.new" "${QUADLET_DIR}/colosseum-postgres.container"
else
    cp -v "${SCRIPT_DIR}/colosseum-postgres.container" "${QUADLET_DIR}/"
fi

# Update container file to use secrets and custom image
cat > "${QUADLET_DIR}/colosseum-postgres.container" <<EOF
[Unit]
Description=PostgreSQL database for Colosseum data lake
Documentation=https://github.com/davdunc/colosseum
After=colosseum-network.service
Requires=colosseum-network.service
Wants=colosseum-postgres-data.service

[Container]
Image=${POSTGRES_IMAGE}
ContainerName=colosseum-postgres
Pull=missing
Network=colosseum-network.network
PublishPort=5432:5432
Volume=colosseum-postgres-data.volume:/var/lib/postgresql/data:Z

# Database configuration
Environment=POSTGRES_DB=colosseum_data_lake
Environment=POSTGRES_USER=colosseum
Secret=colosseum-db-password,type=env,target=POSTGRES_PASSWORD
Environment=PGDATA=/var/lib/postgresql/data/pgdata

# Security
User=999
SecurityLabelDisable=false
DropCapability=ALL
AddCapability=CHOWN SETGID SETUID DAC_OVERRIDE

# Healthcheck
HealthCmd=/usr/bin/pg_isready -U colosseum -d colosseum_data_lake
HealthInterval=10s
HealthTimeout=5s
HealthRetries=5
HealthStartPeriod=30s

# Resources
Memory=2g
CPUShares=1024
CPUQuota=200%

# Auto-updates
Label=io.containers.autoupdate=registry

# Logging
LogDriver=journald

[Service]
Restart=always
RestartSec=10
TimeoutStartSec=120
TimeoutStopSec=30

[Install]
WantedBy=default.target
EOF

# Reload systemd
echo ""
echo "🔄 Reloading systemd daemon..."
systemctl --user daemon-reload

# Enable and start services
echo ""
echo "🚀 Starting PostgreSQL service..."
systemctl --user enable --now colosseum-postgres.service

# Wait for PostgreSQL with better feedback
echo ""
echo "⏳ Waiting for PostgreSQL to be ready (max 60s)..."
for i in {1..30}; do
    if podman exec colosseum-postgres pg_isready -U colosseum -d colosseum_data_lake &>/dev/null; then
        echo "   ✅ PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ PostgreSQL did not start in time"
        echo "   Check logs: journalctl --user -u colosseum-postgres.service"
        exit 1
    fi
    printf "   Waiting... (%d/30)\r" $i
    sleep 2
done

# Verify extensions
echo ""
echo "🔍 Verifying extensions..."
if podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('timescaledb', 'pgvector');" &>/dev/null; then
    echo "   ✅ Extensions check passed"
else
    echo "   ⚠️  Could not verify extensions (database may not be initialized yet)"
fi

# Show status
echo ""
echo "📊 Service Status:"
systemctl --user status colosseum-postgres.service --no-pager --lines=10 || true

# Summary
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Initialize database schema:"
echo "      ./init-schema.sh"
echo ""
echo "   2. Verify deployment:"
echo "      systemctl --user status colosseum-postgres.service"
echo "      podman exec -it colosseum-postgres psql -U colosseum -d colosseum_data_lake"
echo ""
echo "   3. Check logs:"
echo "      journalctl --user -u colosseum-postgres.service -f"
echo ""
echo "🔐 Retrieve password:"
echo "   podman secret inspect colosseum-db-password --showsecret"
echo ""
echo "🔗 Connection string:"
echo "   postgresql://colosseum:<password>@localhost:5432/colosseum_data_lake"
