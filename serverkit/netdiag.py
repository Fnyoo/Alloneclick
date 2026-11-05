"""Diagnostik jaringan."""
from __future__ import annotations

import shutil
import socket

from . import ui, utils, validators as v


def interfaces() -> None:
    print(utils.out(["ip", "-br", "address"]) or "(perintah 'ip' tidak tersedia)")
    print()
    print(utils.out(["ip", "route"]))


def resolvers() -> None:
    try:
        lines = [l.strip() for l in open("/etc/resolv.conf") if l.strip() and not l.startswith("#")]
        print("/etc/resolv.conf:\n  " + "\n  ".join(lines))
    except OSError:
        ui.error("Tidak bisa membaca /etc/resolv.conf")
    if shutil.which("resolvectl"):
        print("\n" + utils.out(["resolvectl", "status"])[:1500])


def dns_lookup() -> None:
    name = ui.ask("Nama host/domain", None, width=0)
    rtype = ui.ask("Tipe record", "A", width=0).upper()
    server = ui.ask("DNS server (kosong = default sistem)", "", width=0, allow_empty=True)
    if shutil.which("dig"):
        cmd = ["dig", "+short", name, rtype]
        if server:
            cmd.insert(1, f"@{server}")
        res = utils.out(cmd)
        print(res if res else "(tidak ada jawaban)")
    else:
        try:
            print("\n".join(sorted({a[4][0] for a in socket.getaddrinfo(name, None)})))
        except socket.gaierror as e:
            ui.error(f"Gagal resolve: {e}")


def reverse_lookup() -> None:
    ip = ui.ask("IP address", None, v.ipv4, width=0)
    server = ui.ask("DNS server (kosong = default sistem)", "", width=0, allow_empty=True)
    if shutil.which("dig"):
        cmd = ["dig", "+short", "-x", ip]
        if server:
            cmd.insert(1, f"@{server}")
        print(utils.out(cmd) or "(tidak ada jawaban)")
    else:
        try:
            print(socket.gethostbyaddr(ip)[0])
        except OSError as e:
            ui.error(str(e))


def ping() -> None:
    host = ui.ask("Host tujuan", "8.8.8.8", width=0)
    print(utils.out(["ping", "-c", "4", "-W", "2", host]))


def check_port() -> None:
    host = ui.ask("Host", "127.0.0.1", width=0)
    port = int(ui.ask("Port", None, v.port, width=0))
    (ui.ok if utils.port_open(port, host) else ui.error)(
        f"{host}:{port} " + ("terbuka" if utils.port_open(port, host) else "tertutup/tidak terjangkau"))


def menu() -> None:
    actions = {
        "1": ("Interface & routing", interfaces),
        "2": ("DNS resolver sistem", resolvers),
        "3": ("DNS lookup (forward)", dns_lookup),
        "4": ("DNS lookup (reverse / PTR)", reverse_lookup),
        "5": ("Ping", ping),
        "6": ("Cek port TCP", check_port),
    }
    ui.section("NETWORK DIAGNOSTICS")
    ui.menu([(k, a[0]) for k, a in actions.items()] + [("0", "Kembali")])
    c = input("Select option: ").strip()
    if c in actions:
        print()
        actions[c][1]()
