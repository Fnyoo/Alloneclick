"""Registry layanan. Nama paket/unit dipilih agar sama di Ubuntu 24.04, Debian 12, dan Debian 13."""
from dataclasses import dataclass, field

from .runner import Runner, validate_package


@dataclass(frozen=True)
class Service:
    key: str
    title: str
    category: str
    packages: tuple
    unit: str = ""
    ports: tuple = ()
    verify_cmds: tuple = field(default_factory=tuple)


REGISTRY = {
    s.key: s
    for s in [
        Service("bind9", "BIND9 DNS Server", "DNS", ("bind9", "bind9-utils", "dnsutils"), "named", (53,), (("named-checkconf",),)),
        Service("dnsmasq", "dnsmasq", "DNS", ("dnsmasq",), "dnsmasq", (53,), (("dnsmasq", "--test"),)),
        Service("unbound", "Unbound", "DNS", ("unbound",), "unbound", (53,), (("unbound-checkconf",),)),
        Service("nginx", "Nginx", "Web", ("nginx",), "nginx", (80,), (("nginx", "-t"),)),
        Service("apache2", "Apache HTTP Server", "Web", ("apache2",), "apache2", (80,), (("apache2ctl", "configtest"),)),
        Service("mariadb", "MariaDB", "Database", ("mariadb-server",), "mariadb", (3306,)),
        Service("postgresql", "PostgreSQL", "Database", ("postgresql",), "postgresql", (5432,)),
        Service("redis", "Redis", "Database", ("redis-server",), "redis-server", (6379,)),
        Service("samba", "Samba", "File", ("samba",), "smbd", (445,)),
    ]
}


def get(key: str) -> Service:
    try:
        return REGISTRY[key.lower()]
    except KeyError:
        raise KeyError(f"Layanan tidak dikenal: {key}. Pilihan: {', '.join(REGISTRY)}")


def is_installed(pkg: str, runner: Runner) -> bool:
    r = runner.run(["dpkg-query", "-W", "-f=${Status}", validate_package(pkg)], mutating=False, check=False)
    return r.ok and "install ok installed" in r.stdout


def listening_ports(runner: Runner) -> set:
    r = runner.run(["ss", "-ltnuH"], mutating=False, check=False)
    ports = set()
    for line in r.stdout.splitlines():
        cols = line.split()
        if len(cols) >= 5 and ":" in cols[4]:
            tail = cols[4].rsplit(":", 1)[1]
            if tail.isdigit():
                ports.add(int(tail))
    return ports


def port_conflicts(s: Service, runner: Runner) -> list:
    busy = listening_ports(runner)
    return [p for p in s.ports if p in busy]


def unit_active(unit: str, runner: Runner) -> bool:
    return runner.run(["systemctl", "is-active", "--quiet", unit], mutating=False, check=False).ok


def verify(s: Service, runner: Runner) -> list:
    """Kembalikan list (label, ok, detail)."""
    out = []
    missing = [p for p in s.packages if not is_installed(p, runner)]
    out.append(("Paket terpasang", not missing, ", ".join(missing) or ", ".join(s.packages)))
    if s.unit:
        out.append((f"systemd: {s.unit}", unit_active(s.unit, runner), "active" if unit_active(s.unit, runner) else "tidak aktif"))
    for cmd in s.verify_cmds:
        r = runner.run(list(cmd), mutating=False, check=False)
        out.append((" ".join(cmd), r.ok, (r.stderr or r.stdout).strip()[:120] or "OK"))
    if s.ports:
        busy = listening_ports(runner)
        for p in s.ports:
            out.append((f"port {p} listening", p in busy, ""))
    return out
