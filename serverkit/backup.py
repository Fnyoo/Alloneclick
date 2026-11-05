"""Backup & restore konfigurasi layanan (tar.gz di /var/backups/serverkit)."""
from __future__ import annotations

import time
from pathlib import Path

from . import ui, utils
from .services import SERVICES, Service, parse_selection


def _installed() -> list[Service]:
    return [s for s in SERVICES if utils.pkg_installed(s.packages[0])]


def create_backup(services: list[Service], label: str = "backup") -> Path | None:
    paths = [utils.STATE_DIR]
    for s in services:
        paths.extend(s.config_paths)
    existing = [x for x in dict.fromkeys(paths) if utils.p(x).exists()]
    if not existing:
        ui.warn("Tidak ada file konfigurasi yang ditemukan.")
        return None
    dest_dir = utils.p(utils.BACKUP_DIR)
    dest = dest_dir / f"{label}-{time.strftime('%Y%m%d-%H%M%S')}.tar.gz"
    if utils.DRY_RUN and not utils.PREFIX:
        print(f"[dry-run] tar -czpf {dest} " + " ".join(existing))
        return dest
    dest_dir.mkdir(parents=True, exist_ok=True)
    r = utils.run(["tar", "-czpf", str(dest), "-C", utils.PREFIX or "/",
                   *[x.lstrip("/") for x in existing]])
    if r.returncode != 0:
        ui.error(f"Backup gagal: {r.stdout}")
        return None
    return dest


def backup_menu() -> None:
    pool = _installed()
    if not pool:
        ui.warn("Belum ada layanan terpasang.")
        return
    ui.table("Layanan terpasang", ["No", "Kunci", "Layanan"],
             [(i, s.key, s.name) for i, s in enumerate(pool, 1)])
    raw = ui.ask("Backup layanan (contoh: 1,2 atau all)", "all", width=0)
    try:
        chosen = parse_selection(raw, pool)
    except ValueError as e:
        ui.error(str(e))
        return
    dest = create_backup(chosen)
    if dest:
        ui.ok(f"Backup tersimpan: {dest}")


def restore_menu() -> None:
    d = utils.p(utils.BACKUP_DIR)
    files = sorted(d.glob("*.tar.gz"), reverse=True) if d.exists() else []
    if not files:
        ui.warn(f"Tidak ada arsip backup di {d}")
        return
    ui.table("Arsip backup", ["No", "File", "Ukuran"],
             [(i, f.name, f"{f.stat().st_size / 1024:.1f} KB") for i, f in enumerate(files, 1)])
    n = ui.ask("Nomor arsip yang dipulihkan", None, width=0)
    if not n.isdigit() or not 1 <= int(n) <= len(files):
        ui.error("Nomor tidak valid.")
        return
    archive = files[int(n) - 1]
    ui.warn("Restore akan menimpa file konfigurasi saat ini.")
    if not ui.confirm(f"Pulihkan dari {archive.name}?", default=False):
        return
    snap = create_backup(_installed(), label="pre-restore")
    if snap:
        ui.info(f"Snapshot kondisi saat ini: {snap.name}")
    r = utils.run(["tar", "-xzpf", str(archive), "-C", utils.PREFIX or "/"])
    if r.returncode != 0:
        ui.error(f"Restore gagal: {r.stdout}")
        return
    ui.ok("Restore selesai.")
    if ui.confirm("Restart layanan terkait sekarang?", default=False):
        for s in _installed():
            for u in s.units[:1]:
                if utils.unit_active(u):
                    utils.systemctl("restart", u)
                    ui.ok(f"{u} di-restart")


def menu() -> None:
    ui.section("BACKUP & RESTORE")
    ui.menu([("1", "Backup konfigurasi"), ("2", "Restore dari backup"), ("0", "Kembali")])
    c = input("Select option: ").strip()
    if c == "1":
        backup_menu()
    elif c == "2":
        restore_menu()
