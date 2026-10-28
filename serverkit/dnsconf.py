"""Konfigurasi BIND9: zona forward + reverse (IPv4).

Semua input divalidasi sebelum masuk template, jadi isi file zona tidak bisa
disisipi baris/direktif lain. Bekerja sama di Ubuntu 24.04, Debian 12, dan Debian 13
(path /etc/bind, unit `named`, `type primary` didukung BIND 9.18 dan 9.20).
"""
import ipaddress
import re
import shutil
import tarfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, StrictUndefined

LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
DOMAIN_RE = re.compile(rf"^{LABEL}(?:\.{LABEL})+$")
LABEL_RE = re.compile(rf"^{LABEL}$")

BEGIN = "// BEGIN serverkit zone {name}"
END = "// END serverkit zone {name}"

_env = Environment(undefined=StrictUndefined, keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True)

FORWARD_TMPL = _env.from_string("""\
$TTL {{ ttl }}
@ IN SOA {{ ns_fqdn }}. hostmaster.{{ domain }}. (
        {{ serial }} ; serial
        3600 ; refresh
        900 ; retry
        604800 ; expire
        300 ) ; negative cache TTL
@ IN NS {{ ns_fqdn }}.
{% for name, ip in records %}
{{ name }} IN A {{ ip }}
{% endfor %}
""")

REVERSE_TMPL = _env.from_string("""\
$TTL {{ ttl }}
@ IN SOA {{ ns_fqdn }}. hostmaster.{{ domain }}. (
        {{ serial }} ; serial
        3600 ; refresh
        900 ; retry
        604800 ; expire
        300 ) ; negative cache TTL
@ IN NS {{ ns_fqdn }}.
{% for owner, target in ptrs %}
{{ owner }} IN PTR {{ target }}.
{% endfor %}
""")

OPTIONS_TMPL = _env.from_string("""\
// Dibuat oleh ServerKit. Konfigurasi sebelumnya ada di backup /var/backups/serverkit.
options {
    directory "/var/cache/bind";
    listen-on { 127.0.0.1; {{ ip }}; };
    listen-on-v6 { none; };
    allow-query { localhost; {{ network }}; };
    recursion yes;
    allow-recursion { localhost; {{ network }}; };
{% if forwarders %}
    forwarders { {% for f in forwarders %}{{ f }}; {% endfor %}};
    forward first;
{% endif %}
    dnssec-validation auto;
};
""")

ZONE_BLOCK_TMPL = _env.from_string("""\
{{ begin }}
zone "{{ name }}" {
    type primary;
    file "{{ path }}";
    allow-transfer { none; };
};
{{ end }}
""")


