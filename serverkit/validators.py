"""Validator input. Setiap validator mengembalikan nilai bersih atau raise ValueError."""
import ipaddress
import re

_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_LABEL_RE = re.compile(r"^(@|[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)$")


def domain(value: str) -> str:
    value = value.strip().lower().rstrip(".")
    if not _DOMAIN_RE.match(value):
        raise ValueError("Format domain tidak valid (contoh: dinfor.com)")
    return value


def ipv4(value: str) -> str:
    try:
        return str(ipaddress.IPv4Address(value.strip()))
    except ValueError:
        raise ValueError("Alamat IPv4 tidak valid (contoh: 192.168.100.5)")


def prefix(value: str) -> str:
    try:
        n = int(value)
    except ValueError:
        raise ValueError("Prefix harus berupa angka")
    if not 8 <= n <= 30:
        raise ValueError("Prefix harus antara 8 dan 30")
    return str(n)


def label(value: str) -> str:
    value = value.strip().lower()
    if not _LABEL_RE.match(value):
        raise ValueError("Nama host tidak valid (huruf kecil, angka, '-')")
    return value


def ip_list(value: str) -> str:
    items = [v.strip() for v in value.replace(" ", ",").split(",") if v.strip()]
    if not items:
        raise ValueError("Minimal satu IP")
    return ",".join(ipv4(i) for i in items)


def port(value: str) -> str:
    try:
        n = int(value)
    except ValueError:
        raise ValueError("Port harus berupa angka")
    if not 1 <= n <= 65535:
        raise ValueError("Port 1-65535")
    return str(n)
