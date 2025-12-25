# Colosseum Deployment Guide

## Overview

Colosseum supports multiple deployment strategies to accommodate different environments and use cases:

1. **Local Development** - Direct Python execution for development and testing
2. **Systemd/Quadlet** - Production deployment on Fedora/RHEL with systemd integration
3. **Kubernetes** - Containerized deployment on KIND or production K8s clusters
4. **Fedora Bootable Container** - Immutable infrastructure deployment

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Deployment Layer                                       │
│  ├─ Systemd (quadlets) - PostgreSQL, Agents            │
│  ├─ Kubernetes (pods) - All services                   │
│  └─ Fedora Bootable Container - Immutable base         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Application Layer                                      │
│  ├─ SupervisorAgent (orchestrator)                     │
│  ├─ CuratorAgent (data lake keeper)                    │
│  ├─ ResearchAgent (analysis)                           │
│  ├─ PortfolioAgent (portfolio management)              │
│  └─ TradingAgent (execution)                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Data & Integration Layer                               │
│  ├─ PostgreSQL Data Lake (TimescaleDB + pgvector)      │
│  ├─ MCP Servers (IB, E*TRADE, DAS Trader)             │
│  └─ Redis Cache (optional)                             │
└─────────────────────────────────────────────────────────┘
```

---

## 1. Local Development Setup

### Prerequisites

- Python 3.11+
- Podman 4.6+ (for PostgreSQL)
- Git

### Quick Start

```bash
# Clone repository
git clone https://github.com/davdunc/colosseum.git
cd colosseum

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r colosseum/requirements.txt

# Deploy PostgreSQL data lake
cd quadlets
./deploy.sh
./init-schema.sh
cd ..

# Configure
mkdir -p ~/.config/colosseum
cp quadlets/config.yaml.example ~/.config/colosseum/config.yaml
export DB_PASSWORD=$(podman secret inspect colosseum-db-password --showsecret)

# Run the curator
python -m colosseum.cli.curator start --interval 60 --tickers AAPL GOOGL MSFT
```

### Development Workflow

```bash
# Terminal 1: PostgreSQL
systemctl --user status colosseum-postgres.service
journalctl --user -u colosseum-postgres.service -f

# Terminal 2: Curator Agent
python -m colosseum.cli.curator start --interval 60

# Terminal 3: Development/Testing
python examples/curator_example.py
pytest tests/
```

---

## 2. Systemd/Quadlet Deployment (Recommended for Production)

### Overview

Uses Podman Quadlets for systemd-native container management. This is the **recommended production deployment** for single-node or small-scale deployments.

### Components

- **PostgreSQL** (quadlet) - Data lake
- **CuratorAgent** (systemd service) - Background worker
- **Additional Agents** (systemd services) - As needed

### PostgreSQL Deployment (Already Documented)

See [quadlets/README.md](../quadlets/README.md) for PostgreSQL deployment.

### CuratorAgent Systemd Service

Create systemd service for the CuratorAgent:

**File**: `~/.config/systemd/user/colosseum-curator.service`

```ini
[Unit]
Description=Colosseum CuratorAgent - The Keeper of Records
Documentation=https://github.com/davdunc/colosseum
After=colosseum-postgres.service
Requires=colosseum-postgres.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/colosseum
Environment="PATH=/opt/colosseum/venv/bin:/usr/bin"
Environment="DB_PASSWORD_FILE=/run/user/%U/secrets/colosseum-db-password"
ExecStartPre=/bin/bash -c 'podman secret inspect colosseum-db-password --showsecret > /run/user/%U/secrets/colosseum-db-password'
ExecStart=/opt/colosseum/venv/bin/python -m colosseum.cli.curator start --interval 60 --tickers AAPL GOOGL MSFT AMZN TSLA
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true

# Resource limits
MemoryMax=1G
CPUQuota=50%

[Install]
WantedBy=default.target
```

### Deployment Steps

```bash
# 1. Install application
sudo mkdir -p /opt/colosseum
sudo cp -r colosseum /opt/colosseum/
cd /opt/colosseum
python3 -m venv venv
source venv/bin/activate
pip install -r colosseum/requirements.txt

# 2. Install systemd service
mkdir -p ~/.config/systemd/user
cp deployment/systemd/colosseum-curator.service ~/.config/systemd/user/

# 3. Enable and start
systemctl --user daemon-reload
systemctl --user enable --now colosseum-curator.service

# 4. Check status
systemctl --user status colosseum-curator.service
journalctl --user -u colosseum-curator.service -f
```

### System-wide Deployment (Root)

For system-wide deployment:

```bash
# Install to /opt/colosseum (as shown above)

