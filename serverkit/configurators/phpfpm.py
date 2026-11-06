"""Konfigurator PHP-FPM: membuat pool aplikasi terpisah + user sistem."""
from __future__ import annotations

from .. import ui, utils, validators as v

POOL_TEMPLATE = """\
; Dikelola oleh SERVERKIT
[{pool}]
user = {user}
group = {user}
listen = /run/php/php8.3-fpm-{pool}.sock
listen.owner = www-data
listen.group = www-data
listen.mode = 0660

pm = dynamic
pm.max_children = 10
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
"""


def configure() -> None:
    ui.banner("PHP-FPM POOL")
    pool = ui.ask("Nama pool", None, v.label)
    user = ui.ask("User sistem", pool, v.label)
    if not utils.run(["id", user]).returncode == 0:
        if ui.confirm(f"User '{user}' belum ada. Buat?", default=True):
            utils.run(["useradd", "-r", "-s", "/usr/sbin/nologin", user])

    tx = utils.Transaction()
    target = utils.p(f"/etc/php/8.3/fpm/pool.d/{pool}.conf")
    tx.write(target, POOL_TEMPLATE.format(pool=pool, user=user))

    r = utils.run(["php-fpm8.3", "-t"])
    if r.returncode != 0:
        ui.error("php-fpm -t gagal:")
        print((r.stdout or "").strip())
        tx.rollback()
        return
    ui.ok("php-fpm -t: OK")
    utils.systemctl("reload", "php8.3-fpm")
    ui.ok(f"Pool PHP-FPM '{pool}' aktif (socket: /run/php/php8.3-fpm-{pool}.sock).")