#!/bin/bash
# Install Colosseum systemd services
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/colosseum}"
SERVICE_DIR="${SERVICE_DIR:-/etc/systemd/system}"
USER="${COLOSSEUM_USER:-colosseum}"
GROUP="${COLOSSEUM_GROUP:-colosseum}"

echo "🏛️  Installing Colosseum Systemd Services"
echo "==========================================="
echo "Install dir: $INSTALL_DIR"
echo "Service dir: $SERVICE_DIR"
echo "User/Group:  $USER:$GROUP"
echo ""

# Check if running as root
if [ "$(id -u)" != "0" ]; then
    echo "❌ This script must be run as root (for system-wide installation)"
    echo "   For user installation, use --user flag"
    exit 1
fi

# Create colosseum user if it doesn't exist
if ! id "$USER" &>/dev/null; then
    echo "👤 Creating user: $USER"
    useradd -r -s /bin/bash -d "$INSTALL_DIR" -m "$USER"
else
    echo "👤 User already exists: $USER"
fi

# Install application
echo "📦 Installing application to $INSTALL_DIR..."
if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
fi

# Copy application files
echo "   Copying application files..."
cp -r ../../colosseum "$INSTALL_DIR/"
cp -r ../../quadlets "$INSTALL_DIR/"
cp -r ../../examples "$INSTALL_DIR/"

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r colosseum/requirements.txt

# Create directories
echo "📁 Creating directories..."
mkdir -p /etc/colosseum
mkdir -p /var/lib/colosseum/backups
mkdir -p /var/log/colosseum

# Set ownership
chown -R "$USER:$GROUP" "$INSTALL_DIR"
chown -R "$USER:$GROUP" /var/lib/colosseum
chown -R "$USER:$GROUP" /var/log/colosseum

# Install systemd services
echo "🔧 Installing systemd services..."
cp colosseum-curator.service "$SERVICE_DIR/"
cp colosseum-curator@.service "$SERVICE_DIR/"
cp colosseum-curator.target "$SERVICE_DIR/"
cp colosseum-backup.service "$SERVICE_DIR/"
cp colosseum-backup.timer "$SERVICE_DIR/"

# Install backup script
echo "📜 Installing backup script..."
cat > /usr/local/bin/colosseum-backup.sh <<'EOF'
#!/bin/bash
# Backup Colosseum PostgreSQL database
set -euo pipefail

BACKUP_DIR="/var/lib/colosseum/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/colosseum_$TIMESTAMP.sql"
RETENTION_DAYS=30

# Create backup
echo "Starting backup at $(date)"
podman exec colosseum-postgres pg_dump -U colosseum colosseum_data_lake | gzip > "$BACKUP_FILE.gz"

# Verify backup
if [ -f "$BACKUP_FILE.gz" ]; then
    SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
    echo "Backup completed: $BACKUP_FILE.gz ($SIZE)"
else
    echo "ERROR: Backup failed!"
    exit 1
fi

# Remove old backups
echo "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "colosseum_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully"
EOF

chmod +x /usr/local/bin/colosseum-backup.sh

# Create configuration template
echo "⚙️  Creating configuration template..."
cat > /etc/colosseum/curator.env <<'EOF'
# Colosseum Curator Configuration
# Customize these values for your environment

# Watchlist for different worker instances (for multi-instance setup)
WATCHLIST_1=AAPL GOOGL MSFT
WATCHLIST_2=AMZN TSLA NVDA
WATCHLIST_3=META NFLX AMD

# Curator settings
FETCH_INTERVAL=60
CACHE_TTL=300

# Logging
LOG_LEVEL=INFO
EOF

# Reload systemd
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Print next steps
echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Deploy PostgreSQL:"
echo "      cd $INSTALL_DIR/quadlets"
echo "      sudo -u $USER ./deploy.sh"
echo "      sudo -u $USER ./init-schema.sh"
echo ""
echo "   2. Configure MCP servers:"
echo "      vi /etc/colosseum/mcp.json"
echo ""
echo "   3. Edit configuration:"
echo "      vi /etc/colosseum/curator.env"
echo ""
echo "   4. Enable and start services:"
echo "      systemctl enable --now colosseum-curator.service"
echo "      systemctl enable --now colosseum-backup.timer"
echo ""
echo "   5. Check status:"
echo "      systemctl status colosseum-curator.service"
echo "      journalctl -u colosseum-curator.service -f"
echo ""
echo "🔗 Documentation: $INSTALL_DIR/docs/DEPLOYMENT.md"
