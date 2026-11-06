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
    # ================================================================ DNS
    Service("bind9", "BIND9 DNS Server", "DNS",
            ("bind9", "bind9-utils", "dnsutils"),
            ("bind9",), 53, ("/etc/bind",), ("named-checkconf",),
            ("dnsmasq", "unbound", "powerdns"),
            description="Authoritative DNS server"),
    Service("dnsmasq", "dnsmasq", "DNS", ("dnsmasq",), ("dnsmasq",), 53,
            ("/etc/dnsmasq.conf", "/etc/dnsmasq.d"), ("dnsmasq", "--test"),
            ("bind9", "unbound", "powerdns"),
            description="DNS forwarder + DHCP ringan"),
    Service("unbound", "Unbound", "DNS", ("unbound",), ("unbound",), 53,
            ("/etc/unbound",), ("unbound-checkconf",),
            ("bind9", "dnsmasq", "powerdns"),
            description="Recursive/validating DNS resolver"),
    Service("powerdns", "PowerDNS", "DNS", ("pdns-server",), ("pdns",), 53,
            ("/etc/powerdns",), ("pdns_control", "cycle"),
            ("bind9", "dnsmasq", "unbound"), external_repo=True,
            description="DNS server modular"),

    # ================================================================ DHCP
    Service("kea-dhcp4", "Kea DHCPv4", "DHCP", ("kea-dhcp4-server",),
            ("kea-dhcp4-server",), 67, ("/etc/kea",),
            description="DHCP server modern (pengganti ISC DHCP)"),
    Service("isc-dhcp", "ISC DHCP", "DHCP", ("isc-dhcp-server",),
            ("isc-dhcp-server",), 67, ("/etc/dhcp",),
            description="DHCP server klasik (deprecated)"),

    # ================================================================ WEB
    Service("nginx", "Nginx", "Web", ("nginx",), ("nginx",), 80,
            ("/etc/nginx",), ("nginx", "-t"), ("apache2",),
            description="Web server & reverse proxy"),
    Service("apache2", "Apache HTTP Server", "Web", ("apache2",), ("apache2",), 80,
            ("/etc/apache2",), ("apache2ctl", "configtest"), ("nginx",),
            description="Web server klasik"),
    Service("php-fpm", "PHP-FPM 8.3", "Web",
            ("php8.3-fpm", "php8.3-cli", "php8.3-mysql"),
            ("php8.3-fpm",), 9000, ("/etc/php",), ("php-fpm8.3", "-t"),
            description="PHP FastCGI Process Manager"),
    Service("caddy", "Caddy", "Web", ("caddy",), ("caddy",), 80,
            ("/etc/caddy",), ("caddy", "validate", "--config", "/etc/caddy/Caddyfile"),
            ("nginx", "apache2"), external_repo=True,
            description="Web server dengan HTTPS otomatis"),
    Service("lighttpd", "Lighttpd", "Web", ("lighttpd",), ("lighttpd",), 80,
            ("/etc/lighttpd",), ("lighttpd", "-tt", "-f", "/etc/lighttpd/lighttpd.conf"),
            ("nginx", "apache2", "caddy"),
            description="Web server ringan"),
    Service("openlitespeed", "OpenLiteSpeed", "Web", ("openlitespeed",),
            ("lshttpd",), 8088, ("/usr/local/lsws/conf",), external_repo=True,
            description="Web server performa tinggi"),

    # ================================================================ DATABASE
    Service("mariadb", "MariaDB", "Database", ("mariadb-server",), ("mariadb",), 3306,
            ("/etc/mysql",), description="MySQL-compatible RDBMS"),
    Service("mysql", "MySQL", "Database", ("mysql-server",), ("mysql",), 3306,
            ("/etc/mysql",), ("mysqladmin", "ping"),
            description="MySQL (butuh repo Oracle)"),
    Service("postgresql", "PostgreSQL", "Database", ("postgresql",), ("postgresql",), 5432,
            ("/etc/postgresql",), description="Object-relational database"),
    Service("redis", "Redis", "Database", ("redis-server",), ("redis-server",), 6379,
            ("/etc/redis",), ("redis-cli", "ping"),
            description="In-memory key-value store"),
    Service("mongodb", "MongoDB", "Database", ("mongodb-org",), ("mongod",), 27017,
            ("/etc/mongod.conf",), external_repo=True,
            description="Document database (butuh repo MongoDB)"),
    Service("sqlite", "SQLite", "Database", ("sqlite3",), (), None,
            description="Embedded SQL database (tanpa daemon)"),

    # ================================================================ FILE
    Service("samba", "Samba", "File", ("samba",), ("smbd", "nmbd"), 445,
            ("/etc/samba",), ("testparm", "-s"), description="SMB/CIFS file sharing"),
    Service("nfs-kernel-server", "NFS Server", "File", ("nfs-kernel-server",),
            ("nfs-server",), 2049, ("/etc/exports",), description="Network File System"),
    Service("vsftpd", "vsftpd", "File", ("vsftpd",), ("vsftpd",), 21,
            ("/etc/vsftpd.conf",), ("vsftpd", "-t"), description="FTP server ringan"),
    Service("proftpd", "ProFTPD", "File", ("proftpd-basic",), ("proftpd",), 21,
            ("/etc/proftpd",), ("proftpd", "-t"), ("vsftpd",),
            description="FTP server modular"),

    # ================================================================ MAIL
    Service("postfix", "Postfix", "Mail", ("postfix", "mailutils"), ("postfix",), 25,
            ("/etc/postfix",), ("postfix", "check"), description="MTA klasik"),
    Service("dovecot", "Dovecot", "Mail",
            ("dovecot-core", "dovecot-imapd", "dovecot-pop3d"),
            ("dovecot",), 143, ("/etc/dovecot",), ("doveconf", "-n"),
            description="IMAP/POP3 server"),
    Service("exim4", "Exim4", "Mail", ("exim4",), ("exim4",), 25,
            ("/etc/exim4",), ("exim4", "--test"), ("postfix",),
            description="MTA alternatif"),
    Service("rspamd", "Rspamd", "Mail", ("rspamd",), ("rspamd",), 11334,
            ("/etc/rspamd",), ("rspamadm", "configtest"), external_repo=True,
            description="Spam filtering"),
    Service("roundcube", "Roundcube", "Mail", ("roundcube",), ("roundcube",), 80,
            ("/etc/roundcube",), external_repo=True,
            description="Webmail client"),

    # ================================================================ VPN
    Service("wireguard", "WireGuard", "VPN", ("wireguard", "wireguard-tools"),
            ("wg-quick@wg0",), 51820, ("/etc/wireguard",), ("wg", "show"),
            description="VPN modern berbasis kernel"),
    Service("openvpn", "OpenVPN", "VPN", ("openvpn",), ("openvpn@server",), 1194,
            ("/etc/openvpn",), description="VPN TLS-based"),
    Service("strongswan", "StrongSwan", "VPN", ("strongswan",), ("strongswan",), 500,
            ("/etc/ipsec.conf", "/etc/ipsec.d"), ("ipsec", "statusall"),
            description="IPsec VPN"),

    # ================================================================ CONTAINER
    Service("docker", "Docker Engine", "Container", ("docker.io", "docker-compose-v2"),
            ("docker",), None, ("/etc/docker",), ("docker", "info"), external_repo=True,
            description="Container runtime + compose"),
    Service("podman", "Podman", "Container", ("podman",), ("podman",), None,
            ("/etc/containers",), ("podman", "info"),
            description="Daemonless container runtime"),
    Service("containerd", "containerd", "Container", ("containerd",), ("containerd",),
            None, ("/etc/containerd",), description="Container runtime engine"),
    Service("lxc", "LXC", "Container", ("lxc",), ("lxc",), None,
            ("/etc/lxc",), description="System containers"),

    # ================================================================ MONITORING
    Service("prometheus", "Prometheus", "Monitoring", ("prometheus",), ("prometheus",),
            9090, ("/etc/prometheus",),
            ("promtool", "check", "config", "/etc/prometheus/prometheus.yml"),
            description="Metrics collection & TSDB"),
    Service("grafana", "Grafana", "Monitoring", ("grafana",), ("grafana-server",), 3000,
            ("/etc/grafana",), external_repo=True,
            description="Dashboard & visualisasi metrics"),
    Service("netdata", "Netdata", "Monitoring", ("netdata",), ("netdata",), 19999,
            ("/etc/netdata",), external_repo=True,
            description="Real-time monitoring"),
    Service("zabbix", "Zabbix", "Monitoring", ("zabbix-server-mysql",),
            ("zabbix-server",), 10051, ("/etc/zabbix",), external_repo=True,
            description="Enterprise monitoring"),
    Service("node-exporter", "Node Exporter", "Monitoring", ("prometheus-node-exporter",),
            ("prometheus-node-exporter",), 9100, description="Prometheus host metrics"),

    # ================================================================ SECURITY
    Service("ufw", "UFW Firewall", "Security", ("ufw",), ("ufw",), None,
            ("/etc/ufw",), description="Uncomplicated Firewall"),
    Service("fail2ban", "Fail2ban", "Security", ("fail2ban",), ("fail2ban",), None,
            ("/etc/fail2ban",), ("fail2ban-client", "-t"),
            description="Brute-force protection"),
    Service("apparmor", "AppArmor", "Security", ("apparmor", "apparmor-utils"),
            ("apparmor",), None, ("/etc/apparmor.d",),
            description="Mandatory Access Control"),
    Service("suricata", "Suricata", "Security", ("suricata",), ("suricata",), None,
            ("/etc/suricata",), ("suricata", "-T", "-c", "/etc/suricata/suricata.yaml"),
            external_repo=True, description="IDS/IPS"),
    Service("snort", "Snort", "Security", ("snort",), ("snort",), None,
            ("/etc/snort",), ("snort", "-T", "-c", "/etc/snort/snort.conf"),
            external_repo=True, description="IDS klasik"),
    Service("clamav", "ClamAV", "Security", ("clamav", "clamav-daemon"),
            ("clamav-daemon", "clamav-freshclam"), 3310, ("/etc/clamav",),
            description="Antivirus open source"),

    # ================================================================ PROXY
    Service("haproxy", "HAProxy", "Proxy", ("haproxy",), ("haproxy",), 80,
            ("/etc/haproxy",), ("haproxy", "-c", "-f", "/etc/haproxy/haproxy.cfg"),
            description="Load balancer TCP/HTTP"),
    Service("squid", "Squid", "Proxy", ("squid",), ("squid",), 3128,
            ("/etc/squid",), ("squid", "-k", "parse", "/etc/squid/squid.conf"),
            description="Caching HTTP proxy"),
    Service("traefik", "Traefik", "Proxy", ("traefik",), ("traefik",), 80,
            ("/etc/traefik",), external_repo=True,
            description="Reverse proxy modern"),
    Service("cloudflared", "Cloudflared", "Proxy", ("cloudflared",), ("cloudflared",),
            None, ("/etc/cloudflared",), external_repo=True,
            description="Cloudflare Tunnel"),

    # ================================================================ STORAGE & CLOUD
    Service("nextcloud", "Nextcloud", "Storage", ("nextcloud",), ("apache2",), 80,
            ("/etc/nextcloud", "/var/lib/nextcloud"), external_repo=True,
            description="Self-hosted file sync"),
    Service("minio", "MinIO", "Storage", ("minio",), ("minio",), 9000,
            ("/etc/minio",), external_repo=True,
            description="S3-compatible object storage"),
    Service("syncthing", "Syncthing", "Storage", ("syncthing",),
            ("syncthing@syncthing",), 8384, ("/etc/syncthing",), external_repo=True,
            description="Peer-to-peer file sync"),
    Service("rclone", "Rclone", "Storage", ("rclone",), (), None,
            description="Cloud sync CLI (tanpa daemon)"),

    # ================================================================ DEVELOPMENT
    Service("git", "Git", "Development", ("git",), (), None, description="VCS"),
    Service("gitea", "Gitea", "Development", ("gitea",), ("gitea",), 3000,
            ("/etc/gitea",), external_repo=True, description="Git service ringan"),
    Service("jenkins", "Jenkins", "Development", ("jenkins",), ("jenkins",), 8080,
            ("/etc/default/jenkins", "/var/lib/jenkins"), external_repo=True,
            description="CI/CD automation"),
    Service("gitlab-runner", "GitLab Runner", "Development", ("gitlab-runner",),
            ("gitlab-runner",), None, ("/etc/gitlab-runner",), external_repo=True,
            description="Runner CI GitLab"),
    Service("python-env", "Python Environment", "Development",
            ("python3", "python3-pip", "python3-venv"), (), None,
            description="Python + pip + venv"),
    Service("nodejs", "Node.js", "Development", ("nodejs", "npm"), (), None,
            external_repo=True, description="JavaScript runtime + npm"),

    # ================================================================ REMOTE
    Service("openssh-server", "OpenSSH Server", "Remote", ("openssh-server",),
            ("ssh",), 22, ("/etc/ssh",), ("sshd", "-t"),
            description="Remote login SSH"),
    Service("cockpit", "Cockpit", "Remote", ("cockpit",), ("cockpit.socket",), 9090,
            ("/etc/cockpit",), description="Web-based admin UI"),
    Service("webmin", "Webmin", "Remote", ("webmin",), ("webmin",), 10000,
            ("/etc/webmin",), external_repo=True,
            description="Web admin panel klasik"),
    Service("rustdesk", "RustDesk Server", "Remote", ("rustdesk-server",),
            ("rustdesk-hbbs", "rustdesk-hbbr"), None,
            ("/var/lib/rustdesk",), external_repo=True,
            description="Remote desktop relay"),

    # ================================================================ MEDIA
    Service("jellyfin", "Jellyfin", "Media", ("jellyfin",), ("jellyfin",), 8096,
            ("/etc/jellyfin", "/var/lib/jellyfin"), external_repo=True,
            description="Media server open source (fork Emby)"),
    Service("plex", "Plex Media Server", "Media", ("plexmediaserver",),
            ("plexmediaserver",), 32400, ("/etc/plex", "/var/lib/plexmediaserver"),
            external_repo=True, description="Media server komersial"),
    Service("emby", "Emby", "Media", ("emby-server",), ("emby-server",), 8096,
            ("/etc/emby-server", "/var/lib/emby"), external_repo=True,
            description="Media server (fork Jellyfin)"),
    Service("navidrome", "Navidrome", "Media", ("navidrome",), ("navidrome",), 4533,
            ("/etc/navidrome",), external_repo=True,
            description="Music streaming server (Subsonic API)"),
    Service("subsonic", "Subsonic", "Media", ("subsonic",), ("subsonic",), 4040,
            ("/var/subsonic",), external_repo=True,
            description="Music streaming server klasik"),
    Service("audiobookshelf", "Audiobookshelf", "Media", ("audiobookshelf",),
            ("audiobookshelf",), 13378,
            ("/etc/audiobookshelf", "/var/lib/audiobookshelf"), external_repo=True,
            description="Audiobook & podcast server"),
    Service("dlna", "DLNA/UPnP (MiniDLNA)", "Media", ("minidlna",), ("minidlna",), 8200,
            ("/etc/minidlna.conf",), description="DLNA/UPnP media sharing"),
]

BY_KEY = {s.key: s for s in SERVICES}


def categories() -> list[str]:
    """Kategori unik, urut sesuai kemunculan pertama di SERVICES."""
    seen: list[str] = []
    for s in SERVICES:
        if s.category not in seen:
            seen.append(s.category)
    return seen


def by_category() -> dict[str, list[Service]]:
    """Kelompokkan SERVICES per kategori, urutan dipertahankan."""
    out: dict[str, list[Service]] = {}
    for s in SERVICES:
        out.setdefault(s.category, []).append(s)
    return out


def services_in(category: str) -> list[Service]:
    """Layanan di kategori tertentu (case-insensitive)."""
    cat = category.strip().lower()
    return [s for s in SERVICES if s.category.lower() == cat]


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