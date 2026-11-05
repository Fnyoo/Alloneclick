"""Konfigurator Nginx: membuat virtual host (server block) lengkap dengan docroot."""
from __future__ import annotations

from .. import ui, utils, validators as v

TEMPLATE = """\
# Dikelola oleh SERVERKIT
server {{
    listen {port};
    listen [::]:{port};
    server_name {domain} www.{domain};

    root {root};
    index index.html index.htm;

    access_log /var/log/nginx/{domain}.access.log;
    error_log  /var/log/nginx/{domain}.error.log;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
"""

INDEX_HTML = "<!doctype html><title>{domain}</title><h1>{domain} berjalan di Nginx</h1>\n"


def configure() -> None:
    ui.banner("NGINX VIRTUAL HOST")
    domain = ui.ask("Domain", None, v.domain)
    root = ui.ask("Document root", f"/var/www/{domain}")
    port = ui.ask("Port", "80", v.port)
    disable_default = ui.confirm("Nonaktifkan site 'default'?", default=False)

    print()
    if not ui.confirm("Apakah konfigurasi sudah benar?"):
        ui.warn("Dibatalkan.")
        return

    tx = utils.Transaction()
    avail = utils.p(f"/etc/nginx/sites-available/{domain}")
    enabled = utils.p(f"/etc/nginx/sites-enabled/{domain}")
    tx.write(avail, TEMPLATE.format(domain=domain, root=root, port=port))

    docroot = utils.p(root)
    if not utils.DRY_RUN or utils.PREFIX:
        docroot.mkdir(parents=True, exist_ok=True)
        index = docroot / "index.html"
        if not index.exists():
            index.write_text(INDEX_HTML.format(domain=domain))
        enabled.parent.mkdir(parents=True, exist_ok=True)
        if enabled.is_symlink() or enabled.exists():
            enabled.unlink()
        enabled.symlink_to(avail if utils.PREFIX else f"/etc/nginx/sites-available/{domain}")
        if disable_default:
            utils.p("/etc/nginx/sites-enabled/default").unlink(missing_ok=True)

    r = utils.run(["nginx", "-t"])
    if r.returncode != 0:
        ui.error("nginx -t gagal:")
        print((r.stdout or "").strip())
        tx.rollback()
        if not utils.DRY_RUN or utils.PREFIX:
            enabled.unlink(missing_ok=True)
        return
    ui.ok("nginx -t: OK")
    utils.systemctl("reload", "nginx")
    ui.ok(f"Virtual host {domain} aktif (root: {root}).")
    utils.open_firewall(["Nginx Full"] if port == "80" else [port])