@dataclass
class DnsConfig:
    domain: str
    ip: str
    hostname: str
    network: str
    forwarders: tuple
    records: tuple  # ((nama, ip), ...) — nama server selalu pertama
    ttl: int = 3600

    @classmethod
    def build(cls, domain, ip, hostname="ns1", network=None, forwarders="", records=None, ttl=3600):
        domain = (domain or "").strip().lower().rstrip(".")
        if len(domain) > 253 or not DOMAIN_RE.match(domain):
            raise ValueError(f"Domain tidak valid: {domain!r} (contoh: lab.lan)")
        hostname = (hostname or "").strip().lower()
        if not LABEL_RE.match(hostname):
            raise ValueError(f"Hostname DNS tidak valid: {hostname!r}")
        try:
            addr = ipaddress.IPv4Address((ip or "").strip())
        except ValueError:
            raise ValueError(f"IP server harus IPv4 yang valid: {ip!r}")
        try:
            net = ipaddress.IPv4Network((network or f"{addr}/24").strip(), strict=False)
        except ValueError:
            raise ValueError(f"Jaringan tidak valid: {network!r} (contoh: 192.168.1.0/24)")
        if net.prefixlen not in (8, 16, 24):
            raise ValueError("Prefix jaringan harus /8, /16, atau /24 (batas zona reverse klasik).")
        if addr not in net:
            raise ValueError(f"IP server {addr} tidak berada di jaringan {net}.")
        fw = []
        for item in (forwarders or "").split(","):
            item = item.strip()
            if not item:
                continue
            try:
                fw.append(str(ipaddress.ip_address(item)))
            except ValueError:
                raise ValueError(f"Forwarder tidak valid: {item!r}")
        recs = {hostname: str(addr)}
        for raw in records or []:
            name, sep, rip = raw.partition("=")
            name = name.strip().lower()
            if not sep or (name != "@" and not LABEL_RE.match(name)):
                raise ValueError(f"Format record salah: {raw!r} (gunakan nama=ip, mis. www=192.168.1.20)")
            try:
                recs[name] = str(ipaddress.IPv4Address(rip.strip()))
            except ValueError:
                raise ValueError(f"IP record tidak valid: {raw!r}")
        if not 60 <= int(ttl) <= 86400:
            raise ValueError("TTL harus antara 60 dan 86400 detik.")
        return cls(domain, str(addr), hostname, str(net), tuple(fw), tuple(recs.items()), int(ttl))

    @property
    def ns_fqdn(self) -> str:
        return f"{self.hostname}.{self.domain}"

    @property
    def reverse_zone(self) -> str:
        net = ipaddress.IPv4Network(self.network)
        parts = str(net.network_address).split(".")[: net.prefixlen // 8]
        return ".".join(reversed(parts)) + ".in-addr.arpa"

    def fqdn(self, name: str) -> str:
        return self.domain if name == "@" else f"{name}.{self.domain}"

    @property
    def ptrs(self) -> tuple:
        """(owner, target-fqdn) untuk IP yang berada di jaringan; satu PTR per IP."""
        net = ipaddress.IPv4Network(self.network)
        seen, out = set(), []
        for name, ip in self.records:
            addr = ipaddress.IPv4Address(ip)
            if addr not in net or ip in seen:
                continue
            seen.add(ip)
            owner = addr.reverse_pointer[: -(len(self.reverse_zone) + 1)]
            out.append((owner, self.fqdn(name)))
        return tuple(out)


def next_serial(existing: str, today: date = None) -> int:
    base = int((today or date.today()).strftime("%Y%m%d")) * 100
    m = re.search(r"(\d{10})\s*;\s*serial", existing or "")
    if m and int(m.group(1)) >= base:
        return int(m.group(1)) + 1
    return base


def update_zone_blocks(local_text: str, cfg: DnsConfig, bind_dir: Path) -> str:
    """Ganti/tambah blok zona milik ServerKit di named.conf.local (idempoten)."""
    text = local_text
    zones = {
        cfg.domain: bind_dir / "zones" / f"db.{cfg.domain}",
        cfg.reverse_zone: bind_dir / "zones" / f"db.{cfg.reverse_zone}",
    }
    for name in zones:
        pattern = re.escape(BEGIN.format(name=name)) + r"\n.*?" + re.escape(END.format(name=name)) + r"\n?"
        text = re.sub(pattern, "", text, flags=re.DOTALL)
        if re.search(rf'zone\s+"{re.escape(name)}"', text):
            raise ValueError(f'Zona "{name}" sudah didefinisikan di luar ServerKit; hapus/ubah manual dulu.')
    if text and not text.endswith("\n"):
        text += "\n"
    for name, path in zones.items():
        text += ZONE_BLOCK_TMPL.render(begin=BEGIN.format(name=name), end=END.format(name=name), name=name, path=path)
    return text


def build_plan(cfg: DnsConfig, bind_dir="/etc/bind", today: date = None) -> dict:
    """Hasilkan {path: isi} untuk semua file yang akan ditulis. Tidak menulis apa pun."""
    bind = Path(bind_dir)
    read = lambda p: p.read_text() if p.exists() else ""
    fwd = bind / "zones" / f"db.{cfg.domain}"
    rev = bind / "zones" / f"db.{cfg.reverse_zone}"
    common = dict(ttl=cfg.ttl, ns_fqdn=cfg.ns_fqdn, domain=cfg.domain)
    local = bind / "named.conf.local"
    return {
        fwd: FORWARD_TMPL.render(serial=next_serial(read(fwd), today), records=cfg.records, **common),
        rev: REVERSE_TMPL.render(serial=next_serial(read(rev), today), ptrs=cfg.ptrs, **common),
        local: update_zone_blocks(read(local), cfg, bind),
        bind / "named.conf.options": OPTIONS_TMPL.render(ip=cfg.ip, network=cfg.network, forwarders=cfg.forwarders),
    }


    try:
        shutil.chown(path, user="root", group="bind")
    except (LookupError, OSError):
        pass


def write_plan(plan: dict, bind_dir="/etc/bind", backup_dir="/var/backups/serverkit", now: datetime = None):
    """Backup /etc/bind, tulis file, kembalikan (path_backup, fungsi_rollback)."""
    bind, backup = Path(bind_dir), Path(backup_dir)
    backup.mkdir(parents=True, exist_ok=True)
    archive = backup / f"bind-{(now or datetime.now()).strftime('%Y%m%d-%H%M%S')}.tar.gz"
    if bind.exists():
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(bind, arcname="bind")
    originals = {p: (p.read_bytes() if p.exists() else None) for p in plan}
    (bind / "zones").mkdir(parents=True, exist_ok=True)
    (bind / "zones").chmod(0o755)
    _chown(bind / "zones")
    for path, text in plan.items():
        path.write_text(text)
        path.chmod(0o644)
        _chown(path)

    def rollback():
        for p, data in originals.items():
            if data is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(data)

    return archive, rollback


def validation_commands(cfg: DnsConfig, bind_dir="/etc/bind") -> list:
    bind = Path(bind_dir)
    return [
        ["named-checkconf"],
        ["named-checkzone", cfg.domain, str(bind / "zones" / f"db.{cfg.domain}")],
        ["named-checkzone", cfg.reverse_zone, str(bind / "zones" / f"db.{cfg.reverse_zone}")],
    ]


def parse_a_records(zone_text: str) -> list:
    return re.findall(r"^(\S+)\s+IN\s+A\s+(\S+)\s*$", zone_text, flags=re.MULTILINE)


def check_dns(domain: str, runner, bind_dir="/etc/bind", server="127.0.0.1") -> list:
    """Uji forward & reverse lewat dig terhadap server lokal. Return [(label, ok, detail)]."""
    zdir = Path(bind_dir) / "zones"
    fwd = zdir / f"db.{domain}"
    if not fwd.exists():
        raise FileNotFoundError(f"File zona tidak ditemukan: {fwd}")
    rev_zones = [p.name[3:] for p in zdir.glob("db.*.in-addr.arpa")]
    results = []
    for name, ip in parse_a_records(fwd.read_text()):
        fq = domain if name == "@" else f"{name}.{domain}"
        r = runner.run(["dig", "+short", "+time=2", "+tries=1", f"@{server}", fq, "A"], mutating=False, check=False)
        got = set(r.stdout.split())
        results.append((f"A {fq}", ip in got, ", ".join(sorted(got)) or (r.stderr.strip() or "tidak ada jawaban")))
        rp = ipaddress.IPv4Address(ip).reverse_pointer
        if any(rp.endswith("." + z) for z in rev_zones):
            r = runner.run(["dig", "+short", "+time=2", "+tries=1", f"@{server}", "-x", ip], mutating=False, check=False)
            got = set(r.stdout.split())
            results.append((f"PTR {ip}", (fq + ".") in got, ", ".join(sorted(got)) or "tidak ada jawaban"))
    return results
