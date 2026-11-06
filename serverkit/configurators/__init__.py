"""Registry konfigurator interaktif. key = Service.key, value = fungsi configure()."""
from . import bind9, fail2ban, nginx, phpfpm, vsftpd, wireguard

CONFIGURATORS = {
    "bind9": bind9.configure,
    "nginx": nginx.configure,
    "php-fpm": phpfpm.configure,
    "vsftpd": vsftpd.configure,
    "wireguard": wireguard.configure,
    "fail2ban": fail2ban.configure,
}