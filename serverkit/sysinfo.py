"""Informasi server."""
from __future__ import annotations

import os
import platform
import shutil
import socket

from . import ui, utils


def _meminfo() -> dict[str, int]:
    data: dict[str, int] = {}
    try:
        for line in open("/proc/meminfo"):
            k, v = line.split(":", 1)
            data[k] = int(v.split()[0])
    except OSError:
        pass
    return data


def _uptime() -> str:
    try:
        secs = int(float(open("/proc/uptime").read().split()[0]))
    except OSError:
        return "-"
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    return f"{d}h {h}j {r // 60}m"


def show() -> None:
    ui.banner("SERVER INFORMATION")
    osr = utils.os_info()
    mem = _meminfo()
    total, free = mem.get("MemTotal", 0), mem.get("MemAvailable", 0)
    disk = shutil.disk_usage("/")
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
    ips = utils.out(["hostname", "-I"]) or utils.detect_primary_ip()
    rows = [
        ("Hostname", socket.gethostname()),
        ("OS", osr.get("PRETTY_NAME", platform.platform())),
        ("Kernel", platform.release()),
        ("Arsitektur", platform.machine()),
        ("CPU", f"{os.cpu_count()} core"),
        ("Load average", " / ".join(f"{x:.2f}" for x in load)),
        ("Memori", f"{(total - free) / 1024:.0f} MB terpakai dari {total / 1024:.0f} MB"),
        ("Disk /", f"{disk.used / 2**30:.1f} GB terpakai dari {disk.total / 2**30:.1f} GB"),
        ("IP address", ips),
        ("Uptime", _uptime()),
        ("Python", platform.python_version()),
    ]
    ui.table("Ringkasan Sistem", ["Item", "Nilai"], rows)
