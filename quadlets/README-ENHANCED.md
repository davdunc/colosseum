# Colosseum Quadlet Configuration - Enhanced Production Setup

This directory contains the **production-ready quadlet configuration** for deploying Colosseum with Podman and systemd.

## 🆕 What's New (Enhanced Configuration)

### Custom PostgreSQL Image
- **TimescaleDB 2.13.1** + **pgvector 0.5.1** + **PostgreSQL 16**
- Built from source for optimal compatibility
- Includes all necessary extensions pre-installed

### Optimized Configuration
- **postgresql.conf** - Production-tuned settings for time-series data
- **Enhanced security** - Capability dropping, user isolation
- **Resource limits** - Memory, CPU, and swap constraints
- **Health checks** - Comprehensive readiness probes

### CuratorAgent Quadlet
- **Containerized curator** running as systemd service
- **Automatic restarts** with backoff
- **Resource management** separate from PostgreSQL
- **Integrated logging** via journald

## Quick Start

### 1. Build Custom PostgreSQL Image (First Time Only)

```bash
cd /home/user/colosseum/quadlets
./build-postgres-image.sh
```

This builds a custom image with:
- PostgreSQL 16
- TimescaleDB 2.13.1
- pgvector 0.5.1

**Time**: ~5-10 minutes

### 2. Deploy with Enhanced Script

```bash
./deploy-enhanced.sh
```

This will:
- ✅ Check prerequisites
- ✅ Build image if needed
- ✅ Create podman secrets
- ✅ Install quadlet files
- ✅ Start PostgreSQL
- ✅ Verify extensions
- ✅ Show status

### 3. Initialize Database Schema

```bash
./init-schema.sh
```

This creates:
- market_data schema (quotes, OHLCV, news)
- agent_data schema (decisions, logs)
- metadata schema (tickers, sources)
- TimescaleDB hypertables
- pgvector indexes

### 4. Verify Deployment

```bash
# Check service status
systemctl --user status colosseum-postgres.service

# Verify extensions
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT extname, extversion FROM pg_extension;"

# Check TimescaleDB
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT * FROM timescaledb_information.hypertables;"
```

## Files Overview

### Core Quadlet Files

| File | Purpose |
|------|---------|
| **colosseum-network.network** | Bridge network (10.89.0.0/24) |
| **colosseum-postgres-data.volume** | Persistent data volume |
| **colosseum-postgres.container** | PostgreSQL container (basic) |
| **colosseum-postgres.container.new** | PostgreSQL container (enhanced) |
| **colosseum-curator.container** | CuratorAgent container |

### Build & Deploy Scripts

| File | Purpose |
|------|---------|
| **build-postgres-image.sh** | Build custom PostgreSQL image |
| **deploy.sh** | Original deployment script |
| **deploy-enhanced.sh** | Enhanced deployment with validation |
| **init-schema.sh** | Initialize database schema |
| **cleanup.sh** | Remove all resources |

### Configuration

| File | Purpose |
|------|---------|
| **postgresql.conf** | Production PostgreSQL tuning |
| **config.yaml.example** | Application configuration template |
| **init-db.sql** | Database schema DDL |

## Quadlet Architecture

```
┌─────────────────────────────────────────────┐
│  ~/.config/containers/systemd/              │
│  (or /etc/containers/systemd/)              │
│                                             │
│  ├─ colosseum-network.network               │
│  │  └─ Creates: colosseum bridge           │
│  │                                          │
│  ├─ colosseum-postgres-data.volume          │
│  │  └─ Creates: persistent volume          │
│  │                                          │
│  ├─ colosseum-postgres.container            │
│  │  └─ Container: colosseum-postgres       │
│  │     ├─ Image: localhost/colosseum-postgres:latest │
│  │     ├─ Network: colosseum               │
│  │     ├─ Volume: postgres-data            │
│  │     └─ Secret: db-password              │
│  │                                          │
│  └─ colosseum-curator.container (optional) │
│     └─ Container: colosseum-curator        │
│        ├─ Depends on: postgres             │
│        ├─ Network: colosseum               │
│        └─ Secret: db-password              │
│                                             │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  systemd --user                             │
│  ├─ colosseum-network.service               │
│  ├─ colosseum-postgres-data.service         │
│  ├─ colosseum-postgres.service              │
│  └─ colosseum-curator.service (optional)    │
└─────────────────────────────────────────────┘
```

## Configuration Details

### PostgreSQL Tuning

Key settings in `postgresql.conf`:

```ini
shared_buffers = 512MB           # 25% of RAM
effective_cache_size = 1536MB    # 75% of RAM
work_mem = 16MB
maintenance_work_mem = 128MB
max_connections = 100

# TimescaleDB
shared_preload_libraries = 'timescaledb'
timescaledb.max_background_workers = 8

# WAL
max_wal_size = 1GB
checkpoint_completion_target = 0.9
```

Adjust based on your system resources.

### Resource Limits

