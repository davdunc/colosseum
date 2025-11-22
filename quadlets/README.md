# Colosseum Quadlet Configuration

This directory contains Podman Quadlet configuration files for running Colosseum with systemd integration.

## What are Quadlets?

Quadlets are systemd unit files that Podman uses to manage containers declaratively. They provide:
- Native systemd integration
- Automatic dependency management
- Better networking than KIND for localhost access
- Persistent storage with volumes
- Automatic restarts and health checks

## Architecture

```
┌─────────────────────────────────────┐
│  colosseum-network (bridge)         │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ colosseum-db │  │ colosseum-  │ │
│  │ (PostgreSQL) │←─┤   agent     │ │
│  └──────────────┘  └─────────────┘ │
│         ↓                           │
│    colosseum-db-data (volume)       │
└─────────────────────────────────────┘
         ↓
    Host: localhost:5432 (DB)
    Host: localhost:8000 (API)
```

## Installation

### User Service (Recommended for Development)

```bash
# Create user systemd directory
mkdir -p ~/.config/containers/systemd/

# Copy quadlet files
cp quadlets/*.{network,volume,container} ~/.config/containers/systemd/

# Reload systemd to discover quadlets
systemctl --user daemon-reload

# Enable and start services
systemctl --user enable --now colosseum-network.service
systemctl --user enable --now colosseum-db-data.service
systemctl --user enable --now colosseum-state.service
systemctl --user enable --now colosseum-db.service
systemctl --user enable --now colosseum-agent.service
```

### System Service (Production)

```bash
# Copy as root
sudo cp quadlets/*.{network,volume,container} /etc/containers/systemd/

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable --now colosseum-network.service
sudo systemctl enable --now colosseum-db.service
sudo systemctl enable --now colosseum-agent.service
```

## Configuration

### Environment Variables

Create `~/.config/colosseum/env` for secrets:

```bash
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://colosseum:your-password@colosseum-db:5432/colosseum
```

Update `colosseum-agent.container` to load it:
```ini
[Service]
EnvironmentFile=%h/.config/colosseum/env
```

### Database Password

**IMPORTANT**: Change the default password in `colosseum-db.container`:

```ini
Environment=POSTGRES_PASSWORD=your-secure-password-here
```

And update the DATABASE_URL accordingly.

## Management Commands

```bash
# Check status
systemctl --user status colosseum-agent.service
systemctl --user status colosseum-db.service

# View logs
journalctl --user -u colosseum-agent.service -f
journalctl --user -u colosseum-db.service -f

# Restart services
systemctl --user restart colosseum-agent.service

# Stop all services
systemctl --user stop colosseum-agent.service
systemctl --user stop colosseum-db.service

# Start all services
systemctl --user start colosseum-db.service
systemctl --user start colosseum-agent.service
```

## Database Access

### From Host

```bash
# Connect to PostgreSQL from host
psql -h localhost -p 5432 -U colosseum -d colosseum

# Or using docker exec
podman exec -it colosseum-db psql -U colosseum -d colosseum
```

### From Agent Container

The agent container can access the database via the network:
```python
# DATABASE_URL is already set in the container
import os
db_url = os.getenv("DATABASE_URL")
# postgresql://colosseum:password@colosseum-db:5432/colosseum
```

## Building Custom Image

For production, build a custom image with Colosseum installed:

```dockerfile
# Containerfile
FROM registry.fedoraproject.org/fedora:latest

RUN dnf install -y python3 python3-pip && dnf clean all
WORKDIR /opt/colosseum
COPY . .
RUN pip install -e .

CMD ["python3", "-m", "colosseum.main"]
```

Build and update the quadlet:
```bash
podman build -t localhost/colosseum:latest .

# Update colosseum-agent.container:
# Image=localhost/colosseum:latest
# Exec=python3 -m colosseum.main
```

## Networking

- **Database**: Accessible at `localhost:5432` from host, `colosseum-db:5432` from containers
- **Agent API**: Accessible at `localhost:8000` from host
- **Container to Host**: Use `host.containers.internal` to access host services

This solves the KIND localhost access issue by using Podman's bridge networking with proper DNS.

## Troubleshooting

### Services won't start
```bash
# Check systemd status
systemctl --user status colosseum-*.service

# View detailed logs
journalctl --user -xe
```

### Database connection refused
```bash
# Check if DB is running
podman ps | grep colosseum-db

# Check DB logs
podman logs colosseum-db
```

### Port already in use
```bash
# Check what's using the port
ss -tlnp | grep 5432

# Change port in quadlet file
PublishPort=127.0.0.1:5433:5432
```

## Advantages over KIND

1. **Localhost Access**: No networking issues accessing host services
2. **Simpler Setup**: No Kubernetes complexity
3. **Native systemd**: Better integration with Fedora
4. **Easier Debugging**: Direct podman commands work
5. **Better Performance**: No Kubernetes overhead
6. **Persistent State**: Volumes survive container restarts
7. **Service Discovery**: DNS works out of the box

## References

- [Podman Quadlet Documentation](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
- [Systemd Service Files](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
