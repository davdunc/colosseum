"""
Podman Quadlet deployment and management for Colosseum agents.

Provides functions to deploy, manage, and monitor Colosseum services
using Podman Quadlets with systemd integration.
"""

import subprocess
import shutil
import os
from pathlib import Path
from typing import Optional, List, Dict


class QuadletDeployment:
    """Manage Podman Quadlet deployments for Colosseum."""

    def __init__(self, system_wide: bool = False):
        """
        Initialize Quadlet deployment manager.

        Args:
            system_wide: If True, use system-wide deployment (/etc/containers/systemd)
                        If False, use user deployment (~/.config/containers/systemd)
        """
        self.system_wide = system_wide
        if system_wide:
            self.systemd_dir = Path("/etc/containers/systemd")
            self.systemctl_cmd = ["systemctl"]
        else:
            self.systemd_dir = Path.home() / ".config" / "containers" / "systemd"
            self.systemctl_cmd = ["systemctl", "--user"]

    def install_quadlets(self, source_dir: Optional[Path] = None) -> bool:
        """
        Install Quadlet files from source directory to systemd directory.

        Args:
            source_dir: Directory containing .container, .network, .volume files
                       Defaults to ./quadlets in the project root

        Returns:
            True if installation succeeded
        """
        if source_dir is None:
            # Find quadlets directory relative to this file
            project_root = Path(__file__).parent.parent
            source_dir = project_root / "quadlets"

        if not source_dir.exists():
            raise FileNotFoundError(f"Quadlets directory not found: {source_dir}")

        # Create systemd directory if it doesn't exist
        self.systemd_dir.mkdir(parents=True, exist_ok=True)

        # Copy all quadlet files
        quadlet_files = list(source_dir.glob("*.network")) + \
                        list(source_dir.glob("*.volume")) + \
                        list(source_dir.glob("*.container"))

        if not quadlet_files:
            raise FileNotFoundError(f"No quadlet files found in {source_dir}")

        for file in quadlet_files:
            dest = self.systemd_dir / file.name
            shutil.copy2(file, dest)
            print(f"Installed: {file.name} -> {dest}")

        # Reload systemd to discover new units
        self._systemctl(["daemon-reload"])
        return True

    def enable_services(self, services: Optional[List[str]] = None):
        """
        Enable and start Colosseum services.

        Args:
            services: List of service names to enable. If None, enables all Colosseum services
        """
        if services is None:
            services = [
                "colosseum-network.service",
                "colosseum-db-data.service",
                "colosseum-state.service",
                "colosseum-db.service",
                "colosseum-agent.service",
            ]

        for service in services:
            print(f"Enabling {service}...")
            self._systemctl(["enable", "--now", service])

    def disable_services(self, services: Optional[List[str]] = None):
        """
        Disable and stop Colosseum services.

        Args:
            services: List of service names to disable. If None, disables all Colosseum services
        """
        if services is None:
            services = [
                "colosseum-agent.service",
                "colosseum-db.service",
                "colosseum-state.service",
                "colosseum-db-data.service",
                "colosseum-network.service",
            ]

        for service in services:
            print(f"Disabling {service}...")
            self._systemctl(["disable", "--now", service])

    def status(self, service: str = "colosseum-agent.service") -> Dict[str, str]:
        """
        Get status of a Colosseum service.

        Args:
            service: Service name to check

        Returns:
            Dictionary with status information
        """
        result = self._systemctl(["status", service], check=False, capture_output=True)
        return {
            "service": service,
            "returncode": result.returncode,
            "output": result.stdout.decode() if result.stdout else "",
            "error": result.stderr.decode() if result.stderr else "",
        }

    def logs(self, service: str = "colosseum-agent.service", follow: bool = False, lines: int = 50):
        """
        View logs for a Colosseum service.

        Args:
            service: Service name
            follow: If True, follow logs in real-time
            lines: Number of lines to show
        """
        cmd = ["journalctl"]
        if not self.system_wide:
            cmd.append("--user")
        cmd.extend(["-u", service, "-n", str(lines)])
        if follow:
            cmd.append("-f")

        subprocess.run(cmd)

    def restart(self, service: str = "colosseum-agent.service"):
        """
        Restart a Colosseum service.

        Args:
            service: Service name to restart
        """
        print(f"Restarting {service}...")
        self._systemctl(["restart", service])

    def exec_in_container(self, container: str, command: List[str]) -> subprocess.CompletedProcess:
        """
        Execute a command in a running container.

        Args:
            container: Container name (e.g., "colosseum-agent")
            command: Command to execute as list of strings

        Returns:
            CompletedProcess with command results
        """
        cmd = ["podman", "exec", "-it", container] + command
        return subprocess.run(cmd)

    def db_shell(self):
        """Open a PostgreSQL shell in the database container."""
        self.exec_in_container("colosseum-db", ["psql", "-U", "colosseum", "-d", "colosseum"])

    def agent_shell(self):
        """Open a bash shell in the agent container."""
        self.exec_in_container("colosseum-agent", ["/bin/bash"])

    def _systemctl(self, args: List[str], check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
        """
        Run systemctl command.

        Args:
            args: Arguments to pass to systemctl
            check: If True, raise exception on non-zero exit
            capture_output: If True, capture stdout/stderr

        Returns:
            CompletedProcess with command results
        """
        cmd = self.systemctl_cmd + args
        return subprocess.run(cmd, check=check, capture_output=capture_output)


def deploy_colosseum(system_wide: bool = False):
    """
    Deploy Colosseum using Quadlets.

    Args:
        system_wide: If True, deploy system-wide (requires root)
                    If False, deploy as user service

    Example:
        >>> from colosseum.quadlet_deploy import deploy_colosseum
        >>> deploy_colosseum(system_wide=False)
    """
    deployment = QuadletDeployment(system_wide=system_wide)

    print("Installing Quadlet files...")
    deployment.install_quadlets()

    print("\nEnabling services...")
    deployment.enable_services()

    print("\nDeployment complete!")
    print("\nUseful commands:")
    if system_wide:
        print("  sudo systemctl status colosseum-agent.service")
        print("  sudo journalctl -u colosseum-agent.service -f")
    else:
        print("  systemctl --user status colosseum-agent.service")
        print("  journalctl --user -u colosseum-agent.service -f")
    print("\nAccess database: podman exec -it colosseum-db psql -U colosseum -d colosseum")


def undeploy_colosseum(system_wide: bool = False):
    """
    Remove Colosseum Quadlet deployment.

    Args:
        system_wide: If True, remove system-wide deployment
                    If False, remove user deployment
    """
    deployment = QuadletDeployment(system_wide=system_wide)

    print("Disabling services...")
    deployment.disable_services()

    print("\nTo remove Quadlet files:")
    print(f"  rm -rf {deployment.systemd_dir}/colosseum-*")
    print("  Then run: systemctl daemon-reload")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "deploy":
        deploy_colosseum(system_wide="--system" in sys.argv)
    elif len(sys.argv) > 1 and sys.argv[1] == "undeploy":
        undeploy_colosseum(system_wide="--system" in sys.argv)
    else:
        print("Usage: python -m colosseum.quadlet_deploy [deploy|undeploy] [--system]")
        sys.exit(1)
