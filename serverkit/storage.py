"""Storage & Cloud: Nextcloud, MinIO, Syncthing, Rclone."""
from .base import Service, ServiceCategory


class StorageServices(ServiceCategory):
    name = "Storage"

    services = (
        Service("nextcloud", "Nextcloud", "Storage", ("nextcloud",), ("apache2",),
                80, ("/etc/nextcloud", "/var/lib/nextcloud"), external_repo=True,
                description="Self-hosted file sync"),
        Service("minio", "MinIO", "Storage", ("minio",), ("minio",), 9000,
                ("/etc/minio",), external_repo=True,
                description="S3-compatible object storage"),
        Service("syncthing", "Syncthing", "Storage", ("syncthing",),
                ("syncthing@syncthing",), 8384, ("/etc/syncthing",),
                external_repo=True, description="Peer-to-peer file sync"),
        Service("rclone", "Rclone", "Storage", ("rclone",), (), None,
                description="Cloud sync CLI (tanpa daemon)"),
    )