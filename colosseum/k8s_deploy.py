import subprocess

def deploy_fedora_container(name, image, command=None, env=None):
    # Use kubectl to deploy a Fedora container in KIND
    cmd = [
        "kubectl", "run", name,
        "--image", image,
        "--restart", "Never"
    ]
    if command:
        cmd += ["--", *command]
    if env:
        for k, v in env.items():
            cmd += ["--env", f"{k}={v}"]
    subprocess.run(cmd, check=True)
