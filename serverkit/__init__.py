"""Registry layanan — gabungkan semua kategori menjadi satu list SERVICES."""
from __future__ import annotations

from .base import Service, ServiceCategory
from .container import ContainerServices
from .database import DatabaseServices
from .development import DevelopmentServices
from .dhcp import DhcpServices
from .dns import DnsServices
from .filesharing import FileSharingServices
from .mail import MailServices
from .media import MediaServices
from .monitoring import MonitoringServices
from .proxy import ProxyServices
from .remote import RemoteServices
from .security import SecurityServices
from .storage import StorageServices
from .vpn import VpnServices
from .web import WebServices

CATEGORIES: list[type[ServiceCategory]] = [
    WebServices,
    DatabaseServices,
    DnsServices,
    DhcpServices,
    FileSharingServices,
    MailServices,
    VpnServices,
    ContainerServices,
    MonitoringServices,
    SecurityServices,
    ProxyServices,
    StorageServices,
    DevelopmentServices,
    RemoteServices,
    MediaServices,
]

SERVICES: list[Service] = [s for cat in CATEGORIES for s in cat.services]
BY_KEY: dict[str, Service] = {s.key: s for s in SERVICES}


def categories() -> list[str]:
    return [cat.name for cat in CATEGORIES]


def by_category() -> dict[str, list[Service]]:
    return {cat.name: list(cat.services) for cat in CATEGORIES}


def services_in(category: str) -> list[Service]:
    cat = category.strip().lower()
    for c in CATEGORIES:
        if c.name.lower() == cat:
            return list(c.services)
    return []


def parse_selection(raw: str, pool: list[Service]) -> list[Service]:
    """Parse '1,4', '1-3', 'bind9,nginx' atau 'all' terhadap daftar `pool`."""
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