**PostgreSQL Container**:
- Memory: 2GB (max)
- CPU: 200% (2 cores)
- Swap: 2GB

**Curator Container**:
- Memory: 1GB (max)
- CPU: 50% (0.5 core)
- Swap: 1GB

### Security

Both containers use:
- ✅ Non-root user (999 for postgres, 1000 for curator)
- ✅ Capability dropping (CAP_DROP=ALL)
- ✅ Minimal capabilities (only what's needed)
- ✅ Podman secrets for credentials
- ✅ SELinux labels (:Z suffix)
- ✅ NoNewPrivileges

## Production Deployment

### System-Wide Installation

For production, deploy system-wide:

```bash
# Use system quadlet directory
export QUADLET_DIR="/etc/containers/systemd"

# Run as root
sudo ./deploy-enhanced.sh

# Use system systemctl (not --user)
sudo systemctl enable --now colosseum-postgres.service
```

### Enable Auto-Updates

```bash
# Enable podman auto-update timer
systemctl --user enable --now podman-auto-update.timer

# Manual update check
podman auto-update

# View auto-update logs
journalctl --user -u podman-auto-update.service
```

### Backup Configuration

Automated backups are configured via systemd timer (see deployment/systemd/):

```bash
# Copy backup service and timer
cp ../deployment/systemd/colosseum-backup.service ~/.config/systemd/user/
cp ../deployment/systemd/colosseum-backup.timer ~/.config/systemd/user/

# Enable timer
systemctl --user enable --now colosseum-backup.timer

# Check next run
systemctl --user list-timers
```

## Monitoring

### Systemd Status

```bash
# Service status
systemctl --user status colosseum-postgres.service

# View logs
journalctl --user -u colosseum-postgres.service -f

# Check resource usage
systemd-cgtop
```

### PostgreSQL Metrics

```bash
# Connection count
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Database size
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT pg_size_pretty(pg_database_size('colosseum_data_lake'));"

# Cache hit ratio
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_hit_ratio FROM pg_statio_user_tables;"
```

### Container Stats

```bash
# Real-time stats
podman stats colosseum-postgres

# Inspect container
podman inspect colosseum-postgres
```

## Troubleshooting

### PostgreSQL Won't Start

```bash
# Check logs
journalctl --user -u colosseum-postgres.service -n 50

# Check if image exists
podman images localhost/colosseum-postgres

# Rebuild image
./build-postgres-image.sh

# Check volume
podman volume inspect colosseum-postgres-data
```

### Extensions Not Loading

```bash
# Check shared_preload_libraries
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SHOW shared_preload_libraries;"

# Manually create extensions
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "CREATE EXTENSION IF NOT EXISTS timescaledb; CREATE EXTENSION IF NOT EXISTS pgvector;"

# Check extension versions
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT * FROM pg_available_extensions WHERE name IN ('timescaledb', 'pgvector');"
```

### Permission Errors

```bash
# Check SELinux context
ls -laZ ~/.local/share/containers/storage/volumes/

# Relabel volume
podman volume rm colosseum-postgres-data
./deploy-enhanced.sh

# Check SELinux denials
sudo ausearch -m avc -ts recent
```

### Performance Issues

```bash
# Check slow queries
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check table bloat
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables WHERE schemaname IN ('market_data', 'agent_data') ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Vacuum analyze
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c "VACUUM ANALYZE;"
```

## Upgrading

### Upgrade PostgreSQL Image

```bash
# Pull new base image
podman pull postgres:16

# Rebuild custom image
./build-postgres-image.sh

# Restart with new image
systemctl --user restart colosseum-postgres.service
```

### Migrate Data

```bash
# Backup current data
podman exec colosseum-postgres pg_dump -U colosseum colosseum_data_lake > backup.sql

# Stop services
systemctl --user stop colosseum-postgres.service

# Remove old volume (DANGER: DATA LOSS)
podman volume rm colosseum-postgres-data

# Redeploy
./deploy-enhanced.sh

# Restore data
podman exec -i colosseum-postgres psql -U colosseum -d colosseum_data_lake < backup.sql
```

## Comparison: Basic vs Enhanced

| Feature | Basic | Enhanced |
|---------|-------|----------|
| **PostgreSQL** | pgvector only | TimescaleDB + pgvector |
| **Image** | docker.io/pgvector/pgvector | Custom built |
| **Config** | Default | Optimized postgresql.conf |
| **Security** | Basic | Capability dropping |
| **Resources** | Basic limits | Tuned limits + swap |
| **Validation** | Minimal | Comprehensive checks |
| **Curator** | Separate | Integrated quadlet |

## References

- [Podman Quadlet Documentation](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
- [Major Hayden's Quadlet Blog](https://major.io/p/quadlet-networking/)
- [TimescaleDB Configuration](https://docs.timescale.com/timescaledb/latest/how-to-guides/configuration/)
- [PostgreSQL Tuning](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server)

## License

See [LICENSE](../LICENSE) in the root of the repository.
