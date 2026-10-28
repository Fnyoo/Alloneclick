"""Command-line interface for ServerKit."""
import os
import platform
import shutil
import socket
from typing import List, Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from . import __version__, db, dnsconf, osinfo
from . import services as svc
from .runner import CommandError, Runner

app = typer.Typer(help="ServerKit CLI - One command. Your server. Your configuration.", add_completion=False)
console = Console()
APT_ENV = {"DEBIAN_FRONTEND": "noninteractive"}


def fail(msg: str, code: int = 1):
    console.print(f"[red]✗[/red] {msg}")
    raise typer.Exit(code)


def preflight(dry_run: bool, force: bool, need_root: bool = True):
    info = osinfo.detect()
    if not info.supported:
        console.print(f"[yellow]![/yellow] {info.pretty_name} belum termasuk target yang diuji (Ubuntu 24.04, Debian 12/13).")
        if not force:
            fail("Gunakan --force bila tetap ingin melanjutkan.")
    if not shutil.which("apt-get"):
        fail("apt-get tidak ditemukan. ServerKit hanya mendukung sistem berbasis APT.")
    if not os.path.isdir("/run/systemd/system") and need_root:
        console.print("[yellow]![/yellow] systemd tidak terdeteksi; beberapa operasi layanan mungkin gagal.")
    if need_root and not dry_run and os.geteuid() != 0:
        fail("Butuh hak root. Jalankan dengan sudo, atau gunakan --dry-run.")
    return info, Runner(dry_run=dry_run, console=console)


