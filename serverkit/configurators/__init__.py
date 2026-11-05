"""Registry konfigurator interaktif. key = Service.key, value = fungsi configure()."""
from . import bind9, nginx

CONFIGURATORS = {
    "bind9": bind9.configure,
    "nginx": nginx.configure,
}
