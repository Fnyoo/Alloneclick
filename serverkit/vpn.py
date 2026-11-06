"""VPN: WireGuard, OpenVPN, StrongSwan."""
from .base import Service, ServiceCategory


class VpnServices(ServiceCategory):
    name = "VPN"

    services = (
        Service("wireguard", "WireGuard", "VPN", ("wireguard", "wireguard-tools"),
                ("wg-quick@wg0",), 51820, ("/etc/wireguard",), ("wg", "show"),
                description="VPN modern berbasis kernel"),
        Service("openvpn", "OpenVPN", "VPN", ("openvpn",), ("openvpn@server",), 1194,
                ("/etc/openvpn",), description="VPN TLS-based"),
        Service("strongswan", "StrongSwan", "VPN", ("strongswan",), ("strongswan",),
                500, ("/etc/ipsec.conf", "/etc/ipsec.d"), ("ipsec", "statusall"),
                description="IPsec VPN"),
    )