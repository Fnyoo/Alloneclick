"""Security: UFW, Fail2ban, AppArmor, Suricata, Snort, ClamAV."""
from .base import Service, ServiceCategory


class SecurityServices(ServiceCategory):
    name = "Security"

    services = (
        Service("ufw", "UFW Firewall", "Security", ("ufw",), ("ufw",), None,
                ("/etc/ufw",), description="Uncomplicated Firewall"),
        Service("fail2ban", "Fail2ban", "Security", ("fail2ban",), ("fail2ban",),
                None, ("/etc/fail2ban",), ("fail2ban-client", "-t"),
                description="Brute-force protection"),
        Service("apparmor", "AppArmor", "Security", ("apparmor", "apparmor-utils"),
                ("apparmor",), None, ("/etc/apparmor.d",),
                description="MAC security"),
        Service("suricata", "Suricata", "Security", ("suricata",), ("suricata",),
                None, ("/etc/suricata",),
                ("suricata", "-T", "-c", "/etc/suricata/suricata.yaml"),
                external_repo=True, description="IDS/IPS"),
        Service("snort", "Snort", "Security", ("snort",), ("snort",), None,
                ("/etc/snort",),
                ("snort", "-T", "-c", "/etc/snort/snort.conf"),
                external_repo=True, description="IDS klasik"),
        Service("clamav", "ClamAV", "Security", ("clamav", "clamav-daemon"),
                ("clamav-daemon", "clamav-freshclam"), 3310, ("/etc/clamav",),
                description="Antivirus open source"),
    )