"""Monitoring: Prometheus, Grafana, Netdata, Zabbix, Node Exporter."""
from .services.base import Service, ServiceCategory


class MonitoringServices(ServiceCategory):
    name = "Monitoring"

    services = (
        Service("prometheus", "Prometheus", "Monitoring", ("prometheus",),
                ("prometheus",), 9090, ("/etc/prometheus",),
                ("promtool", "check", "config", "/etc/prometheus/prometheus.yml"),
                description="Metrics collection & TSDB"),
        Service("grafana", "Grafana", "Monitoring", ("grafana",), ("grafana-server",),
                3000, ("/etc/grafana",), external_repo=True,
                description="Dashboard & visualisasi metrics"),
        Service("netdata", "Netdata", "Monitoring", ("netdata",), ("netdata",), 19999,
                ("/etc/netdata",), external_repo=True,
                description="Real-time monitoring"),
        Service("zabbix", "Zabbix", "Monitoring", ("zabbix-server-mysql",),
                ("zabbix-server",), 10051, ("/etc/zabbix",), external_repo=True,
                description="Enterprise monitoring"),
        Service("node-exporter", "Node Exporter", "Monitoring",
                ("prometheus-node-exporter",), ("prometheus-node-exporter",), 9100,
                description="Prometheus host metrics"),
    )