# Create systemd service at /etc/systemd/system/colosseum-curator.service
sudo cp deployment/systemd/colosseum-curator.service /etc/systemd/system/

# Adjust paths and user
sudo systemctl daemon-reload
sudo systemctl enable --now colosseum-curator.service
```

---

## 3. Kubernetes Deployment

### Overview

Deploy all Colosseum components to Kubernetes (KIND for development, production K8s for prod).

### Prerequisites

```bash
# Install KIND
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Create cluster
kind create cluster --name colosseum
```

### Architecture

```
┌─────────────────────────────────────────┐
│  Kubernetes Cluster                     │
│                                         │
│  ┌────────────────────────────────┐    │
│  │  Namespace: colosseum          │    │
│  │                                 │    │
│  │  Pods:                          │    │
│  │  ├─ postgres-0 (StatefulSet)   │    │
│  │  ├─ curator-xxx (Deployment)   │    │
│  │  ├─ supervisor-xxx              │    │
│  │  └─ agents-xxx (Deployment)    │    │
│  │                                 │    │
│  │  Services:                      │    │
│  │  ├─ postgres (ClusterIP)       │    │
│  │  └─ curator-api (ClusterIP)    │    │
│  │                                 │    │
│  │  ConfigMaps:                    │    │
│  │  ├─ colosseum-config            │    │
│  │  └─ mcp-config                  │    │
│  │                                 │    │
│  │  Secrets:                       │    │
│  │  ├─ postgres-credentials        │    │
│  │  └─ mcp-api-keys                │    │
│  │                                 │    │
│  │  PersistentVolumes:             │    │
│  │  └─ postgres-data (10Gi)       │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### Manifests

Will be created in `deployment/kubernetes/` directory.

---

## 4. Fedora Bootable Container

### Overview

Deploy Colosseum as an immutable Fedora Bootable Container for edge deployments or production immutability.

### Containerfile

```dockerfile
FROM quay.io/fedora/fedora-bootc:43

# Install dependencies
RUN dnf install -y \
    python3.11 \
    python3-pip \
    podman \
    postgresql \
    && dnf clean all

# Install Colosseum
COPY colosseum /opt/colosseum/
WORKDIR /opt/colosseum
RUN python3 -m venv venv && \
    source venv/bin/activate && \
    pip install -r requirements.txt

# Install quadlet files
COPY quadlets/*.network /etc/containers/systemd/
COPY quadlets/*.volume /etc/containers/systemd/
COPY quadlets/*.container /etc/containers/systemd/

# Install systemd services
COPY deployment/systemd/*.service /etc/systemd/system/

# Enable services
RUN systemctl enable colosseum-postgres.service && \
    systemctl enable colosseum-curator.service

# Expose ports
EXPOSE 5432

CMD ["/sbin/init"]
```

### Build and Deploy

```bash
# Build bootable container
podman build -t colosseum-bootc:latest -f Containerfile .

# Deploy to bootable system
bootc install to-disk --device /dev/sda colosseum-bootc:latest
```

---

## 5. Deployment Comparison

| Feature | Local Dev | Systemd/Quadlet | Kubernetes | Bootable Container |
|---------|-----------|-----------------|------------|-------------------|
| **Use Case** | Development | Single-node prod | Multi-node prod | Edge/Immutable |
| **Complexity** | Low | Low | High | Medium |
| **Scalability** | Single host | Single host | Multi-host | Single host |
| **HA** | No | No | Yes | No |
| **Updates** | Manual | dnf/systemctl | kubectl | Atomic |
| **Rollback** | Manual | Manual | kubectl | Atomic |
| **Resource Usage** | Low | Low | Medium-High | Low |
| **Best For** | Testing | Production (1-2 nodes) | Production (3+ nodes) | Edge/IoT |

---

## 6. Production Considerations

### Security

**Secrets Management**:
```bash
# Use podman secrets (Quadlet)
echo "my_password" | podman secret create colosseum-db-password -

# Use Kubernetes secrets (K8s)
kubectl create secret generic postgres-credentials \
  --from-literal=password=$(openssl rand -base64 32)

# Use environment variables
export DB_PASSWORD=$(cat /run/secrets/db-password)
```

**Network Security**:
- Disable PostgreSQL port publishing for internal-only access
- Use firewall rules (firewalld/iptables)
- Enable SSL/TLS for database connections

**Container Security**:
- Run rootless containers (Podman)
- Use SELinux contexts
- Limit capabilities with SecurityContext (K8s)

### Monitoring

**Systemd/Quadlet**:
```bash
# Logs
journalctl --user -u colosseum-curator.service -f
journalctl --user -u colosseum-postgres.service -f

# Status
systemctl --user status colosseum-curator.service

# Metrics (via systemd)
systemd-cgtop
```

