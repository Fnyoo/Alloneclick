"""Konfigurator Fail2ban: jail sshd + nginx-http-auth."""
from __future__ import annotations

from .. import ui, utils

JAIL = """\
# Dikelola oleh SERVERKIT
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s

[nginx-http-auth]
enabled = true
"""


def configure() -> None:
    ui.banner("FAIL2BAN JAIL")
    ports = ui.ask("Port SSH yang diawasi", "22")
    bantime = ui.ask("Bantime", "1h")
    maxretry = ui.ask("Max retry", "5")

    content = (JAIL
               .replace("bantime  = 1h", f"bantime  = {bantime}")
               .replace("maxretry = 5", f"maxretry = {maxretry}")
               .replace("port    = ssh", f"port    = {ports}"))

    tx = utils.Transaction()
    tx.write(utils.p("/etc/fail2ban/jail.local"), content)

    r = utils.run(["fail2ban-client", "-t"])
    if r.returncode != 0:
        ui.error("fail2ban-client -t gagal:")
        print((r.stdout or "").strip())
        tx.rollback()
        return
    ui.ok("Konfigurasi valid.")
    utils.systemctl("enable", "fail2ban")
    utils.systemctl("restart", "fail2ban")
    ui.ok("Fail2ban aktif.")