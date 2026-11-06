"""Konfigurator WireGuard: generate keypair + interface wg0 + NAT via iptables."""
from __future__ import annotations

import subprocess

from .. import ui, utils, validators as v

TEMPLATE = """\
# Dikelola oleh SERVERKIT
[Interface]
Address = {address}/24
ListenPort = {port}
PrivateKey = {privkey}
PostUp   = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o {wan} -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o {wan} -j MASQUERADE
"""


def _genkey() -> tuple[str, str]:
    """Kembalikan (private, public). Private lewat wg genkey, public lewat wg pubkey."""
    priv = utils.out(["wg", "genkey"])
    if not priv:
        return "", ""
    try:
        pub_proc = subprocess.run(
            ["wg", "pubkey"],
            input=priv,
            text=True,
            capture_output=True,
        )
        pub = pub_proc.stdout.strip()
    except FileNotFoundError:
        pub = ""
    return priv, pub


def configure() -> None:
    ui.banner("WIREGUARD VPN")
    address = ui.ask("IP interface wg0 (mis. 10.10.0.1)", "10.10.0.1", v.ipv4)
    port = ui.ask("Listen port", "51820", v.port)
    wan = ui.ask("Interface WAN (untuk NAT)", "eth0")

    if not ui.confirm("Buat keypair baru?", default=True):
        ui.warn("Dibatalkan.")
        return
    priv, pub = _genkey()
    if not priv:
        ui.error("Gagal generate key (paket wireguard-tools belum terpasang?).")
        return
    print(f"\nPublic key (bagikan ke client): {pub}\n")
    ui.info("Private key akan ditulis ke /etc/wireguard/wg0.conf (mode 600).")

    tx = utils.Transaction()
    target = utils.p("/etc/wireguard/wg0.conf")
    tx.write(target, TEMPLATE.format(address=address, port=port, privkey=priv, wan=wan),
             mode=0o600)

    utils.run(["sysctl", "-w", "net.ipv4.ip_forward=1"])
    r = utils.run(["wg", "quick", "up", "wg0"])
    if r.returncode != 0:
        ui.error("wg-quick up gagal:")
        print((r.stdout or "").strip())
        tx.rollback()
        return
    utils.systemctl("enable", "wg-quick@wg0")
    utils.open_firewall([f"{port}/udp"])
    ui.ok(f"WireGuard aktif di {address}:{port} (WAN: {wan}).")