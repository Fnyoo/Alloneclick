"""Menu utama SERVERKIT."""
from __future__ import annotations

from . import __version__, backup, netdiag, sysinfo, ui, utils
from .configurators import CONFIGURATORS
from .services import SERVICES, Service, parse_selection


# ------------------------------------------------------------------ helper
def status_of(s: Service) -> str:
    if not utils.pkg_installed(s.packages[0]):
        return "-"
    return "aktif" if utils.unit_active(s.units[0]) else "terpasang"


def show_services(title: str, pool: list[Service], with_status: bool = True) -> None:
    rows = []
    for i, s in enumerate(pool, 1):
        row = [i, s.key, s.name, s.category, ",\n".join(s.packages) if len(s.packages) > 1 else s.packages[0]]
        if with_status:
            row.append(status_of(s))
        rows.append(row)
    cols = ["No", "Kunci", "Layanan", "Kategori", "Paket"] + (["Status"] if with_status else [])
    ui.table(title, cols, rows)


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


# ------------------------------------------------------------------ aksi
def install_services() -> None:
    ui.section("DAFTAR LAYANAN")
    show_services("Daftar Layanan", SERVICES)
    chosen = pick("Masukkan nomor layanan", SERVICES)
    if not chosen:
        return
    keys = {s.key for s in chosen}
    for s in chosen:
        clash = keys & set(s.conflicts)
        if clash and s.key < min(clash):
            ui.warn(f"{s.name} dan {', '.join(sorted(clash))} memakai port yang sama ({s.port}).")
    if any(set(s.conflicts) & keys for s in chosen) and not ui.confirm("Tetap lanjutkan?", default=False):
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
            ui.error(f"Gagal menginstal {s.name}.")
    for s in done:
        if s.key in CONFIGURATORS and ui.confirm(f"Konfigurasi {s.name} sekarang?"):
            CONFIGURATORS[s.key]()


def configure_services() -> None:
    pool = [s for s in installed_pool() if s.key in CONFIGURATORS]
    if not pool:
        ui.warn("Tidak ada layanan terpasang yang punya konfigurator "
                f"(tersedia: {', '.join(CONFIGURATORS)}). Instal dulu lewat menu [1].")
        return
    ui.section("CONFIGURE SERVICES")
    show_services("Layanan yang bisa dikonfigurasi", pool, with_status=False)
    chosen = pick("Pilih layanan", pool)
    for s in chosen or []:
        CONFIGURATORS[s.key]()


def manage_services() -> None:
    pool = installed_pool()
    ui.section("MANAGE SERVICES")
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


def verify_services() -> None:
    pool = installed_pool()
    if not pool:
        ui.warn("Belum ada layanan terpasang.")
        return
    ui.section("VERIFY SERVICES")
    rows = []
    for s in pool:
        unit = s.units[0]
        active = "OK" if utils.unit_active(unit) else "MATI"
        enabled = "ya" if utils.unit_enabled(unit) else "tidak"
        port = "-" if not s.port else (f"{s.port} OK" if utils.port_open(s.port) else f"{s.port} tutup")
        cfg = "-"
        if s.check_cmd:
            r = utils.run(list(s.check_cmd))
            cfg = "OK" if r.returncode == 0 else "ERROR"
        rows.append((s.key, active, enabled, port, cfg))
    ui.table("Hasil verifikasi", ["Layanan", "Berjalan", "Autostart", "Port", "Konfigurasi"], rows)


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


# ------------------------------------------------------------------ main loop
def main() -> None:
    utils.require_root()
    utils.check_supported_os()
    actions = {
        "1": install_services, "2": configure_services, "3": manage_services,
        "4": verify_services, "5": update_services, "6": uninstall_services,
        "7": sysinfo.show, "8": netdiag.menu, "9": backup.menu,
    }
    try:
        while True:
            ui.banner(f"SERVERKIT - LINUX SERVER TOOLKIT  v{__version__}")
            ui.menu([("1", "Install Services"), ("2", "Configure Services"),
                     ("3", "Manage Services"), ("4", "Verify Services"),
                     ("5", "Update Services"), ("6", "Uninstall Services"),
                     ("7", "Server Information"), ("8", "Network Diagnostics"),
                     ("9", "Backup & Restore"), ("0", "Exit")])
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
