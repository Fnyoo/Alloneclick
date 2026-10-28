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
    if need_root and not dry_run and os.geteuid() != 0:
        fail("Butuh hak root. Jalankan dengan sudo, atau gunakan --dry-run.")
    return info, Runner(dry_run=dry_run, console=console)


def service_arg(name: str):
    try:
        return svc.get(name)
    except KeyError as e:
        fail(str(e.args[0]))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, version: bool = typer.Option(False, "--version", help="Tampilkan versi")):
    if version:
        console.print(f"ServerKit CLI {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        menu()


def services_table(runner: Runner) -> list:
    """Tampilkan daftar layanan bernomor beserta status; kembalikan list Service sesuai nomor."""
    items = list(svc.REGISTRY.values())
    t = Table("No", "Kunci", "Layanan", "Kategori", "Paket", "Status", title="Daftar Layanan")
    t.columns[4].overflow = "fold"
    for i, s in enumerate(items, 1):
        have = [svc.is_installed(p, runner) for p in s.packages]
        status = "[green]terpasang[/green]" if all(have) else ("[yellow]sebagian[/yellow]" if any(have) else "-")
        t.add_row(str(i), s.key, s.title, s.category, ", ".join(s.packages), status)
    console.print(t)
    return items


def pick_services(runner: Runner, multiple: bool = True) -> list:
    """Minta pengguna mengetik nomor layanan. Kosong = batal."""
    items = services_table(runner)
    hint = "Ketik nomor (mis. 1 atau 1,3 atau 1-3)" if multiple else "Ketik nomor layanan"
    while True:
        try:
            raw = Prompt.ask(f"{hint}, kosong = batal", default="", show_default=False)
        except (EOFError, KeyboardInterrupt):
            return []
        if not raw.strip():
            return []
        try:
            nums = svc.parse_selection(raw, len(items))
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            continue
        if not multiple and len(nums) != 1:
            console.print("[red]Pilih satu nomor saja.[/red]")
            continue
        return [items[n - 1] for n in nums]


@app.command("list")
def list_services():
    """Daftar layanan bernomor dan statusnya."""
    services_table(Runner())


@app.command()
def install(
    names: Optional[List[str]] = typer.Argument(None, help="Kunci layanan (boleh lebih dari satu). Kosong = pilih dari daftar bernomor"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulasi tanpa mengubah sistem"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Lewati konfirmasi"),
    force: bool = typer.Option(False, "--force", help="Lanjut meski OS belum teruji"),
):
    """Install layanan: pilih nomor dari daftar (atau sebut namanya) → rencana → konfirmasi → install → verifikasi."""
    info, runner = preflight(dry_run, force)
    console.print(f"OS terdeteksi: [bold]{info.pretty_name}[/bold]")
    selected = [service_arg(n) for n in names] if names else pick_services(runner)
    if not selected:
        console.print("Dibatalkan: tidak ada layanan dipilih.")
        raise typer.Exit()

    console.print("\n[bold]Rencana:[/bold]")
    for s in selected:
        already = [p for p in s.packages if svc.is_installed(p, runner)]
        console.print(f"  • {s.title}: pasang {', '.join(s.packages)}" + (f", aktifkan unit {s.unit}" if s.unit else ""))
        if already:
            console.print(f"    sudah terpasang: {', '.join(already)}")
        if len(already) < len(s.packages):
            busy = svc.port_conflicts(s, runner)
            if busy:
                console.print(f"[yellow]    port sudah dipakai proses lain: {busy}[/yellow]")
    by_port = {}
    for s in selected:
        for p in s.ports:
            by_port.setdefault(p, []).append(s.key)
    for port, keys in by_port.items():
        if len(keys) > 1:
            console.print(f"[yellow]! Port {port} dipakai bersamaan oleh pilihan Anda: {', '.join(keys)}. Salah satu mungkin gagal start.[/yellow]")
    if not yes and not dry_run and not Confirm.ask("Lanjutkan?", default=False):
        raise typer.Exit()

    try:
        with console.status("apt-get update..."):
            runner.run(["apt-get", "update"], env_extra=APT_ENV)
    except CommandError as e:
        fail(f"apt-get update gagal:\n{e}")
    failed = []
    for s in selected:
        try:
            with console.status(f"Memasang {s.title}..."):
                runner.run(["apt-get", "install", "-y", *s.packages], env_extra=APT_ENV)
                if s.unit:
                    runner.run(["systemctl", "enable", "--now", s.unit])
        except CommandError as e:
            failed.append(s.key)
            if not dry_run:
                db.record("install", s.key, "gagal", str(e))
            console.print(f"[red]✗ {s.title} gagal:[/red]\n{e}")
            continue
        if dry_run:
            continue
        ok = show_verify(s, runner)
        db.record("install", s.key, "ok" if ok else "verifikasi-gagal")
        if not ok:
            failed.append(s.key)
    if dry_run:
        console.print("[green]Dry-run selesai. Tidak ada perubahan dilakukan.[/green]")
        return
    if failed:
        console.print(f"[yellow]Perlu dicek: {', '.join(failed)}[/yellow]")
        raise typer.Exit(1)
    console.print("[green]Selesai.[/green]")


def show_verify(s: svc.Service, runner: Runner) -> bool:
    t = Table("Pemeriksaan", "Hasil", "Detail", title=f"Verifikasi {s.title}")
    all_ok = True
    for label, ok, detail in svc.verify(s, runner):
        all_ok &= ok
        t.add_row(label, "[green]OK[/green]" if ok else "[red]GAGAL[/red]", detail)
    console.print(t)
    return all_ok


@app.command()
def verify(name: str):
    """Periksa konfigurasi dan status layanan."""
    s = service_arg(name)
    _, runner = preflight(False, True, need_root=False)
    if not show_verify(s, runner):
        raise typer.Exit(1)


@app.command()
def manage(
    name: str,
    action: str = typer.Argument(..., help="start|stop|restart|enable|disable|status|logs"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Kelola status dan log layanan."""
    s = service_arg(name)
    if not s.unit:
        fail("Layanan ini tidak memiliki unit systemd.")
    if action not in {"start", "stop", "restart", "enable", "disable", "status", "logs"}:
        fail("Aksi tidak valid.")
    read_only = action in {"status", "logs"}
    _, runner = preflight(dry_run, True, need_root=not read_only)
    cmd = ["journalctl", "-u", s.unit, "-n", "50", "--no-pager"] if action == "logs" else ["systemctl", action, s.unit]
    if action == "status":
        cmd.insert(2, "--no-pager")
    r = runner.run(cmd, mutating=not read_only, check=False)
    console.print((r.stdout or r.stderr).rstrip() or f"{action}: selesai")
    if not read_only and not dry_run:
        db.record("manage-" + action, s.key, "ok" if r.ok else "gagal", r.stderr.strip()[:200])


@app.command()
def update(
    name: Optional[str] = typer.Argument(None, help="Layanan yang diperbarui; kosong = hanya cek"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Cek pembaruan (tanpa argumen) atau perbarui paket satu layanan."""
    _, runner = preflight(dry_run, True, need_root=name is not None)
    if name is None:
        runner.run(["apt-get", "update"], check=False)
        r = runner.run(["apt-get", "-s", "upgrade"], mutating=False, check=False)
        rows = [l.split()[1:4] for l in r.stdout.splitlines() if l.startswith("Inst ")]
        t = Table("Paket", "Versi lama", "Versi baru", title=f"{len(rows)} paket dapat diperbarui")
        for row in rows:
            t.add_row(row[0], row[1].strip("[]") if len(row) > 1 else "", row[2].lstrip("(") if len(row) > 2 else "")
        console.print(t)
        return
    s = service_arg(name)
    console.print(f"Akan memperbarui: {', '.join(s.packages)} (backup konfigurasi bukan rollback versi paket)")
    if not yes and not dry_run and not Confirm.ask("Lanjutkan?", default=False):
        raise typer.Exit()
    try:
        runner.run(["apt-get", "update"], env_extra=APT_ENV)
        runner.run(["apt-get", "install", "-y", "--only-upgrade", *s.packages], env_extra=APT_ENV)
    except CommandError as e:
        db.record("update", s.key, "gagal", str(e))
        fail(f"Update gagal:\n{e}")
    if not dry_run:
        ok = show_verify(s, runner)
        db.record("update", s.key, "ok" if ok else "verifikasi-gagal")


@app.command()
def uninstall(
    name: str,
    purge: bool = typer.Option(False, "--purge", help="Hapus juga file konfigurasi"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Hapus layanan (dengan konfirmasi)."""
    s = service_arg(name)
    _, runner = preflight(dry_run, True)
    console.print(f"[red]Akan menghapus:[/red] {', '.join(s.packages)}" + (" [bold](termasuk konfigurasi/data)[/bold]" if purge else ""))
    if not yes and not dry_run and not Confirm.ask("Yakin?", default=False):
        raise typer.Exit()
    try:
        if s.unit:
            runner.run(["systemctl", "disable", "--now", s.unit], check=False)
        runner.run(["apt-get", "purge" if purge else "remove", "-y", *s.packages], env_extra=APT_ENV)
    except CommandError as e:
        db.record("uninstall", s.key, "gagal", str(e))
        fail(f"Uninstall gagal:\n{e}")
    if not dry_run:
        db.record("uninstall", s.key, "ok", "purge" if purge else "remove")


@app.command()
def info():
    """Informasi server."""
    o = osinfo.detect()
    t = Table("Item", "Nilai", title="Informasi Server")
    t.add_row("Hostname", socket.gethostname())
    t.add_row("OS", f"{o.pretty_name} ({'didukung' if o.supported else 'belum teruji'})")
    t.add_row("Kernel", platform.release())
    t.add_row("CPU", str(os.cpu_count()))
    try:
        mem = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo")}
        t.add_row("RAM", f"{mem['MemTotal'] // 1024} MB (tersedia {mem['MemAvailable'] // 1024} MB)")
        up = float(open("/proc/uptime").read().split()[0])
        t.add_row("Uptime", f"{int(up // 3600)} jam {int(up % 3600 // 60)} menit")
    except (OSError, KeyError):
        pass
    d = shutil.disk_usage("/")
    t.add_row("Disk /", f"{d.free // 2**30} GB bebas dari {d.total // 2**30} GB")
    r = Runner().run(["hostname", "-I"], mutating=False, check=False)
    t.add_row("IP", r.stdout.strip() or "-")
    console.print(t)


@app.command()
def doctor():
    """Diagnosis dasar sistem dan rekomendasi."""
    o = osinfo.detect()
    runner = Runner()
    checks = []
    checks.append(("OS didukung", o.supported, o.pretty_name, "Gunakan Ubuntu 24.04 / Debian 12 / 13"))
    checks.append(("Hak root", os.geteuid() == 0, "", "Jalankan dengan sudo untuk install/manage"))
    checks.append(("systemd berjalan", os.path.isdir("/run/systemd/system"), "", "ServerKit membutuhkan systemd"))
    checks.append(("apt-get tersedia", bool(shutil.which("apt-get")), "", "Hanya sistem berbasis APT"))
    free_gb = shutil.disk_usage("/").free // 2**30
    checks.append(("Disk bebas ≥ 2 GB", free_gb >= 2, f"{free_gb} GB", "Bersihkan disk: apt-get clean"))
    audit = runner.run(["dpkg", "--audit"], mutating=False, check=False)
    checks.append(("dpkg konsisten", audit.ok and not audit.stdout.strip(), audit.stdout.strip()[:80], "Jalankan: dpkg --configure -a"))
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        net = True
    except OSError:
        net = False
    checks.append(("Koneksi internet", net, "", "Periksa jaringan/DNS"))
    t = Table("Pemeriksaan", "Hasil", "Detail", "Rekomendasi", title="System Doctor")
    for label, ok, detail, rec in checks:
        t.add_row(label, "[green]OK[/green]" if ok else "[red]MASALAH[/red]", detail, "" if ok else rec)
    console.print(t)


@app.command()
def history(limit: int = 20):
    """Riwayat tindakan."""
    t = Table("Waktu (UTC)", "Aksi", "Layanan", "Status", "Detail", title="Installation History")
    for row in db.history(limit):
        t.add_row(*[str(c or "") for c in row])
    console.print(t)


dns_app = typer.Typer(help="Konfigurasi DNS (BIND9): zona forward dan reverse")
app.add_typer(dns_app, name="dns")


@dns_app.command("setup")
def dns_setup(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Contoh: lab.lan"),
    ip: Optional[str] = typer.Option(None, "--ip", help="IPv4 server DNS ini"),
    hostname: str = typer.Option("ns1", "--hostname", help="Nama host name-server"),
    network: Optional[str] = typer.Option(None, "--network", help="CIDR /8,/16,/24 (default: /24 dari IP)"),
    forwarders: str = typer.Option("1.1.1.1,8.8.8.8", "--forwarders", help="Pisahkan koma; kosong = tanpa forwarder"),
    record: Optional[List[str]] = typer.Option(None, "--record", "-r", help="nama=ip, bisa diulang (mis. www=192.168.1.20)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Tampilkan file yang akan dibuat tanpa menulis"),
    yes: bool = typer.Option(False, "--yes", "-y"),
    force: bool = typer.Option(False, "--force"),
):
    """Buat zona forward + reverse BIND9: render → backup → tulis → validasi → reload → uji (rollback jika gagal)."""
    _, runner = preflight(dry_run, force)
    if not domain:
        domain = Prompt.ask("Domain (mis. lab.lan)")
    if not ip:
        ip = Prompt.ask("IP server DNS ini")
    try:
        cfg = dnsconf.DnsConfig.build(domain, ip, hostname, network, forwarders, record)
        plan = dnsconf.build_plan(cfg)
    except ValueError as e:
        fail(str(e))
    if cfg.domain.endswith(".local"):
        console.print("[yellow]![/yellow] Domain .local bentrok dengan mDNS; disarankan .lan, .home.arpa, atau domain milik sendiri.")
    if not dry_run and not svc.is_installed("bind9", runner):
        fail("BIND9 belum terpasang. Jalankan: sudo serverkit install bind9")

    t = Table("Item", "Nilai", title="Rencana konfigurasi DNS")
    t.add_row("Zona forward", cfg.domain)
    t.add_row("Zona reverse", cfg.reverse_zone)
    t.add_row("Name server", f"{cfg.ns_fqdn} ({cfg.ip})")
    t.add_row("Jaringan", cfg.network)
    t.add_row("Forwarder", ", ".join(cfg.forwarders) or "-")
    t.add_row("Record A", ", ".join(f"{n}={i}" for n, i in cfg.records))
    t.add_row("Record PTR", str(len(cfg.ptrs)))
    console.print(t)

    if dry_run:
        for path, text in plan.items():
            console.rule(str(path))
            console.print(text, markup=False, highlight=False)
        for cmd in dnsconf.validation_commands(cfg):
            console.print("[yellow]\\[dry-run][/yellow] " + " ".join(cmd))
        console.print("[yellow]\\[dry-run][/yellow] systemctl reload named")
        console.print("[green]Dry-run selesai. Tidak ada file diubah.[/green]")
        return
    if not yes and not Confirm.ask("Tulis konfigurasi ini? (backup /etc/bind dibuat dulu)", default=False):
        raise typer.Exit()

    archive, rollback = dnsconf.write_plan(plan)
    console.print(f"Backup: {archive}")
    errors = []
    for cmd in dnsconf.validation_commands(cfg):
        r = runner.run(cmd, mutating=False, check=False)
        if not r.ok:
            errors.append(f"{' '.join(cmd)}\n{(r.stderr or r.stdout).strip()}")
    if errors:
        rollback()
        db.record("configure-dns", "bind9", "gagal-validasi", cfg.domain)
        fail("Validasi gagal, konfigurasi dikembalikan:\n" + "\n".join(errors))
    try:
        if svc.unit_active("named", runner):
            runner.run(["systemctl", "reload", "named"])
        else:
            runner.run(["systemctl", "enable", "--now", "named"])
    except CommandError as e:
        rollback()
        runner.run(["systemctl", "reload", "named"], check=False)
        db.record("configure-dns", "bind9", "gagal-reload", cfg.domain)
        fail(f"Reload gagal, konfigurasi dikembalikan (backup: {archive}):\n{e}")
    ok = show_dns_check(cfg.domain, runner)
    db.record("configure-dns", "bind9", "ok" if ok else "uji-gagal", cfg.domain)


def show_dns_check(domain: str, runner: Runner) -> bool:
    try:
        results = dnsconf.check_dns(domain, runner)
    except FileNotFoundError as e:
        fail(str(e))
    t = Table("Uji", "Hasil", "Jawaban", title=f"Uji DNS {domain}")
    for label, ok, detail in results:
        t.add_row(label, "[green]OK[/green]" if ok else "[red]GAGAL[/red]", detail)
    console.print(t)
    return all(ok for _, ok, _ in results)


@dns_app.command("test")
def dns_test(domain: str = typer.Argument(..., help="Domain yang sudah dikonfigurasi")):
    """Uji resolusi forward dan reverse untuk zona yang dibuat ServerKit."""
    _, runner = preflight(False, True, need_root=False)
    if not show_dns_check(domain.strip().lower(), runner):
        raise typer.Exit(1)


def menu():
    items = {
        "1": "Install Services", "2": "Configure Services", "3": "Verify Services", "4": "Manage Services",
        "5": "Update Services", "6": "Uninstall Services", "7": "Server Information", "8": "Network Diagnostics",
        "9": "Backup & Restore", "10": "Installation History", "11": "Configuration Profiles",
        "12": "System Doctor", "13": "Exit",
    }
    while True:
        console.print(f"\n[bold cyan]ServerKit CLI {__version__}[/bold cyan]")
        for k, v in items.items():
            console.print(f" {k:>2}. {v}")
        c = Prompt.ask("Pilih", choices=list(items), show_choices=False)
        if c == "13":
            return
        if c in {"8", "9", "11"}:
            console.print("[yellow]Fitur ini ada di roadmap, belum tersedia.[/yellow]")
            continue
        try:
            if c == "2":
                dns_setup(domain=None, ip=None, hostname="ns1", network=None, forwarders="1.1.1.1,8.8.8.8",
                          record=None, dry_run=False, yes=False, force=False)
            elif c == "7":
                info()
            elif c == "10":
                history()
            elif c == "12":
                doctor()
            elif c == "5":
                update(None, False, False)
            elif c == "1":
                install(names=None, dry_run=False, yes=False, force=False)
            else:
                picked = pick_services(Runner(), multiple=False)
                if not picked:
                    continue
                name = picked[0].key
                if c == "3":
                    verify(name)
                elif c == "4":
                    act = Prompt.ask("Aksi", choices=["start", "stop", "restart", "status", "logs"])
                    manage(name, act, False)
                elif c == "6":
                    uninstall(name, False, False, False)
        except typer.Exit:
            pass


if __name__ == "__main__":
    app()
