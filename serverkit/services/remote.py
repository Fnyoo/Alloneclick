"""Remote Management: OpenSSH, Cockpit, Webmin, RustDesk."""
from .base import Service, ServiceCategory


class RemoteServices(ServiceCategory):
    name = "Remote"

    services = (
        Service("openssh-server", "OpenSSH Server", "Remote", ("openssh-server",),
                ("ssh",), 22, ("/etc/ssh",), ("sshd", "-t"),
                description="Remote login SSH"),
        Service("cockpit", "Cockpit", "Remote", ("cockpit",),
                ("cockpit.socket",), 9090, ("/etc/cockpit",),
                description="Web-based admin UI"),
        Service("webmin", "Webmin", "Remote", ("webmin",), ("webmin",), 10000,
                ("/etc/webmin",), external_repo=True,
                description="Web admin panel klasik"),
        Service("rustdesk", "RustDesk Server", "Remote", ("rustdesk-server",),
                ("rustdesk-hbbs", "rustdesk-hbbr"), None,
                ("/var/lib/rustdesk",), external_repo=True,
                description="Remote desktop relay"),
    )