# Colosseum Deployment Files

This directory contains deployment configurations for various deployment strategies.

## Directory Structure

```
deployment/
├── systemd/              # Systemd service files for production deployment
│   ├── colosseum-curator.service
│   ├── colosseum-curator@.service  # Template for multiple instances
│   ├── colosseum-curator.target
│   ├── colosseum-backup.service
│   ├── colosseum-backup.timer
│   └── install.sh
│
├── kubernetes/           # Kubernetes manifests for K8s deployment
│   ├── namespace.yaml
│   ├── postgres-statefulset.yaml
│   ├── curator-deployment.yaml
│   ├── secrets.yaml
│   ├── kustomization.yaml
│   └── deploy.sh
│
├── docker/               # Container build files
│   ├── Dockerfile                # Standard Docker image
│   ├── Containerfile             # Podman/Fedora image
│   ├── Containerfile.bootc       # Fedora Bootable Container
│   ├── build.sh
│   └── .dockerignore
│
└── README.md            # This file
```

## Quick Links

- **[Deployment Guide](../docs/DEPLOYMENT.md)** - Comprehensive deployment documentation
- **[Quadlets Guide](../quadlets/README.md)** - PostgreSQL quadlet deployment
- **[Curator Documentation](../docs/CURATOR_AGENT.md)** - CuratorAgent details

## Deployment Options

### 1. Local Development

Perfect for development and testing:

```bash
# Deploy PostgreSQL
cd ../quadlets
./deploy.sh
./init-schema.sh

# Run curator directly
python -m colosseum.cli.curator start --interval 60
```

See: [Deployment Guide - Local Development](../docs/DEPLOYMENT.md#1-local-development-setup)

### 2. Systemd/Quadlet (Recommended for Production)

Single-node production deployment with systemd:

```bash
# Install as system service
cd systemd
sudo ./install.sh

# Or install as user service
systemctl --user enable --now colosseum-curator.service
```

See: [Deployment Guide - Systemd](../docs/DEPLOYMENT.md#2-systemdquadlet-deployment-recommended-for-production)

### 3. Kubernetes

Multi-node production deployment:

```bash
# Build image
cd docker
./build.sh

# Deploy to K8s
cd ../kubernetes
./deploy.sh
```

See: [Deployment Guide - Kubernetes](../docs/DEPLOYMENT.md#3-kubernetes-deployment)

### 4. Fedora Bootable Container

Immutable edge deployment:

```bash
# Build bootable container
cd docker
BUILD_BOOTC=true ./build.sh

# Deploy to disk
bootc install to-disk --device /dev/sda ghcr.io/davdunc/colosseum-bootc:latest
```

See: [Deployment Guide - Bootable Container](../docs/DEPLOYMENT.md#4-fedora-bootable-container)

## Deployment Comparison

| Feature | Local | Systemd | Kubernetes | Bootable |
|---------|-------|---------|------------|----------|
| **Complexity** | Low | Low | High | Medium |
| **Scalability** | 1 host | 1 host | Multi-host | 1 host |
| **HA** | No | No | Yes | No |
| **Best For** | Dev/Test | Single-node prod | Enterprise | Edge/IoT |

## Getting Started

1. **Choose your deployment strategy** (see comparison above)
2. **Read the comprehensive [Deployment Guide](../docs/DEPLOYMENT.md)**
3. **Follow the specific deployment instructions** for your chosen strategy
4. **Verify the deployment** with health checks

## Common Commands

### Systemd

```bash
# Status
systemctl --user status colosseum-curator.service

# Logs
journalctl --user -u colosseum-curator.service -f

# Restart
systemctl --user restart colosseum-curator.service
```

### Kubernetes

```bash
# Status
kubectl get all -n colosseum

# Logs
kubectl logs -f deployment/curator -n colosseum

# Shell
kubectl exec -it deployment/curator -n colosseum -- bash
```

### Container

```bash
# Build
cd docker && ./build.sh

# Run
podman run --rm -it ghcr.io/davdunc/colosseum-curator:latest

# Test
podman run --rm ghcr.io/davdunc/colosseum-curator:latest python -m colosseum.cli.curator health
```

## Support

For detailed deployment instructions, troubleshooting, and best practices, see:

- **[Full Deployment Guide](../docs/DEPLOYMENT.md)**
- **[GitHub Issues](https://github.com/davdunc/colosseum/issues)**

## License

See [LICENSE](../LICENSE) in the root of the repository.
