"""DHCP: Kea DHCP, ISC DHCP."""
from .base import Service, ServiceCategory


class DhcpServices(ServiceCategory):
    name = "DHCP"

    services = (
        Service("kea-dhcp4", "Kea DHCPv4", "DHCP", ("kea-dhcp4-server",),
                ("kea-dhcp4-server",), 67, ("/etc/kea",),
                description="DHCP server modern (pengganti ISC DHCP)"),
        Service("isc-dhcp", "ISC DHCP", "DHCP", ("isc-dhcp-server",),
                ("isc-dhcp-server",), 67, ("/etc/dhcp",),
                description="DHCP server klasik (deprecated)"),
    )