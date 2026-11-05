"""Konfigurator BIND9: membuat named.conf*, zona forward & reverse secara otomatis."""
from __future__ import annotations

import ipaddress
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .. import ui, utils, validators as v

BIND_DIR = "/etc/bind"
ZONE_DIR = f"{BIND_DIR}/zones"
STATE_NAME = "bind9"


@dataclass
class Bind9Config:
    domain: str
    ip: str
    prefix: int
    ns: str
    forwarders: list[str] = field(default_factory=lambda: ["8.8.8.8", "1.1.1.1"])
    records: list[tuple[str, str]] = field(default_factory=list)   # (label, ip)

    # --- turunan
    @property
    def network(self) -> ipaddress.IPv4Network:
        return ipaddress.ip_network(f"{self.ip}/{self.prefix}", strict=False)

    @property
    def octets(self) -> int:
        """Jumlah oktet jaringan untuk zona reverse (disejajarkan ke /8, /16, /24)."""
        return 3 if self.prefix >= 24 else 2 if self.prefix >= 16 else 1

    @property
    def reverse_zone(self) -> str:
        parts = self.ip.split(".")[: self.octets]
        return ".".join(reversed(parts)) + ".in-addr.arpa"

    @property
    def ns_label(self):
        """Label host NS di dalam domain, atau None bila NS berada di luar domain."""
        if self.ns.endswith("." + self.domain):
            return self.ns[: -len(self.domain) - 1]
        return None

    def in_reverse_zone(self, ip: str) -> bool:
        return ip.split(".")[: self.octets] == self.ip.split(".")[: self.octets]

    def ptr_name(self, ip: str) -> str:
        return ".".join(reversed(ip.split(".")[self.octets:]))

    def to_state(self) -> dict:
        return {"domain": self.domain, "ip": self.ip, "prefix": self.prefix, "ns": self.ns,
                "forwarders": self.forwarders, "records": self.records}


# ------------------------------------------------------------------------ renderer
NAMED_CONF = f"""\
// Dikelola oleh SERVERKIT - jangan lupa: perubahan manual bisa tertimpa.
include "{BIND_DIR}/named.conf.options";
include "{BIND_DIR}/named.conf.local";
include "{BIND_DIR}/named.conf.default-zones";
"""


def render_options(cfg: Bind9Config) -> str:
    fwd = "\n".join(f"        {f};" for f in cfg.forwarders)
    return f"""\
// Dikelola oleh SERVERKIT
options {{
    directory "/var/cache/bind";

    listen-on {{ any; }};
    listen-on-v6 {{ any; }};

    allow-query {{ any; }};
    recursion yes;
    allow-recursion {{ localhost; localnets; {cfg.network}; }};

    forwarders {{
{fwd}
    }};

    dnssec-validation auto;
}};
"""


def render_local(cfg: Bind9Config) -> str:
    return f"""\
// Dikelola oleh SERVERKIT
zone "{cfg.domain}" {{
    type master;
    file "{ZONE_DIR}/{cfg.domain}.db";
}};

zone "{cfg.reverse_zone}" {{
    type master;
    file "{ZONE_DIR}/reverse.db";
}};
"""


def _soa(cfg: Bind9Config, serial: str) -> str:
    return f"""\
$TTL    604800
@       IN      SOA     {cfg.ns}. admin.{cfg.domain}. (
                        {serial}   ; Serial
                        604800     ; Refresh
                        86400      ; Retry
                        2419200    ; Expire
                        604800 )   ; Negative Cache TTL
;
"""


def render_forward(cfg: Bind9Config, serial: str) -> str:
    lines = [_soa(cfg, serial), f"@       IN      NS      {cfg.ns}.\n"]
    seen: set[tuple[str, str]] = set()

    def add(label: str, ip: str) -> None:
        if (label, ip) not in seen:
            seen.add((label, ip))
            lines.append(f"{label:<8}IN      A       {ip}\n")

    if cfg.ns_label:
        add(cfg.ns_label, cfg.ip)
    add("@", cfg.ip)
    for label, ip in cfg.records:
        add(label, ip)
    return "".join(lines)


def render_reverse(cfg: Bind9Config, serial: str) -> str:
    lines = [_soa(cfg, serial), f"@       IN      NS      {cfg.ns}.\n"]
    used: set[str] = set()

    def add(ip: str, target: str) -> None:
        if ip in used or not cfg.in_reverse_zone(ip):
            return
        used.add(ip)
        lines.append(f"{cfg.ptr_name(ip):<8}IN      PTR     {target}\n")

    add(cfg.ip, f"{cfg.ns}.")
    for label, ip in cfg.records:
        add(ip, f"{cfg.domain}." if label == "@" else f"{label}.{cfg.domain}.")
    return "".join(lines)


