"""Registry layanan yang didukung. Tambah layanan baru cukup menambah satu entri."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Service:
    key: str
    name: str
    category: str
    packages: tuple[str, ...]
    units: tuple[str, ...]                 # unit systemd (yang pertama = utama)
    port: Optional[int] = None             # port TCP untuk verifikasi
    config_paths: tuple[str, ...] = ()     # dipakai fitur backup
    check_cmd: Optional[tuple[str, ...]] = None  # validasi konfigurasi
    conflicts: tuple[str, ...] = ()        # bentrok port
    description: str = ""                  # ringkasan singkat
    external_repo: bool = False            # butuh repo vendor (docker, caddy, dll.)


SERVICES: list[Service] = [
    # ---------------------------------------------------------------- DNS
    Service("bind9", "BIND9 DNS Server", "DNS", ("bind9", "bind9-utils", "dnsutils"),
            ("bind9",), 53, ("/etc/bind",), ("named-checkconf",), ("dnsmasq", "unbound"),
            description="Authoritative DNS server"),
    Service("dnsmasq", "dnsmasq", "DNS", ("dnsmasq",), ("dnsmasq",), 53,
            ("/etc/dnsmasq.conf", "/etc/dnsmasq.d"), ("dnsmasq", "--test"),
            ("bind9", "unbound"), description="DNS forwarder + DHCP ringan"),
    Service("unbound", "Unbound", "DNS", ("unbound",), ("unbound",), 53,
            ("/etc/unbound",), ("unbound-checkconf",), ("bind9", "dnsmasq"),
            description="Recursive/validating DNS resolver"),

    # ---------------------------------------------------------------- DHCP
    Service("kea-dhcp4", "Kea DHCPv4", "DHCP", ("kea-dhcp4-server",),
            ("kea-dhcp4-server",), 67, ("/etc/kea",),
            description="DHCP server modern (pengganti ISC DHCP)"),

    # ---------------------------------------------------------------- Web
    Service("nginx", "Nginx", "Web", ("nginx",), ("nginx",), 80,
            ("/etc/nginx",), ("nginx", "-t"), ("apache2",),
            description="Web server & reverse proxy"),
    Service("apache2", "Apache HTTP Server", "Web", ("apache2",), ("apache2",), 80,
            ("/etc/apache2",), ("apache2ctl", "configtest"), ("nginx",),
            description="Web server klasik"),
    Service("php-fpm", "PHP-FPM 8.3", "Web", ("php8.3-fpm", "php8.3-cli", "php8.3-mysql"),
            ("php8.3-fpm",), 9000, ("/etc/php",), ("php-fpm8.3", "-t"),
            description="PHP FastCGI Process Manager"),
    Service("caddy", "Caddy", "Web", ("caddy",), ("caddy",), 80,
            ("/etc/caddy",), ("caddy", "validate", "--config", "/etc/caddy/Caddyfile"),
            ("nginx", "apache2"), external_repo=True,
            description="Web server dengan HTTPS otomatis"),

    # ---------------------------------------------------------------- Database
    Service("mariadb", "MariaDB", "Database", ("mariadb-server",), ("mariadb",), 3306,
            ("/etc/mysql",), description="MySQL-compatible RDBMS"),
    Service("postgresql", "PostgreSQL", "Database", ("postgresql",), ("postgresql",), 5432,
            ("/etc/postgresql",), description="Object-relational database"),
    Service("redis", "Redis", "Database", ("redis-server",), ("redis-server",), 6379,
            ("/etc/redis",), ("redis-cli", "ping"), description="In-memory key-value store"),
    Service("mongodb", "MongoDB", "Database", ("mongodb-org",), ("mongod",), 27017,
            ("/etc/mongod.conf",), external_repo=True,
            description="Document database (butuh repo MongoDB)"),

    # ---------------------------------------------------------------- File
    Service("samba", "Samba", "File", ("samba",), ("smbd", "nmbd"), 445,
            ("/etc/samba",), ("testparm", "-s"), description="SMB/CIFS file sharing"),
    Service("nfs-kernel-server", "NFS Server", "File", ("nfs-kernel-server",),
            ("nfs-server",), 2049, ("/etc/exports",), description="Network File System"),
    Service("vsftpd", "vsftpd", "File", ("vsftpd",), ("vsftpd",), 21,
            ("/etc/vsftpd.conf",), ("vsftpd", "-t"), description="FTP server ringan"),

    # ---------------------------------------------------------------- Mail
    Service("postfix", "Postfix", "Mail", ("postfix", "mailutils"), ("postfix",), 25,
            ("/etc/postfix",), ("postfix", "check"), description="MTA klasik"),
    Service("dovecot", "Dovecot", "Mail", ("dovecot-core", "dovecot-imapd", "dovecot-pop3d"),
            ("dovecot",), 143, ("/etc/dovecot",), ("doveconf", "-n"),
            description="IMAP/POP3 server"),

    # ---------------------------------------------------------------- VPN
    Service("wireguard", "WireGuard", "VPN", ("wireguard", "wireguard-tools"),
            ("wg-quick@wg0",), 51820, ("/etc/wireguard",), ("wg", "show"),
            description="VPN modern berbasis kernel"),
    Service("openvpn", "OpenVPN", "VPN", ("openvpn",), ("openvpn@server",), 1194,
            ("/etc/openvpn",), description="VPN TLS-based"),

    # ---------------------------------------------------------------- Container
    Service("docker", "Docker Engine", "Container", ("docker.io", "docker-compose-v2"),
            ("docker",), None, ("/etc/docker",), ("docker", "info"), external_repo=True,
            description="Container runtime + compose"),
    Service("podman", "Podman", "Container", ("podman",), ("podman",), None,
            ("/etc/containers",), ("podman", "info"),
            description="Daemonless container runtime"),
    Service("containerd", "containerd", "Container", ("containerd",), ("containerd",),
            None, ("/etc/containerd",), description="Container runtime engine"),

    # ---------------------------------------------------------------- Monitoring
    Service("prometheus", "Prometheus", "Monitoring", ("prometheus",), ("prometheus",),
            9090, ("/etc/prometheus",), ("promtool", "check", "config", "/etc/prometheus/prometheus.yml"),
            description="Metrics collection & TSDB"),
    Service("grafana", "Grafana", "Monitoring", ("grafana",), ("grafana-server",), 3000,
            ("/etc/grafana",), external_repo=True,
            description="Dashboard & visualisasi metrics"),
    Service("netdata", "Netdata", "Monitoring", ("netdata",), ("netdata",), 19999,
            ("/etc/netdata",), external_repo=True,
            description="Real-time monitoring"),
    Service("node-exporter", "Node Exporter", "Monitoring", ("prometheus-node-exporter",),
            ("prometheus-node-exporter",), 9100, description="Prometheus host metrics"),

    # ---------------------------------------------------------------- Security
    Service("ufw", "UFW Firewall", "Security", ("ufw",), ("ufw",), None,
            ("/etc/ufw",), description="Uncomplicated Firewall"),
    Service("fail2ban", "Fail2ban", "Security", ("fail2ban",), ("fail2ban",), None,
            ("/etc/fail2ban",), ("fail2ban-client", "-t"),
            description="Brute-force protection"),
    Service("clamav", "ClamAV", "Security", ("clamav", "clamav-daemon"),
            ("clamav-daemon", "clamav-freshclam"), 3310, ("/etc/clamav",),
            description="Antivirus open source"),

    # ---------------------------------------------------------------- Proxy
    Service("haproxy", "HAProxy", "Proxy", ("haproxy",), ("haproxy",), 80,
            ("/etc/haproxy",), ("haproxy", "-c", "-f", "/etc/haproxy/haproxy.cfg"),
            description="Load balancer TCP/HTTP"),
    Service("squid", "Squid", "Proxy", ("squid",), ("squid",), 3128,
            ("/etc/squid",), ("squid", "-k", "parse", "/etc/squid/squid.conf"),
            description="Caching HTTP proxy"),

    # ---------------------------------------------------------------- Storage & Cloud
    Service("nextcloud", "Nextcloud", "Storage", ("nextcloud",), ("apache2",), 80,
            ("/etc/nextcloud", "/var/lib/nextcloud"), external_repo=True,
            description="Self-hosted file sync"),
    Service("minio", "MinIO", "Storage", ("minio",), ("minio",), 9000,
            ("/etc/minio",), external_repo=True,
            description="S3-compatible object storage"),
    Service("syncthing", "Syncthing", "Storage", ("syncthing",), ("syncthing@syncthing",),
            8384, ("/etc/syncthing",), external_repo=True,
            description="Peer-to-peer file sync"),

    # ---------------------------------------------------------------- Dev
    Service("git", "Git", "Development", ("git",), (), None, description="VCS"),
    Service("gitea", "Gitea", "Development", ("gitea",), ("gitea",), 3000,
            ("/etc/gitea",), external_repo=True, description="Git service ringan"),
    Service("jenkins", "Jenkins", "Development", ("jenkins",), ("jenkins",), 8080,
            ("/etc/default/jenkins", "/var/lib/jenkins"), external_repo=True,
            description="CI/CD automation"),

    # ---------------------------------------------------------------- Remote
    Service("openssh-server", "OpenSSH Server", "Remote", ("openssh-server",),
            ("ssh",), 22, ("/etc/ssh",), ("sshd", "-t"),
            description="Remote login SSH"),
    Service("cockpit", "Cockpit", "Remote", ("cockpit",), ("cockpit.socket",), 9090,
            ("/etc/cockpit",), description="Web-based admin UI"),
]

BY_KEY = {s.key: s for s in SERVICES}


def categories() -> list[str]:
    """Kategori unik, urut sesuai kemunculan pertama."""
    seen: list[str] = []
    for s in SERVICES:
        if s.category not in seen:
            seen.append(s.category)
    return seen


def by_category() -> dict[str, list[Service]]:
    out: dict[str, list[Service]] = {}
    for s in SERVICES:
        out.setdefault(s.category, []).append(s)
    return out


def parse_selection(raw: str, pool: list[Service]) -> list[Service]:
    """Parse '1,4', '1-3', 'bind9,nginx' atau 'all' terhadap daftar `pool` (nomor = urutan di pool)."""
    raw = raw.strip().lower()
    if raw in ("all", "semua", "*"):
        return list(pool)
    chosen: list[Service] = []
    for token in raw.replace(" ", ",").split(","):
        if not token:
            continue
        if "-" in token and all(p.isdigit() for p in token.split("-", 1)):
            a, b = (int(x) for x in token.split("-", 1))
            idxs = range(a, b + 1)
        elif token.isdigit():
            idxs = [int(token)]
        else:
            match = [s for s in pool if s.key == token]
            if not match:
                raise ValueError(f"Layanan tidak dikenal: '{token}'")
            idxs = None
            svc = match[0]
            if svc not in chosen:
                chosen.append(svc)
        if idxs is not None:
            for i in idxs:
                if not 1 <= i <= len(pool):
                    raise ValueError(f"Nomor di luar daftar: {i}")
                if pool[i - 1] not in chosen:
                    chosen.append(pool[i - 1])
    if not chosen:
        raise ValueError("Tidak ada layanan yang dipilih")
    return chosen