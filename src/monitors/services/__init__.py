"""Service clients for media stack APIs."""

from monitors.services.radarr import RadarrClient
from monitors.services.sonarr import SonarrClient
from monitors.services.immich import ImmichClient
from monitors.services.jellyfin import JellyfinClient
from monitors.services.qbittorrent import QBittorrentClient

__all__ = [
    "RadarrClient",
    "SonarrClient",
    "ImmichClient",
    "JellyfinClient",
    "QBittorrentClient",
]