def next_serial(path: Path) -> str:
    """Format YYYYMMDDNN; naik otomatis bila file diubah di hari yang sama."""
    today = time.strftime("%Y%m%d")
    try:
        m = re.search(r"(\d{10})\s*;\s*Serial", path.read_text())
    except OSError:
        m = None
    if m and m.group(1).startswith(today):
        return str(int(m.group(1)) + 1)
    return today + "01"


# ------------------------------------------------------------------------ aksi
def apply(cfg: Bind9Config) -> bool:
    tx = utils.Transaction()
    bind = utils.p(BIND_DIR)
    zones = utils.p(ZONE_DIR)
    fwd = zones / f"{cfg.domain}.db"
    rev = zones / "reverse.db"

    ui.info("Menulis file konfigurasi...")
    tx.write(bind / "named.conf", NAMED_CONF, group="bind")
    tx.write(bind / "named.conf.options", render_options(cfg), group="bind")
    tx.write(bind / "named.conf.local", render_local(cfg), group="bind")
    tx.write(fwd, render_forward(cfg, next_serial(fwd)), group="bind")
    tx.write(rev, render_reverse(cfg, next_serial(rev)), group="bind")

    ui.info("Validasi konfigurasi...")
    checks = [
        ("named-checkconf", ["named-checkconf", f"{BIND_DIR}/named.conf"]),
        (f"zona {cfg.domain}", ["named-checkzone", cfg.domain, f"{ZONE_DIR}/{cfg.domain}.db"]),
        (f"zona {cfg.reverse_zone}", ["named-checkzone", cfg.reverse_zone, f"{ZONE_DIR}/reverse.db"]),
    ]
    for label, cmd in checks:
        r = utils.run(cmd)
        if r.returncode != 0:
            ui.error(f"Validasi gagal: {label}")
            print((r.stdout or r.stderr or "").strip())
            tx.rollback()
            return False
        ui.ok(f"{label}: OK")

    utils.save_state(STATE_NAME, cfg.to_state())
    utils.systemctl("enable", "bind9")
    if not utils.systemctl("restart", "bind9"):
        ui.error("Gagal restart bind9. Cek: journalctl -u bind9 -n 50")
        return False
    ui.ok("Layanan BIND9 berhasil di-restart.")

    r = utils.run(["dig", "+short", f"@127.0.0.1", cfg.domain, "A"])
    if r.returncode == 0 and (r.stdout or "").strip():
        ui.ok(f"Tes dig {cfg.domain} -> {r.stdout.strip()}")
    utils.open_firewall(["53"])
    return True


def configure() -> None:
    ui.banner("BIND9 CONFIGURATION")
    st = utils.load_state(STATE_NAME)

    domain = ui.ask("DNS Domain", st.get("domain"), v.domain)
    ip = ui.ask("Server IP", st.get("ip") or utils.detect_primary_ip(), v.ipv4)
    prefix = int(ui.ask("Network Prefix", str(st.get("prefix", 24)), v.prefix))
    ns_default = st["ns"] if st.get("domain") == domain and st.get("ns") else f"ns1.{domain}"
    ns = ui.ask("DNS Server Name", ns_default, v.domain)
    fwd = ui.ask("Forwarders", ",".join(st.get("forwarders", ["8.8.8.8", "1.1.1.1"])), v.ip_list)

    records: list[tuple[str, str]] = [tuple(r) for r in st.get("records", [])] \
        if st.get("domain") == domain else []
    if records:
        ui.info("Record A tambahan sebelumnya: " + ", ".join(f"{l}={i}" for l, i in records))
        if ui.confirm("Hapus semua record tambahan tersebut?", default=False):
            records = []
    print("\nTambah record A (kosongkan nama host untuk selesai).")
    while True:
        label = ui.ask("  Nama host", None, v.label, allow_empty=True)
        if not label:
            break
        rip = ui.ask("  IP address", None, v.ipv4)
        records.append((label, rip))

    cfg = Bind9Config(domain, ip, prefix, ns, fwd.split(","), records)

    print()
    ui.table("Ringkasan", ["Item", "Nilai"], [
        ("Domain", cfg.domain), ("Server IP", cfg.ip), ("Network", str(cfg.network)),
        ("NS", cfg.ns), ("Forwarders", ", ".join(cfg.forwarders)),
        ("Zona forward", f"{cfg.domain}.db"), ("Zona reverse", f"reverse.db ({cfg.reverse_zone})"),
        ("Record tambahan", ", ".join(f"{l}={i}" for l, i in cfg.records) or "-"),
    ])
    if prefix not in (8, 16, 24):
        ui.warn(f"Prefix /{prefix} tidak sejajar oktet; zona reverse memakai /{cfg.octets * 8}.")
    print()
    if not ui.confirm("Apakah konfigurasi sudah benar?"):
        ui.warn("Dibatalkan.")
        return
    if apply(cfg):
        ui.ok("Konfigurasi BIND9 selesai.")
