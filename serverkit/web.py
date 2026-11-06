"""Web Server: Nginx, Apache2, PHP-FPM, Caddy, Lighttpd, OpenLiteSpeed."""
from .base import Service, ServiceCategory


class WebServices(ServiceCategory):
    name = "Web"

    services = (
        Service("nginx", "Nginx", "Web", ("nginx",), ("nginx",), 80,
                ("/etc/nginx",), ("nginx", "-t"), ("apache2",),
                description="Web server & reverse proxy"),
        Service("apache2", "Apache HTTP Server", "Web", ("apache2",), ("apache2",), 80,
                ("/etc/apache2",), ("apache2ctl", "configtest"), ("nginx",),
                description="Web server klasik"),
        Service("php-fpm", "PHP-FPM 8.3", "Web",
                ("php8.3-fpm", "php8.3-cli", "php8.3-mysql"),
                ("php8.3-fpm",), 9000, ("/etc/php",), ("php-fpm8.3", "-t"),
                description="PHP FastCGI Process Manager"),
        Service("caddy", "Caddy", "Web", ("caddy",), ("caddy",), 80,
                ("/etc/caddy",),
                ("caddy", "validate", "--config", "/etc/caddy/Caddyfile"),
                ("nginx", "apache2"), external_repo=True,
                description="Web server dengan HTTPS otomatis"),
        Service("lighttpd", "Lighttpd", "Web", ("lighttpd",), ("lighttpd",), 80,
                ("/etc/lighttpd",),
                ("lighttpd", "-tt", "-f", "/etc/lighttpd/lighttpd.conf"),
                ("nginx", "apache2", "caddy"),
                description="Web server ringan"),
        Service("openlitespeed", "OpenLiteSpeed", "Web", ("openlitespeed",),
                ("lshttpd",), 8088, ("/usr/local/lsws/conf",), external_repo=True,
                description="Web server performa tinggi"),
    )