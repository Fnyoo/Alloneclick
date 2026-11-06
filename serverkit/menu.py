"""Menu utama SERVERKIT."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from . import __version__, backup, netdiag, sysinfo, ui, utils
from .configurators import CONFIGURATORS
from .services import SERVICES, Service, parse_selection


# ------------------------------------------------------------------ helper umum
def status_of(s: Service) -> str:
    if not utils.pkg_installed(s.packages[0]):
        return "-"
    if not s.units:
        return "paket"
    return "aktif" if utils.unit_active(s.units[0]) else "terpasang"

def show_services(title: str, pool: list[Service], with_status: bool = True) -> None:
    rows = []
    for i, s in enumerate(pool, 1):
        pkg = ",\n".join(s.packages) if len(s.packages) > 1 else s.packages[0]
        flag = " *" if s.external_repo else ""
        row = [i, s.key, s.name + flag, s.category, pkg]
        if with_status:
            row.append(status_of(s))
        rows.append(row)
    cols = ["No", "Kunci", "Layanan", "Kategori", "Paket"] + (["Status"] if with_status else [])
    ui.table(title, cols, rows)
    if any(s.external_repo for s in pool):
        ui.info("* = butuh repository vendor (mis. Docker, Caddy, Grafana). "
                "Pastikan repo sudah ditambahkan sebelum instalasi.")


def installed_pool() -> list[Service]:
    return [s for s in SERVICES if utils.pkg_installed(s.packages[0])]


def pick(prompt: str, pool: list[Service]) -> list[Service] | None:
    if not pool:
        ui.warn("Tidak ada layanan yang tersedia untuk aksi ini.")
        return None
    while True:
        raw = input(f"\n{prompt} (contoh: 1,4 | all | 0=batal): ").strip()
        if raw in ("0", ""):
            return None
        try:
            return parse_selection(raw, pool)
        except ValueError as e:
            ui.error(str(e))


# ------------------------------------------------------------------ [1] INSTALL
def install_services() -> None:
    ui.section("DAFTAR LAYANAN")
    show_services("Daftar Layanan", SERVICES)
    chosen = pick("Masukkan nomor layanan", SERVICES)
    if not chosen:
        return

    keys = {s.key for s in chosen}
    conflicts = [(s, keys & set(s.conflicts)) for s in chosen if keys & set(s.conflicts)]
    for s, clash in conflicts:
        ui.warn(f"{s.name} bentrok port dengan {', '.join(sorted(clash))}.")
    if conflicts and not ui.confirm("Tetap lanjutkan?", default=False):
        return

    external = [s for s in chosen if s.external_repo]
    if external and not ui.confirm(
            "Beberapa layanan butuh repo vendor: " +
            ", ".join(s.name for s in external) + ". Lanjut?", default=False):
        return

    ui.info("Memperbarui indeks paket (apt update)...")
    if not utils.apt_update():
        ui.error("apt update gagal. Periksa koneksi internet / repositori.")
        return

    done: list[Service] = []
    for s in chosen:
        ui.info(f"Menginstal {s.name} ({', '.join(s.packages)})...")
        if utils.apt_install(s.packages):
            for u in s.units:
                utils.systemctl("enable", u)
                utils.systemctl("start", u)
            ui.ok(f"{s.name} terpasang.")
            done.append(s)
        else:
            ui.error(f"Gagal menginstal {s.name}. "
                     f"{'Cek repo vendor.' if s.external_repo else 'Cek nama paket di apt.'}")
    for s in done:
        if s.key in CONFIGURATORS and ui.confirm(f"Konfigurasi {s.name} sekarang?"):
            CONFIGURATORS[s.key]()


# ------------------------------------------------------------------ [2] CONFIGURE
def configurator_pool() -> list[Service]:
    """Semua layanan yang punya konfigurator, terpasang maupun belum."""
    return [s for s in SERVICES if s.key in CONFIGURATORS]


def _config_status(s: Service) -> str:
    if not utils.pkg_installed(s.packages[0]):
        return "belum terpasang"
    if not s.units:
        return "siap"
    return "siap" if utils.unit_active(s.units[0]) else "terpasang (mati)"


def _run_configurator(s: Service, backup_first: bool) -> bool:
    """Jalankan satu konfigurator dengan opsi backup. Kembalikan True bila tidak crash."""
    if not utils.pkg_installed(s.packages[0]):
        ui.warn(f"{s.name} belum terpasang — lewati.")
        return False
    if backup_first:
        snap = backup.create_backup([s], label=f"pre-config-{s.key}")
        if snap:
            ui.info(f"Backup {s.name}: {snap.name}")
    try:
        CONFIGURATORS[s.key]()
        return True
    except (KeyboardInterrupt, EOFError):
        print()
        ui.warn(f"Konfigurasi {s.name} dibatalkan.")
        return False
    except Exception as exc:  # noqa: BLE001
        ui.error(f"Konfigurasi {s.name} gagal: {exc}")
        return False


def _edit_manual(s: Service) -> None:
    """Buka file konfigurasi layanan di $EDITOR."""
    if not s.config_paths:
        ui.warn(f"{s.name} tidak punya config_paths terdaftar.")
        return
    files: list[Path] = []
    for raw in s.config_paths:
        path = utils.p(raw)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
    if not files:
        ui.warn("Tidak ada file konfigurasi yang ditemukan.")
        return

    ui.table("File konfigurasi", ["No", "File"],
             [(i, str(f)) for i, f in enumerate(files, 1)])
    raw = input("\nNomor file yang diedit (0=batal): ").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= len(files):
        return
    target = files[int(raw) - 1]
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
    ui.info(f"Membuka {target} dengan {editor} ...")
    if utils.DRY_RUN:
        print(f"[dry-run] {editor} {target}")
        return
    try:
        subprocess.run([editor, str(target)])
    except FileNotFoundError:
        ui.error(f"Editor '{editor}' tidak ditemukan. Set $EDITOR.")
        return
    ui.info("Setelah selesai edit, jalankan Verify Services [4] untuk validasi.")


def configure_services() -> None:
    pool = configurator_pool()
    if not pool:
        ui.warn("Belum ada konfigurator terdaftar.")
        return

    if not hasattr(configure_services, "_backup"):
        configure_services._backup = True  # type: ignore[attr-defined]
    backup_first = configure_services._backup  # type: ignore[attr-defined]

    installed = [s for s in pool if utils.pkg_installed(s.packages[0])]
    ui.section("CONFIGURE SERVICES")
    ui.menu([
        ("1", f"Pilih konfigurator ({len(pool)} tersedia, {len(installed)} terpasang)"),
        ("2", "Configure semua layanan terpasang"),
        ("3", "Edit file konfigurasi manual"),
        ("4", f"Backup otomatis sebelum konfigurasi: "
              f"{'AKTIF' if backup_first else 'NONAKTIF'}"),
        ("0", "Kembali"),
    ])
    choice = input("Select option: ").strip()

    if choice == "0":
        return

    if choice == "4":
        configure_services._backup = not backup_first  # type: ignore[attr-defined]
        ui.info(f"Backup otomatis sebelum konfigurasi: "
                f"{'AKTIF' if configure_services._backup else 'NONAKTIF'}")  # type: ignore[attr-defined]
        return

    if choice == "2":
        if not installed:
            ui.warn("Belum ada layanan konfigurator yang terpasang.")
            return
        ui.table("Akan dikonfigurasi", ["No", "Layanan"],
                 [(i, s.name) for i, s in enumerate(installed, 1)])
        if not ui.confirm(f"Konfigurasi {len(installed)} layanan sekaligus?", default=False):
            return
        ok = fail = 0
        for s in installed:
            print()
            ui.section(f"CONFIGURING {s.name}")
            if _run_configurator(s, backup_first):
                ok += 1
            else:
                fail += 1
        ui.ok(f"Selesai: {ok} sukses, {fail} gagal/dilewati.")
        return

    if choice == "3":
        ui.table("Layanan", ["No", "Kunci", "Layanan", "Status"],
                 [(i, s.key, s.name, _config_status(s)) for i, s in enumerate(pool, 1)])
        raw = input("\nPilih nomor layanan (0=batal): ").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= len(pool):
            return
        _edit_manual(pool[int(raw) - 1])
        return

    if choice != "1":
        ui.error("Pilihan tidak valid.")
        return

    ui.table("Konfigurator tersedia", ["No", "Kunci", "Layanan", "Status"],
             [(i, s.key, s.name, _config_status(s)) for i, s in enumerate(pool, 1)])
    ui.info("Contoh: 1,3 | 1-3 | bind9,nginx | all")
    raw = input("Pilih layanan (0=batal): ").strip()
    if raw in ("", "0"):
        return
    try:
        chosen = parse_selection(raw, pool)
    except ValueError as exc:
        ui.error(str(exc))
        return

    not_installed = [s for s in chosen if not utils.pkg_installed(s.packages[0])]
    if not_installed:
        ui.warn("Belum terpasang: " + ", ".join(s.name for s in not_installed))
        if not ui.confirm("Tetap lanjut (yang belum terpasang akan dilewati)?", default=False):
            return

    if backup_first and any(utils.pkg_installed(s.packages[0]) for s in chosen):
        if ui.confirm("Buat backup konfigurasi sebelum mengubah?", default=True):
            snap = backup.create_backup(
                [s for s in chosen if utils.pkg_installed(s.packages[0])],
                label="pre-config")
            if snap:
                ui.info(f"Backup: {snap}")

    ok = fail = 0
    for s in chosen:
        print()
        ui.section(f"CONFIGURING {s.name}")
        if _run_configurator(s, backup_first=False):
            ok += 1
        else:
            fail += 1
    ui.ok(f"Selesai: {ok} sukses, {fail} gagal/dilewati.")


# ------------------------------------------------------------------ [3] MANAGE
def manage_services() -> None:
    pool = [s for s in installed_pool() if s.units]
    ui.section("MANAGE SERVICES")
    if not pool:
        ui.warn("Tidak ada layanan berbasis systemd yang terpasang.")
        return
    show_services("Layanan terpasang", pool)
    chosen = pick("Pilih layanan", pool)
    if not chosen:
        return
    actions = {"1": "start", "2": "stop", "3": "restart", "4": "reload",
               "5": "enable", "6": "disable", "7": "status", "8": "logs"}
    ui.menu([("1", "Start"), ("2", "Stop"), ("3", "Restart"), ("4", "Reload"),
             ("5", "Enable (autostart)"), ("6", "Disable"), ("7", "Status"), ("8", "Lihat log"),
             ("0", "Batal")])
    act = actions.get(input("Select option: ").strip())
    if not act:
        return
    for s in chosen:
        for u in s.units:
            if act == "status":
                print(utils.out(["systemctl", "status", u, "--no-pager", "-n", "5"]))
            elif act == "logs":
                print(utils.out(["journalctl", "-u", u, "-n", "30", "--no-pager"]))
            else:
                (ui.ok if utils.systemctl(act, u) else ui.error)(f"{act} {u}")


# ------------------------------------------------------------------ [4] VERIFY
    for s in pool:
        if s.units:
            unit = s.units[0]
            active = "OK" if utils.unit_active(unit) else "MATI"
            enabled = "ya" if utils.unit_enabled(unit) else "tidak"
        else:
            active = "n/a"
            enabled = "n/a"
        port = "-" if not s.port else (f"{s.port} OK" if utils.port_open(s.port) else f"{s.port} tutup")
        cfg = "-"
        if s.check_cmd:
            r = utils.run(list(s.check_cmd))
            cfg = "OK" if r.returncode == 0 else "ERROR"
        rows.append((s.key, active, enabled, port, cfg))
    ui.table("Hasil verifikasi", ["Layanan", "Berjalan", "Autostart", "Port", "Konfigurasi"], rows)

# ------------------------------------------------------------------ [5] UPDATE
def update_services() -> None:
    pool = installed_pool()
    ui.section("UPDATE SERVICES")
    show_services("Layanan terpasang", pool)
    chosen = pick("Pilih layanan yang diupdate", pool)
    if not chosen:
        return
    utils.apt_update()
    for s in chosen:
        (ui.ok if utils.apt_upgrade(s.packages) else ui.error)(f"Update {s.name}")


# ------------------------------------------------------------------ [6] UNINSTALL
def uninstall_services() -> None:
    pool = installed_pool()
    ui.section("UNINSTALL SERVICES")
    show_services("Layanan terpasang", pool)
    chosen = pick("Pilih layanan yang dihapus", pool)
    if not chosen:
        return
    purge = ui.confirm("Hapus juga file konfigurasi & data (purge)?", default=False)
    ui.warn("Akan dihapus: " + ", ".join(s.name for s in chosen) + (" [PURGE]" if purge else ""))
    if not ui.confirm("Yakin?", default=False):
        return
    if purge:
        snap = backup.create_backup(chosen, label="pre-uninstall")
        if snap:
            ui.info(f"Backup konfigurasi disimpan: {snap}")
    for s in chosen:
        for u in s.units:
            utils.systemctl("stop", u)
        (ui.ok if utils.apt_remove(s.packages, purge) else ui.error)(f"Uninstall {s.name}")
    utils.apt_autoremove()


# ------------------------------------------------------------------ [7] SERVER INFO
def server_information() -> None:
    """Wrapper: sysinfo.show() sudah berisi submenu lengkap."""
    sysinfo.show()


# ------------------------------------------------------------------ main loop
def main() -> None:
    utils.require_root()
    utils.check_supported_os()
    actions = {
        "1": install_services,
        "2": configure_services,
        "3": manage_services,
        "4": verify_services,
        "5": update_services,
        "6": uninstall_services,
        "7": server_information,
        "8": netdiag.menu,
        "9": backup.menu,
    }
    try:
        while True:
            ui.banner(f"SERVERKIT - LINUX SERVER TOOLKIT  v{__version__}")
            ui.menu([
                ("1", "Install Services"),
                ("2", "Configure Services"),
                ("3", "Manage Services"),
                ("4", "Verify Services"),
                ("5", "Update Services"),
                ("6", "Uninstall Services"),
                ("7", "Server Information"),
                ("8", "Network Diagnostics"),
                ("9", "Backup & Restore"),
                ("0", "Exit"),
            ])
            choice = input("Select option: ").strip()
            if choice == "0":
                print("Sampai jumpa!")
                return
            action = actions.get(choice)
            if not action:
                ui.error("Pilihan tidak valid.")
                continue
            try:
                action()
            except (KeyboardInterrupt, EOFError):
                print()
                ui.warn("Dibatalkan.")
            ui.pause()
    except (KeyboardInterrupt, EOFError):
        print("\nKeluar.")
