"""Konfigurator vsftpd: user FTP terisolasi + passive port range."""
from __future__ import annotations

from .. import ui, utils, validators as v

CONF = """\
# Dikelola oleh SERVERKIT
listen=YES
listen_ipv6=NO
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
chroot_local_user=YES
allow_writeable_chroot=YES
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=40100
userlist_enable=YES
userlist_file=/etc/vsftpd.userlist
userlist_deny=NO
"""


def configure() -> None:
    ui.banner("vsftpd FTP SERVER")
    user = ui.ask("User FTP", None, v.label)

    tx = utils.Transaction()
    tx.write(utils.p("/etc/vsftpd.conf"), CONF)
    tx.write(utils.p("/etc/vsftpd.userlist"), user + "\n")

    if not utils.run(["id", user]).returncode == 0:
        if ui.confirm(f"User '{user}' belum ada. Buat dengan home /srv/ftp/{user}?", default=True):
            utils.run(["useradd", "-m", "-d", f"/srv/ftp/{user}", "-s", "/usr/sbin/nologin", user])
            ui.warn(f"Set password: sudo passwd {user}")

    r = utils.run(["vsftpd", "-t"])
    if r.returncode != 0:
        ui.error("vsftpd -t gagal:")
        print((r.stdout or "").strip())
        tx.rollback()
        return
    ui.ok("vsftpd -t: OK")
    utils.systemctl("restart", "vsftpd")
    utils.open_firewall(["21", "40000:40100/tcp"])
    ui.ok("vsftpd dikonfigurasi.")