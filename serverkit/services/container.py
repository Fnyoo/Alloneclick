"""Container: Docker, Podman, containerd, LXC."""
from .services.base import Service, ServiceCategory


class ContainerServices(ServiceCategory):
    name = "Container"

    services = (
        Service("docker", "Docker Engine", "Container",
                ("docker.io", "docker-compose-v2"),
                ("docker",), None, ("/etc/docker",), ("docker", "info"),
                external_repo=True, description="Container runtime + compose"),
        Service("podman", "Podman", "Container", ("podman",), ("podman",), None,
                ("/etc/containers",), ("podman", "info"),
                description="Daemonless container runtime"),
        Service("containerd", "containerd", "Container", ("containerd",),
                ("containerd",), None, ("/etc/containerd",),
                description="Container runtime engine"),
        Service("lxc", "LXC", "Container", ("lxc",), ("lxc",), None,
                ("/etc/lxc",), description="System containers"),
    )