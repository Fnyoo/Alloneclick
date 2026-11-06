"""DNS: BIND9, dnsmasq, Unbound, PowerDNS."""
from .services.base import Service, ServiceCategory


class DnsServices(ServiceCategory):
    name = "DNS"

    services = (
        Service("bind9", "BIND9 DNS Server", "DNS",
                ("bind9", "bind9-utils", "dnsutils"),
                ("bind9",), 53, ("/etc/bind",), ("named-checkconf",),
                ("dnsmasq", "unbound", "powerdns"),
                description="Authoritative DNS server"),
        Service("dnsmasq", "dnsmasq", "DNS", ("dnsmasq",), ("dnsmasq",), 53,
                ("/etc/dnsmasq.conf", "/etc/dnsmasq.d"), ("dnsmasq", "--test"),
                ("bind9", "unbound", "powerdns"),
                description="DNS forwarder + DHCP ringan"),
        Service("unbound", "Unbound", "DNS", ("unbound",), ("unbound",), 53,
                ("/etc/unbound",), ("unbound-checkconf",),
                ("bind9", "dnsmasq", "powerdns"),
                description="Recursive/validating DNS resolver"),
        Service("powerdns", "PowerDNS", "DNS", ("pdns-server",), ("pdns",), 53,
                ("/etc/powerdns",), ("pdns_control", "cycle"),
                ("bind9", "dnsmasq", "unbound"), external_repo=True,
                description="DNS server modular"),
    )