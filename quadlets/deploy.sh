#!/bin/bash
# Deploy Colosseum PostgreSQL using Podman Quadlets
# Following Major Hayden's approach to quadlet networking
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUADLET_DIR="${HOME}/.config/containers/systemd"

echo "🏛️  Colosseum PostgreSQL Quadlet Deployment"
echo "============================================="

# Check if running rootless
if [ "$(id -u)" = "0" ]; then
    echo "⚠️  Warning: Running as root. Consider using rootless podman."
    QUADLET_DIR="/etc/containers/systemd"
fi

# Create systemd directory for quadlets
echo "📁 Creating systemd quadlet directory..."
mkdir -p "${QUADLET_DIR}"

# Create podman secret for database password
echo "🔐 Setting up database password secret..."
if podman secret exists colosseum-db-password 2>/dev/null; then
    echo "   Secret already exists. Remove with: podman secret rm colosseum-db-password"
else
    # Generate a random password or prompt user
    if [ -t 0 ]; then
        echo -n "   Enter PostgreSQL password (or press Enter for random): "
        read -s DB_PASSWORD
        echo
        if [ -z "$DB_PASSWORD" ]; then
            DB_PASSWORD=$(openssl rand -base64 32)
            echo "   Generated random password: $DB_PASSWORD"
            echo "   Save this password! It won't be shown again."
        fi
    else
        DB_PASSWORD=$(openssl rand -base64 32)
        echo "   Generated random password (non-interactive mode)"
    fi

    echo -n "$DB_PASSWORD" | podman secret create colosseum-db-password -
    echo "   ✅ Secret created: colosseum-db-password"
fi

# Copy quadlet files to systemd directory
echo "📋 Installing quadlet files..."
cp -v "${SCRIPT_DIR}/colosseum-network.network" "${QUADLET_DIR}/"
cp -v "${SCRIPT_DIR}/colosseum-postgres-data.volume" "${QUADLET_DIR}/"
cp -v "${SCRIPT_DIR}/colosseum-postgres.container" "${QUADLET_DIR}/"

# Update the container file to use secrets instead of plain env
echo "🔧 Configuring container to use secrets..."
cat > "${QUADLET_DIR}/colosseum-postgres.container" <<'EOF'
[Unit]
Description=PostgreSQL database for Colosseum data lake
Documentation=https://github.com/davdunc/colosseum
After=colosseum-network.service
Requires=colosseum-network.service
Wants=colosseum-postgres-data.service

[Container]
Image=docker.io/pgvector/pgvector:pg16
ContainerName=colosseum-postgres
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

# Healthcheck
HealthCmd=/usr/bin/pg_isready -U colosseum -d colosseum_data_lake
HealthInterval=10s
HealthTimeout=5s
HealthRetries=5
HealthStartPeriod=30s

# Resources
Memory=2g
CPUShares=1024

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

# Reload systemd to pick up the new quadlet files
echo "🔄 Reloading systemd daemon..."
systemctl --user daemon-reload

# Enable and start the services
echo "🚀 Starting services..."
systemctl --user enable --now colosseum-postgres.service

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if podman exec colosseum-postgres pg_isready -U colosseum -d colosseum_data_lake &>/dev/null; then
        echo "   ✅ PostgreSQL is ready!"
        break
    fi
    echo "   Waiting... ($i/30)"
    sleep 2
done

# Show status
echo ""
echo "📊 Service Status:"
systemctl --user status colosseum-postgres.service --no-pager || true

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Useful commands:"
echo "   Status:    systemctl --user status colosseum-postgres.service"
echo "   Logs:      journalctl --user -u colosseum-postgres.service -f"
echo "   Stop:      systemctl --user stop colosseum-postgres.service"
echo "   Restart:   systemctl --user restart colosseum-postgres.service"
echo "   Shell:     podman exec -it colosseum-postgres psql -U colosseum -d colosseum_data_lake"
echo ""
echo "🔗 Connection string:"
echo "   postgresql://colosseum:<password>@localhost:5432/colosseum_data_lake"
echo ""
echo "🔐 To retrieve the password: podman secret inspect colosseum-db-password"
