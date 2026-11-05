"""Utilitas sistem: eksekusi perintah, apt, systemd, penulisan file aman (dengan backup & rollback).

Variabel lingkungan untuk pengujian:
  SERVERKIT_DRY_RUN=1       -> perintah sistem hanya dicetak, tidak dijalankan
  SERVERKIT_PREFIX=/tmp/x   -> semua file konfigurasi ditulis di bawah prefix tersebut
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

from . import ui

DRY_RUN = os.environ.get("SERVERKIT_DRY_RUN") == "1"
PREFIX = os.environ.get("SERVERKIT_PREFIX", "")

STATE_DIR = "/etc/serverkit"
BACKUP_DIR = "/var/backups/serverkit"


def p(path: str) -> Path:
    """Path absolut dengan dukungan PREFIX (untuk pengujian)."""
    return Path(PREFIX + path)


# --------------------------------------------------------------------------- sistem
def require_root() -> None:
    if DRY_RUN or PREFIX:
        return
    if os.geteuid() != 0:
        ui.error("SERVERKIT harus dijalankan sebagai root. Gunakan: sudo python3 -m serverkit")
        sys.exit(1)


def os_info() -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                data[k] = v.strip().strip('"')
    except OSError:
        pass
    return data


def check_supported_os() -> None:
    info = os_info()
    ids = {info.get("ID", ""), *info.get("ID_LIKE", "").split()}
    if not ids & {"debian", "ubuntu"}:
        ui.warn(f"OS '{info.get('PRETTY_NAME', 'tidak diketahui')}' bukan Debian/Ubuntu. "
                "Fitur instalasi (apt) mungkin tidak berfungsi.")


def run(cmd: Sequence[str], check: bool = False, stream: bool = False,
        env_extra: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Jalankan perintah. stream=True menampilkan output langsung ke terminal."""
    if DRY_RUN:
        print(ui._c("[dry-run] ", "35") + " ".join(cmd))
        return subprocess.CompletedProcess(list(cmd), 0, "", "")
    env = {**os.environ, **(env_extra or {})}
    try:
        if stream:
            return subprocess.run(list(cmd), check=check, env=env)
        return subprocess.run(list(cmd), check=check, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        return subprocess.CompletedProcess(list(cmd), 127, "", f"perintah tidak ditemukan: {cmd[0]}")


def out(cmd: Sequence[str]) -> str:
    r = run(cmd)
    return (r.stdout or "").strip()


# --------------------------------------------------------------------------- apt
_APT_ENV = {"DEBIAN_FRONTEND": "noninteractive"}


def apt_update() -> bool:
    return run(["apt-get", "update"], stream=True, env_extra=_APT_ENV).returncode == 0


def apt_install(pkgs: Sequence[str]) -> bool:
    return run(["apt-get", "install", "-y", *pkgs], stream=True, env_extra=_APT_ENV).returncode == 0


def apt_upgrade(pkgs: Sequence[str]) -> bool:
    return run(["apt-get", "install", "-y", "--only-upgrade", *pkgs],
               stream=True, env_extra=_APT_ENV).returncode == 0


def apt_remove(pkgs: Sequence[str], purge: bool = False) -> bool:
    verb = "purge" if purge else "remove"
    return run(["apt-get", verb, "-y", *pkgs], stream=True, env_extra=_APT_ENV).returncode == 0


def apt_autoremove() -> None:
    run(["apt-get", "autoremove", "-y"], stream=True, env_extra=_APT_ENV)


def pkg_installed(pkg: str) -> bool:
    r = run(["dpkg-query", "-W", "-f=${Status}", pkg])
    return r.returncode == 0 and "install ok installed" in (r.stdout or "")


# --------------------------------------------------------------------------- systemd
def unit_active(unit: str) -> bool:
    return run(["systemctl", "is-active", "--quiet", unit]).returncode == 0


def unit_enabled(unit: str) -> bool:
    return run(["systemctl", "is-enabled", "--quiet", unit]).returncode == 0


def systemctl(action: str, unit: str) -> bool:
    return run(["systemctl", action, unit]).returncode == 0


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def open_firewall(rules: Sequence[str]) -> None:
    """Jika ufw aktif, tawarkan membuka port/profil. rules: ['53', 'Nginx Full']."""
    if not shutil.which("ufw"):
        return
    if "Status: active" not in out(["ufw", "status"]):
        return
    if ui.confirm(f"UFW aktif. Buka akses untuk {', '.join(rules)}?"):
        for rule in rules:
            run(["ufw", "allow", rule])


# --------------------------------------------------------------------------- file
class Transaction:
    """Tulis beberapa file sekaligus; bisa di-rollback jika validasi gagal."""

    def __init__(self) -> None:
        self._items: list[tuple[Path, Optional[bytes]]] = []
        self._stamp = time.strftime("%Y%m%d-%H%M%S")

    def write(self, path: Path, content: str, mode: int = 0o644,
              group: Optional[str] = None) -> None:
        path = Path(path)
        if DRY_RUN and not PREFIX:
            print(ui._c("[dry-run] ", "35") + f"tulis {path} ({len(content)} byte)")
            return
        old = path.read_bytes() if path.exists() else None
        if old is not None:
            bak = p(f"{BACKUP_DIR}/files/{self._stamp}") / str(path).lstrip("/")
            bak.parent.mkdir(parents=True, exist_ok=True)
            bak.write_bytes(old)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        os.chmod(path, mode)
        if group and not PREFIX:
            try:
                shutil.chown(path, user="root", group=group)
            except (LookupError, PermissionError):
                pass
        self._items.append((path, old))

    def rollback(self) -> None:
        for path, old in reversed(self._items):
            if old is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(old)
        self._items.clear()
        ui.warn("Perubahan dibatalkan; file lama dikembalikan.")


def load_state(name: str) -> dict:
    import json
    f = p(f"{STATE_DIR}/{name}.json")
    try:
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return {}


def save_state(name: str, data: dict) -> None:
    import json
    if DRY_RUN and not PREFIX:
        return
    f = p(f"{STATE_DIR}/{name}.json")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2))


def detect_primary_ip() -> str:
    """IP lokal utama (tanpa mengirim paket)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
