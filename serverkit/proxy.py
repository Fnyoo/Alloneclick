"""Proxy & Tunnel: HAProxy, Squid, Traefik, Cloudflared."""
from .services.base import Service, ServiceCategory


class ProxyServices(ServiceCategory):
    name = "Proxy"

    services = (
        Service("haproxy", "HAProxy", "Proxy", ("haproxy",), ("haproxy",), 80,
                ("/etc/haproxy",),
                ("haproxy", "-c", "-f", "/etc/haproxy/haproxy.cfg"),
                description="Load balancer TCP/HTTP"),
        Service("squid", "Squid", "Proxy", ("squid",), ("squid",), 3128,
                ("/etc/squid",),
                ("squid", "-k", "parse", "/etc/squid/squid.conf"),
                description="Caching HTTP proxy"),
        Service("traefik", "Traefik", "Proxy", ("traefik",), ("traefik",), 80,
                ("/etc/traefik",), external_repo=True,
                description="Reverse proxy modern"),
        Service("cloudflared", "Cloudflared", "Proxy", ("cloudflared",),
                ("cloudflared",), None, ("/etc/cloudflared",), external_repo=True,
                description="Cloudflare Tunnel"),
    )