def service_arg(name: str):
    try:
        return svc.get(name)
    except KeyError as exc:
        fail(str(exc.args[0]))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, version: bool = typer.Option(False, "--version", help="Tampilkan versi")):
    if version:
        console.print(f"ServerKit CLI {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        menu()


@app.command("list")
def list_services():
    """Daftar layanan yang tersedia."""
    table = Table("Kunci", "Layanan", "Kategori", "Paket")
    for service in svc.REGISTRY.values():
        table.add_row(service.key, service.title, service.category, " ".join(service.packages))
    console.print(table)


@app.command()
def install(name: str, dry_run: bool = typer.Option(False, "--dry-run", help="Simulasi tanpa mengubah sistem"),
            yes: bool = typer.Option(False, "--yes", "-y", help="Lewati konfirmasi"),
            force: bool = typer.Option(False, "--force", help="Lanjut meski OS belum teruji")):
    """Install layanan melalui APT lalu verifikasi."""
    service = service_arg(name)
    info, runner = preflight(dry_run, force)
    console.print(f"OS terdeteksi: [bold]{info.pretty_name}[/bold]")
    already = [pkg for pkg in service.packages if svc.is_installed(pkg, runner)]
    conflicts = [] if len(already) == len(service.packages) else svc.port_conflicts(service, runner)
    console.print(f"\n[bold]Rencana:[/bold] pasang {', '.join(service.packages)}" + (f", aktifkan unit {service.unit}" if service.unit else ""))
    if already:
        console.print(f"Sudah terpasang: {', '.join(already)}")
    if conflicts:
        console.print(f"[yellow]Port mungkin sudah digunakan: {conflicts}[/yellow]")
    if not yes and not dry_run and not Confirm.ask("Lanjutkan?", default=False):
        raise typer.Exit()
    try:
        with console.status("Menjalankan apt-get..."):
            runner.run(["apt-get", "update"], env_extra=APT_ENV)
            missing = [pkg for pkg in service.packages if pkg not in already]
            if missing:
                runner.run(["apt-get", "install", "-y", *missing], env_extra=APT_ENV)
            if service.unit and not dry_run:
                runner.run(["systemctl", "enable", "--now", service.unit])
    except CommandError as exc:
        if not dry_run:
            db.record("install", service.key, "gagal", str(exc))
        fail(f"Instalasi gagal:\n{exc}")
    if dry_run:
        console.print("[green]Dry-run selesai. Tidak ada perubahan sistem yang dilakukan oleh runner.[/green]")
        return
    ok = show_verify(service, runner)
    db.record("install", service.key, "ok" if ok else "verifikasi-gagal")


def show_verify(service: svc.Service, runner: Runner) -> bool:
    table = Table("Pemeriksaan", "Hasil", "Detail", title=f"Verifikasi {service.title}")
    all_ok = True
    for label, ok, detail in svc.verify(service, runner):
        all_ok = all_ok and ok
        table.add_row(label, "[green]OK[/green]" if ok else "[red]GAGAL[/red]", detail)
    console.print(table)
    return all_ok


@app.command()
def verify(name: str):
    """Periksa konfigurasi dan status layanan."""
    service = service_arg(name)
    _, runner = preflight(False, True, need_root=False)
    if not show_verify(service, runner):
        raise typer.Exit(1)


@app.command()
def manage(name: str, action: str = typer.Argument(..., help="start|stop|restart|enable|disable|status|logs"),
           dry_run: bool = typer.Option(False, "--dry-run")):
    """Kelola status dan log layanan."""
    service = service_arg(name)
    if not service.unit:
        fail("Layanan ini tidak memiliki unit systemd.")
    allowed = {"start", "stop", "restart", "enable", "disable", "status", "logs"}
    if action not in allowed:
        fail("Aksi tidak valid.")
    read_only = action in {"status", "logs"}
    _, runner = preflight(dry_run, True, need_root=not read_only)
    cmd = ["journalctl", "-u", service.unit, "-n", "50", "--no-pager"] if action == "logs" else ["systemctl", action, service.unit]
    if action == "status":
        cmd.insert(2, "--no-pager")
    result = runner.run(cmd, mutating=not read_only, check=False)
    console.print((result.stdout or result.stderr).rstrip() or f"{action}: selesai")
    if not read_only and not dry_run:
        db.record("manage-" + action, service.key, "ok" if result.ok else "gagal", result.stderr.strip()[:200])


@app.command()
def update(name: Optional[str] = typer.Argument(None, help="Layanan yang diperbarui; kosong = hanya cek"),
           dry_run: bool = typer.Option(False, "--dry-run"), yes: bool = typer.Option(False, "--yes", "-y")):
    """Cek pembaruan APT atau perbarui paket satu layanan."""
    _, runner = preflight(dry_run, True, need_root=name is not None)
    if name is None:
        runner.run(["apt-get", "update"], check=False, mutating=False)
        result = runner.run(["apt-get", "-s", "upgrade"], mutating=False, check=False)
        rows = [line.split()[1:4] for line in result.stdout.splitlines() if line.startswith("Inst ")]
        table = Table("Paket", "Versi lama", "Versi baru", title=f"{len(rows)} paket dapat diperbarui")
        for row in rows:
            table.add_row(row[0], row[1].strip("[]") if len(row) > 1 else "", row[2].lstrip("(") if len(row) > 2 else "")
        console.print(table)
        return
    service = service_arg(name)
    console.print(f"Akan memperbarui: {', '.join(service.packages)}. Backup konfigurasi bukan rollback versi paket.")
    if not yes and not dry_run and not Confirm.ask("Lanjutkan?", default=False):
        raise typer.Exit()
    try:
        runner.run(["apt-get", "update"], env_extra=APT_ENV)
        runner.run(["apt-get", "install", "-y", "--only-upgrade", *service.packages], env_extra=APT_ENV)
    except CommandError as exc:
        if not dry_run:
            db.record("update", service.key, "gagal", str(exc))
        fail(f"Update gagal:\n{exc}")
    if not dry_run:
        ok = show_verify(service, runner)
        db.record("update", service.key, "ok" if ok else "verifikasi-gagal")


@app.command()
def uninstall(name: str, purge: bool = typer.Option(False, "--purge", help="Hapus juga file konfigurasi"),
              dry_run: bool = typer.Option(False, "--dry-run"), yes: bool = typer.Option(False, "--yes", "-y")):
    """Hapus layanan melalui APT."""
    service = service_arg(name)
    _, runner = preflight(dry_run, True)
    console.print(f"[red]Akan menghapus:[/red] {', '.join(service.packages)}" + (" [bold](termasuk konfigurasi paket)[/bold]" if purge else ""))
    if not yes and not dry_run and not Confirm.ask("Yakin?", default=False):
        raise typer.Exit()
    try:
        if service.unit:
            runner.run(["systemctl", "disable", "--now", service.unit], check=False)
        runner.run(["apt-get", "purge" if purge else "remove", "-y", *service.packages], env_extra=APT_ENV)
    except CommandError as exc:
        if not dry_run:
            db.record("uninstall", service.key, "gagal", str(exc))
        fail(f"Uninstall gagal:\n{exc}")
    if not dry_run:
        db.record("uninstall", service.key, "ok", "purge" if purge else "remove")


@app.command()
def info():
    """Tampilkan informasi dasar server."""
    os_data = osinfo.detect()
    table = Table("Item", "Nilai", title="Informasi Server")
    table.add_row("Hostname", socket.gethostname())
    table.add_row("OS", f"{os_data.pretty_name} ({'didukung' if os_data.supported else 'belum teruji'})")
    table.add_row("Kernel", platform.release())
    table.add_row("CPU", str(os.cpu_count()))
    try:
        with open("/proc/meminfo", encoding="utf-8") as file:
            mem = {line.split(":")[0]: int(line.split()[1]) for line in file if ":" in line}
        table.add_row("RAM", f"{mem['MemTotal'] // 1024} MB (tersedia {mem.get('MemAvailable', 0) // 1024} MB)")
        with open("/proc/uptime", encoding="utf-8") as file:
            uptime = float(file.read().split()[0])
        table.add_row("Uptime", f"{int(uptime // 3600)} jam {int(uptime % 3600 // 60)} menit")
    except (OSError, KeyError, ValueError):
        pass
    disk = shutil.disk_usage("/")
    table.add_row("Disk /", f"{disk.free // 2**30} GB bebas dari {disk.total // 2**30} GB")
    result = Runner().run(["hostname", "-I"], mutating=False, check=False)
    table.add_row("IP", result.stdout.strip() or "-")
    console.print(table)


@app.command()
def doctor():
    """Diagnosis dasar sistem dan rekomendasi."""
    os_data = osinfo.detect()
    runner = Runner()
    checks = [
        ("OS didukung", os_data.supported, os_data.pretty_name, "Gunakan Ubuntu 24.04 / Debian 12 / 13"),
        ("Hak root", os.geteuid() == 0, "", "Jalankan dengan sudo untuk install/manage"),
        ("systemd berjalan", os.path.isdir("/run/systemd/system"), "", "ServerKit membutuhkan systemd"),
        ("apt-get tersedia", bool(shutil.which("apt-get")), "", "Hanya sistem berbasis APT"),
    ]
    free_gb = shutil.disk_usage("/").free // 2**30
    checks.append(("Disk bebas ≥ 2 GB", free_gb >= 2, f"{free_gb} GB", "Bersihkan disk: apt-get clean"))
    audit = runner.run(["dpkg", "--audit"], mutating=False, check=False)
    checks.append(("dpkg konsisten", audit.ok and not audit.stdout.strip(), audit.stdout.strip()[:80], "Jalankan: dpkg --configure -a"))
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        net_ok = True
    except OSError:
        net_ok = False
    checks.append(("Koneksi internet", net_ok, "", "Periksa jaringan/DNS"))
    table = Table("Pemeriksaan", "Hasil", "Detail", "Rekomendasi", title="System Doctor")
    for label, ok, detail, recommendation in checks:
        table.add_row(label, "[green]OK[/green]" if ok else "[red]MASALAH[/red]", detail, "" if ok else recommendation)
    console.print(table)


@app.command()
def history(limit: int = typer.Option(20, min=1, max=500, help="Jumlah catatan yang ditampilkan")):
    """Tampilkan riwayat tindakan."""
    table = Table("Waktu (UTC)", "Aksi", "Layanan", "Status", "Detail", title="Installation History")
    for row in db.history(limit):
        table.add_row(*[str(value or "") for value in row])
    console.print(table)


dns_app = typer.Typer(help="Konfigurasi DNS (BIND9): zona forward dan reverse")
app.add_typer(dns_app, name="dns")


@dns_app.command("setup")
def dns_setup(domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Contoh: lab.lan"),
              ip: Optional[str] = typer.Option(None, "--ip", help="IPv4 server DNS ini"),
              hostname: str = typer.Option("ns1", "--hostname", help="Nama host name-server"),
              network: Optional[str] = typer.Option(None, "--network", help="CIDR /8, /16, /24 (default: /24 dari IP)"),
              forwarders: str = typer.Option("1.1.1.1,8.8.8.8", "--forwarders", help="Pisahkan koma; kosong = tanpa forwarder"),
              record: Optional[List[str]] = typer.Option(None, "--record", "-r", help="nama=ip, bisa diulang"),
              dry_run: bool = typer.Option(False, "--dry-run", help="Tampilkan rencana tanpa menulis"),
              yes: bool = typer.Option(False, "--yes", "-y"), force: bool = typer.Option(False, "--force")):
    """Buat zona forward/reverse BIND9, validasi, lalu reload."""
    _, runner = preflight(dry_run, force)
    if not domain:
        domain = Prompt.ask("Domain (mis. lab.lan)")
    if not ip:
        ip = Prompt.ask("IP server DNS ini")
    try:
        config = dnsconf.DnsConfig.build(domain, ip, hostname, network, forwarders, record)
        plan = dnsconf.build_plan(config)
    except ValueError as exc:
        fail(str(exc))
    if config.domain.endswith(".local"):
        console.print("[yellow]![/yellow] Domain .local dapat bentrok dengan mDNS; pertimbangkan .lan, .home.arpa, atau domain milik sendiri.")
    if not dry_run and not svc.is_installed("bind9", runner):
        fail("BIND9 belum terpasang. Jalankan: sudo serverkit install bind9")
    table = Table("Item", "Nilai", title="Rencana konfigurasi DNS")
    table.add_row("Zona forward", config.domain)
    table.add_row("Zona reverse", config.reverse_zone)
    table.add_row("Name server", f"{config.ns_fqdn} ({config.ip})")
    table.add_row("Jaringan", config.network)
    table.add_row("Forwarder", ", ".join(config.forwarders) or "-")
    table.add_row("Record A", ", ".join(f"{name}={addr}" for name, addr in config.records))
    table.add_row("Record PTR", str(len(config.ptrs)))
    console.print(table)
    if dry_run:
        for path, content in plan.items():
            console.rule(str(path))
            console.print(content, markup=False, highlight=False)
        for cmd in dnsconf.validation_commands(config):
            console.print("[yellow][dry-run][/yellow] " + " ".join(cmd))
        console.print("[green]Dry-run selesai. File tidak ditulis.[/green]")
        return
    if not yes and not Confirm.ask("Tulis konfigurasi ini? Backup /etc/bind akan dibuat terlebih dahulu.", default=False):
        raise typer.Exit()
    archive, rollback = dnsconf.write_plan(plan)
    console.print(f"Backup: {archive}")
    errors = []
    for cmd in dnsconf.validation_commands(config):
        result = runner.run(cmd, mutating=False, check=False)
        if not result.ok:
            errors.append(f"{' '.join(cmd)}\n{(result.stderr or result.stdout).strip()}")
    if errors:
        rollback()
        db.record("configure-dns", "bind9", "gagal-validasi", config.domain)
        fail("Validasi gagal, konfigurasi dikembalikan:\n" + "\n".join(errors))
    try:
        if svc.unit_active("named", runner):
            runner.run(["systemctl", "reload", "named"])
        else:
            runner.run(["systemctl", "enable", "--now", "named"])
    except CommandError as exc:
        rollback()
        runner.run(["systemctl", "reload", "named"], check=False)
        db.record("configure-dns", "bind9", "gagal-reload", config.domain)
        fail(f"Reload gagal, konfigurasi dikembalikan (backup: {archive}):\n{exc}")
    ok = show_dns_check(config.domain, runner)
    db.record("configure-dns", "bind9", "ok" if ok else "uji-gagal", config.domain)


def show_dns_check(domain: str, runner: Runner) -> bool:
    try:
        results = dnsconf.check_dns(domain, runner)
    except FileNotFoundError as exc:
        fail(str(exc))
    table = Table("Uji", "Hasil", "Jawaban", title=f"Uji DNS {domain}")
    for label, ok, detail in results:
        table.add_row(label, "[green]OK[/green]" if ok else "[red]GAGAL[/red]", detail)
    console.print(table)
    return all(ok for _, ok, _ in results)


@dns_app.command("test")
def dns_test(domain: str = typer.Argument(..., help="Domain yang sudah dikonfigurasi")):
    """Uji resolusi forward dan reverse zona DNS."""
    _, runner = preflight(False, True, need_root=False)
    if not show_dns_check(domain.strip().lower(), runner):
        raise typer.Exit(1)


def menu():
    items = {
        "1": "Install Services", "2": "Configure DNS", "3": "Verify Services", "4": "Manage Services",
        "5": "Check for Updates", "6": "Uninstall Services", "7": "Server Information", "8": "Network Diagnostics",
        "9": "Backup & Restore", "10": "Installation History", "11": "Configuration Profiles",
        "12": "System Doctor", "13": "Exit",
    }
    while True:
        console.print(f"\\n[bold cyan]ServerKit CLI {__version__}[/bold cyan]")
        for key, label in items.items():
            console.print(f" {key:>2}. {label}")
        choice = Prompt.ask("Pilih", choices=list(items), show_choices=False)
        if choice == "13":
            return
        if choice in {"8", "9", "11"}:
            console.print("[yellow]Fitur ini masih dalam roadmap dan belum tersedia.[/yellow]")
            continue
        try:
            if choice == "2":
                dns_setup(domain=None, ip=None, hostname="ns1", network=None, forwarders="1.1.1.1,8.8.8.8", record=None, dry_run=False, yes=False, force=False)
            elif choice == "7":
                info()
            elif choice == "10":
                history()
            elif choice == "12":
                doctor()
            elif choice == "5":
                update(None, False, False)
            else:
                name = Prompt.ask("Layanan", choices=list(svc.REGISTRY))
                if choice == "1":
                    install(name, False, False, False)
                elif choice == "3":
                    verify(name)
                elif choice == "4":
                    action = Prompt.ask("Aksi", choices=["start", "stop", "restart", "status", "logs"])
                    manage(name, action, False)
                elif choice == "6":
                    uninstall(name, False, False, False)
        except typer.Exit:
            continue


if __name__ == "__main__":
    app()
