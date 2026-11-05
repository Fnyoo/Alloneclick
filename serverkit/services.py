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


SERVICES: list[Service] = [
    Service("bind9", "BIND9 DNS Server", "DNS", ("bind9", "bind9-utils", "dnsutils"),
            ("bind9",), 53, ("/etc/bind",), ("named-checkconf",), ("dnsmasq", "unbound")),
    Service("dnsmasq", "dnsmasq", "DNS", ("dnsmasq",), ("dnsmasq",), 53,
            ("/etc/dnsmasq.conf", "/etc/dnsmasq.d"), ("dnsmasq", "--test"), ("bind9", "unbound")),
    Service("unbound", "Unbound", "DNS", ("unbound",), ("unbound",), 53,
            ("/etc/unbound",), ("unbound-checkconf",), ("bind9", "dnsmasq")),
    Service("nginx", "Nginx", "Web", ("nginx",), ("nginx",), 80,
            ("/etc/nginx",), ("nginx", "-t"), ("apache2",)),
    Service("apache2", "Apache HTTP Server", "Web", ("apache2",), ("apache2",), 80,
            ("/etc/apache2",), ("apache2ctl", "configtest"), ("nginx",)),
    Service("mariadb", "MariaDB", "Database", ("mariadb-server",), ("mariadb",), 3306,
            ("/etc/mysql",)),
    Service("postgresql", "PostgreSQL", "Database", ("postgresql",), ("postgresql",), 5432,
            ("/etc/postgresql",)),
    Service("redis", "Redis", "Database", ("redis-server",), ("redis-server",), 6379,
            ("/etc/redis",), ("redis-cli", "ping")),
    Service("samba", "Samba", "File", ("samba",), ("smbd", "nmbd"), 445,
            ("/etc/samba",), ("testparm", "-s")),
]

BY_KEY = {s.key: s for s in SERVICES}


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
