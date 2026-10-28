"""Deteksi distribusi dan versi Linux (dibaca dari /etc/os-release)."""
from dataclasses import dataclass
from pathlib import Path

# Kombinasi yang menjadi target dan harus diuji sebelum dinyatakan didukung.
SUPPORTED = {
    ("ubuntu", "24.04"): "Ubuntu Server 24.04 LTS",
    ("debian", "12"): "Debian 12 (bookworm)",
    ("debian", "13"): "Debian 13 (trixie)",
}


@dataclass
class OSInfo:
    id: str
    version_id: str
    pretty_name: str
    codename: str = ""

    @property
    def supported(self) -> bool:
        return (self.id, self.version_id) in SUPPORTED


def parse(text: str) -> OSInfo:
    data = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key] = value.strip().strip('"').strip("'")
    return OSInfo(
        id=data.get("ID", "unknown").lower(),
        version_id=data.get("VERSION_ID", ""),
        pretty_name=data.get("PRETTY_NAME", "Unknown Linux"),
        codename=data.get("VERSION_CODENAME", ""),
    )


def detect(path: str = "/etc/os-release") -> OSInfo:
    p = Path(path)
    if not p.exists():
        return OSInfo("unknown", "", "Unknown Linux")
    return parse(p.read_text())
