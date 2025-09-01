import os
import yaml

def get_config_path(app_name="colosseum"):
    # Service locations
    service_paths = [
        f"/etc/{app_name}/config.yaml",
        f"/var/lib/{app_name}/config.yaml"
    ]
    # XDG locations
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    xdg_path = os.path.join(xdg_config_home, app_name, "config.yaml")
    # Check service paths first if running as root
    if os.geteuid() == 0:
        for path in service_paths:
            if os.path.exists(path):
                return path
    # Otherwise, use XDG
    if os.path.exists(xdg_path):
        return xdg_path
    # Fallback: first service path or XDG path
    return service_paths[0] if os.geteuid() == 0 else xdg_path

def load_config():
    path = get_config_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return yaml.safe_load(f)
    return {}

def save_config(config):
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(config, f)
