"""Media Server: Jellyfin, Plex, Emby, Navidrome, Subsonic, Audiobookshelf, DLNA."""
from .services.base import Service, ServiceCategory


class MediaServices(ServiceCategory):
    name = "Media"

    services = (
        Service("jellyfin", "Jellyfin", "Media", ("jellyfin",), ("jellyfin",), 8096,
                ("/etc/jellyfin", "/var/lib/jellyfin"), external_repo=True,
                description="Media server open source (fork Emby)"),
        Service("plex", "Plex Media Server", "Media", ("plexmediaserver",),
                ("plexmediaserver",), 32400,
                ("/etc/plex", "/var/lib/plexmediaserver"), external_repo=True,
                description="Media server komersial"),
        Service("emby", "Emby", "Media", ("emby-server",), ("emby-server",), 8096,
                ("/etc/emby-server", "/var/lib/emby"), external_repo=True,
                description="Media server (fork Jellyfin)"),
        Service("navidrome", "Navidrome", "Media", ("navidrome",),
                ("navidrome",), 4533, ("/etc/navidrome",), external_repo=True,
                description="Music streaming server (Subsonic API)"),
        Service("subsonic", "Subsonic", "Media", ("subsonic",), ("subsonic",), 4040,
                ("/var/subsonic",), external_repo=True,
                description="Music streaming server klasik"),
        Service("audiobookshelf", "Audiobookshelf", "Media",
                ("audiobookshelf",), ("audiobookshelf",), 13378,
                ("/etc/audiobookshelf", "/var/lib/audiobookshelf"),
                external_repo=True,
                description="Audiobook & podcast server"),
        Service("dlna", "DLNA/UPnP (MiniDLNA)", "Media", ("minidlna",),
                ("minidlna",), 8200, ("/etc/minidlna.conf",),
                description="DLNA/UPnP media sharing"),
    )