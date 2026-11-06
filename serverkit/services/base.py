"""Definisi class Service + base class untuk registry per kategori."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Service:
    key: str
    name: str
    category: str
    packages: tuple[str, ...]
    units: tuple[str, ...]
    port: Optional[int] = None
    config_paths: tuple[str, ...] = ()
    check_cmd: Optional[tuple[str, ...]] = None
    conflicts: tuple[str, ...] = ()
    description: str = ""
    external_repo: bool = False


class ServiceCategory:
    """Base class untuk kategori. Setiap subclass mengisi `name` dan `services`."""
    name: str = ""
    services: tuple[Service, ...] = ()

    @classmethod
    def items(cls) -> list[Service]:
        return list(cls.services)