**Kubernetes**:
```bash
# Logs
kubectl logs -f deployment/curator -n colosseum

# Metrics (requires metrics-server)
kubectl top pods -n colosseum

# Events
kubectl get events -n colosseum
```

### Backup and Recovery

**Database Backup**:
```bash
# Podman (local)
podman exec colosseum-postgres pg_dump -U colosseum colosseum_data_lake > backup.sql

# Kubernetes
kubectl exec -n colosseum postgres-0 -- pg_dump -U colosseum colosseum_data_lake > backup.sql
```

**Automated Backups with Systemd Timer**:
```ini
# /etc/systemd/system/colosseum-backup.service
[Unit]
Description=Backup Colosseum PostgreSQL database

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup-colosseum.sh

# /etc/systemd/system/colosseum-backup.timer
[Unit]
Description=Colosseum backup timer

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

### High Availability

**PostgreSQL HA** (for K8s):
- Use PostgreSQL Operator (Zalando, Crunchy)
- Configure streaming replication
- Use persistent volumes with ReadWriteMany

**Agent HA**:
- Deploy multiple curator instances
- Use leader election (Kubernetes)
- Implement distributed locking

### Scaling

**Vertical Scaling**:
```bash
# Increase PostgreSQL resources (Quadlet)
# Edit /home/user/.config/containers/systemd/colosseum-postgres.container
Memory=4g
CPUShares=2048

# Increase curator resources (Systemd)
# Edit /home/user/.config/systemd/user/colosseum-curator.service
MemoryMax=2G
CPUQuota=100%
```

**Horizontal Scaling** (K8s only):
```yaml
# Curator Deployment
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
```

---

## 7. Environment-Specific Configurations

### Development
- Single PostgreSQL container
- Single curator instance
- Debug logging enabled
- Short cache TTL (60s)

### Staging
- PostgreSQL with replicas
- Multiple curator instances
- Info logging
- Standard cache TTL (300s)
- Smaller watchlist

### Production
- PostgreSQL HA setup
- Auto-scaling curator
- Warning/Error logging only
- Optimized cache TTL
- Full watchlist
- Monitoring and alerting

---

## 8. Troubleshooting

### Common Issues

**PostgreSQL won't start**:
```bash
# Check logs
journalctl --user -u colosseum-postgres.service -n 50

# Verify volume
podman volume inspect colosseum-postgres-data

# Check SELinux
sudo ausearch -m avc -ts recent
```

**Curator can't connect to database**:
```bash
# Test connection
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c "SELECT 1"

# Check password
echo $DB_PASSWORD

# Verify network
podman network inspect colosseum
```

**Agent crashes**:
```bash
# Check logs
journalctl --user -u colosseum-curator.service -f

# Check health
python -m colosseum.cli.curator health

# Restart
systemctl --user restart colosseum-curator.service
```

---

## 9. Migration Paths

### Local → Quadlet
```bash
# 1. Export data
podman exec colosseum-postgres pg_dump -U colosseum colosseum_data_lake > migration.sql

# 2. Deploy quadlet
cd quadlets && ./deploy.sh && ./init-schema.sh

# 3. Import data
podman exec -i colosseum-postgres psql -U colosseum -d colosseum_data_lake < migration.sql

# 4. Deploy systemd service
systemctl --user enable --now colosseum-curator.service
```

### Quadlet → Kubernetes
```bash
# 1. Build container image
podman build -t curator:latest -f deployment/docker/Dockerfile .

# 2. Push to registry
podman push curator:latest registry.example.com/colosseum/curator:latest

# 3. Deploy to K8s
kubectl apply -f deployment/kubernetes/

# 4. Migrate data (using pg_dump/restore)
```

---

## 10. Next Steps

After deployment:

1. **Verify Installation**
   ```bash
   python -m colosseum.cli.curator health
   python -m colosseum.cli.curator stats
   ```

2. **Configure Watchlist**
   ```bash
   python -m colosseum.cli.curator watch AAPL GOOGL MSFT AMZN TSLA
   ```

3. **Backfill Historical Data**
   ```bash
   python -m colosseum.cli.curator backfill AAPL --period 1Y
   ```

4. **Set Up Monitoring**
   - Configure alerts for agent failures
   - Set up log aggregation
   - Monitor database performance

5. **Deploy Additional Agents**
   - ResearchAgent
   - PortfolioAgent
   - TradingAgent

---

## Resources

- [Quadlets README](../quadlets/README.md) - PostgreSQL deployment
- [CuratorAgent Documentation](CURATOR_AGENT.md) - Agent details
- [Systemd Documentation](https://systemd.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Podman Documentation](https://docs.podman.io/)
