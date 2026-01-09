"""
Weekly report generator.

Aggregates data from all monitors and service clients
to create a comprehensive weekly digest for Discord.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from discord_client import (
    DiscordClient,
    EmbedColor,
    build_embed,
    format_bytes,
    format_percentage,
    format_temperature,
    format_uptime,
    create_progress_bar,
    create_colored_progress_bar,
    create_storage_bar,
)

if TYPE_CHECKING:
    from config import Config
    from monitors.system import SystemMonitor
    from monitors.docker_monitor import DockerMonitor
    from monitors.services.radarr import RadarrClient
    from monitors.services.sonarr import SonarrClient
    from monitors.services.immich import ImmichClient
    from monitors.services.jellyfin import JellyfinClient
    from monitors.services.qbittorrent import QBittorrentClient
    from alerts.manager import AlertManager


logger = logging.getLogger(__name__)


class WeeklyReportGenerator:
    """
    Generates and sends weekly digest reports to Discord.
    
    Collects data from:
    - System monitor (CPU, RAM, disk, temps)
    - Docker monitor (container health)
    - Media services (Radarr, Sonarr, Immich, Jellyfin, qBittorrent)
    - Alert manager (alert statistics)
    """
    
    def __init__(
        self,
        config: "Config",
        discord: DiscordClient,
        alert_manager: "AlertManager",
        system_monitor: "SystemMonitor | None" = None,
        docker_monitor: "DockerMonitor | None" = None,
        radarr: "RadarrClient | None" = None,
        sonarr: "SonarrClient | None" = None,
        immich: "ImmichClient | None" = None,
        jellyfin: "JellyfinClient | None" = None,
        qbittorrent: "QBittorrentClient | None" = None,
    ):
        self.config = config
        self.discord = discord
        self.alert_manager = alert_manager
        
        # Monitors
        self.system_monitor = system_monitor
        self.docker_monitor = docker_monitor
        
        # Service clients
        self.radarr = radarr
        self.sonarr = sonarr
        self.immich = immich
        self.jellyfin = jellyfin
        self.qbittorrent = qbittorrent
    
    async def generate_and_send(self) -> bool:
        """
        Generate the weekly report and send to Discord.
        
        Returns:
            True if report was sent successfully
        """
        logger.info("Generating weekly report...")
        
        try:
            embeds = []
            
            # Header embed
            embeds.append(self._build_header_embed())
            
            # System overview
            if self.system_monitor:
                system_embed = await self._build_system_embed()
                if system_embed:
                    embeds.append(system_embed)
            
            # Docker status
            if self.docker_monitor:
                docker_embed = await self._build_docker_embed()
                if docker_embed:
                    embeds.append(docker_embed)
            
            # Media stack (Radarr + Sonarr)
            media_embed = await self._build_media_embed()
            if media_embed:
                embeds.append(media_embed)
            
            # Immich
            if self.immich and self.immich.is_configured:
                immich_embed = await self._build_immich_embed()
                if immich_embed:
                    embeds.append(immich_embed)
            
            # Jellyfin
            if self.jellyfin and self.jellyfin.is_configured:
                jellyfin_embed = await self._build_jellyfin_embed()
                if jellyfin_embed:
                    embeds.append(jellyfin_embed)
            
            # Downloads (qBittorrent)
            if self.qbittorrent and self.qbittorrent.is_configured:
                downloads_embed = await self._build_downloads_embed()
                if downloads_embed:
                    embeds.append(downloads_embed)
            
            # Alert summary
            alerts_embed = self._build_alerts_embed()
            if alerts_embed:
                embeds.append(alerts_embed)
            
            # Send report
            success = await self.discord.send_message(embeds=embeds)
            
            if success:
                logger.info("Weekly report sent successfully")
            else:
                logger.error("Failed to send weekly report")
            
            return success
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}", exc_info=True)
            return False
    
    def _build_header_embed(self) -> dict[str, Any]:
        """Build the report header embed."""
        now = datetime.now()
        
        return build_embed(
            title="📊 Weekly Server Report",
            description=f"Report for week ending {now.strftime('%B %d, %Y')}",
            color=EmbedColor.PURPLE,
            footer="Unraid Monitor - Weekly Digest",
        )
    
    async def _build_system_embed(self) -> dict[str, Any] | None:
        """Build system overview embed."""
        if not self.system_monitor:
            return None
        
        try:
            data = await self.system_monitor.get_report_data()
            
            # Build storage info
            disk = data.get("disk", {})
            storage_lines = [
                f"Array: {disk.get('main_used_tb', 0):.2f} / {disk.get('main_total_tb', 0):.2f} TB ({disk.get('main_percent', 0):.0f}%)",
            ]
            if disk.get("cache_percent") is not None:
                storage_lines.append(
                    f"Cache: {disk.get('cache_total_gb', 0) - disk.get('cache_free_gb', 0):.0f} / {disk.get('cache_total_gb', 0):.0f} GB ({disk.get('cache_percent', 0):.0f}%)"
                )
            
            fields = [
                {
                    "name": "💻 CPU",
                    "value": f"Avg: {data['cpu']['average']:.1f}%\nCores: {data['cpu']['cores']} ({data['cpu']['threads']} threads)",
                    "inline": True,
                },
                {
                    "name": "🧠 Memory",
                    "value": f"{data['memory']['used_gb']:.1f} / {data['memory']['total_gb']:.1f} GB\nAvailable: {data['memory']['available_gb']:.1f} GB",
                    "inline": True,
                },
                {
                    "name": "💾 Storage",
                    "value": "\n".join(storage_lines),
                    "inline": True,
                },
            ]
            
            # Add temperature if available
            if data.get("temperature", {}).get("max", 0) > 0:
                fields.append({
                    "name": "🌡️ Max Temp",
                    "value": format_temperature(data["temperature"]["max"]),
                    "inline": True,
                })
            
            # Add uptime
            if data.get("uptime_seconds", 0) > 0:
                fields.append({
                    "name": "⏱️ Uptime",
                    "value": format_uptime(data["uptime_seconds"]),
                    "inline": True,
                })
            
            return build_embed(
                title="🖥️ System Overview",
                color=EmbedColor.INFO,
                fields=fields,
                timestamp=False,
            )
            
        except Exception as e:
            logger.error(f"Error building system embed: {e}")
            return None
    
    async def _build_docker_embed(self) -> dict[str, Any] | None:
        """Build Docker status embed."""
        if not self.docker_monitor:
            return None
        
        try:
            data = await self.docker_monitor.get_report_data()
            
            if not data.get("available"):
                return None
            
            summary = data.get("summary", {})
            
            # Determine overall status
            if summary.get("unhealthy", 0) > 0 or summary.get("stopped", 0) > 0:
                status_emoji = "⚠️"
                color = EmbedColor.WARNING
            else:
                status_emoji = "✅"
                color = EmbedColor.SUCCESS
            
            fields = [
                {
                    "name": "Total",
                    "value": str(summary.get("total", 0)),
                    "inline": True,
                },
                {
                    "name": "Running",
                    "value": f"✅ {summary.get('running', 0)}",
                    "inline": True,
                },
                {
                    "name": "Stopped",
                    "value": f"🔴 {summary.get('stopped', 0)}",
                    "inline": True,
                },
            ]
            
            if summary.get("unhealthy", 0) > 0:
                fields.append({
                    "name": "Unhealthy",
                    "value": f"⚠️ {summary.get('unhealthy', 0)}",
                    "inline": True,
                })
            
            # Top CPU consumers
            top_cpu = data.get("top_cpu_containers", [])
            if top_cpu:
                cpu_list = "\n".join(f"• {c['name']}: {c['cpu']}" for c in top_cpu[:3])
                fields.append({
                    "name": "Top CPU Usage",
                    "value": cpu_list,
                    "inline": False,
                })
            
            return build_embed(
                title=f"🐳 Docker Status {status_emoji}",
                color=color,
                fields=fields,
                timestamp=False,
            )
            
        except Exception as e:
            logger.error(f"Error building Docker embed: {e}")
            return None
    
    async def _build_media_embed(self) -> dict[str, Any] | None:
        """Build media stack embed (Radarr + Sonarr)."""
        fields = []
        
        # Radarr stats
        if self.radarr and self.radarr.is_configured:
            try:
                radarr_data = await self.radarr.get_stats_for_report()
                if radarr_data.get("available"):
                    fields.append({
                        "name": "🎬 Movies (Radarr)",
                        "value": (
                            f"Library: {radarr_data['total_movies']}\n"
                            f"Downloaded: {radarr_data['movies_with_files']}\n"
                            f"This week: +{radarr_data['downloaded_this_week']}\n"
                            f"Queue: {radarr_data['queue_count']}"
                        ),
                        "inline": True,
                    })
            except Exception as e:
                logger.error(f"Error getting Radarr stats: {e}")
        
        # Sonarr stats
        if self.sonarr and self.sonarr.is_configured:
            try:
                sonarr_data = await self.sonarr.get_stats_for_report()
                if sonarr_data.get("available"):
                    # Build upcoming episodes text
                    upcoming_text = f"{sonarr_data['upcoming_episodes']} episodes this week"
                    upcoming_details = sonarr_data.get("upcoming_details", [])
                    if upcoming_details:
                        upcoming_text = "\n".join(
                            f"• {ep['series']} S{ep['season']:02d}E{ep['episode']:02d}"
                            for ep in upcoming_details[:3]
                        )
                        if sonarr_data['upcoming_episodes'] > 3:
                            upcoming_text += f"\n...+{sonarr_data['upcoming_episodes'] - 3} more"
                    
                    fields.append({
                        "name": "📺 TV Shows (Sonarr)",
                        "value": (
                            f"Series: {sonarr_data['total_series']}\n"
                            f"Episodes: {sonarr_data['episodes_with_files']}/{sonarr_data['total_episodes']}\n"
                            f"This week: +{sonarr_data['downloaded_this_week']}"
                        ),
                        "inline": True,
                    })
                    
                    # Add upcoming as separate field if there are episodes
                    if sonarr_data['upcoming_episodes'] > 0:
                        fields.append({
                            "name": "📅 Upcoming Episodes",
                            "value": upcoming_text,
                            "inline": True,
                        })
            except Exception as e:
                logger.error(f"Error getting Sonarr stats: {e}")
        
        if not fields:
            return None
        
        return build_embed(
            title="🎬 Media Stack",
            color=0xE74C3C,  # Red - matches Radarr/Sonarr branding
            fields=fields,
            timestamp=False,
        )
    
    async def _build_immich_embed(self) -> dict[str, Any] | None:
        """Build Immich stats embed."""
        if not self.immich or not self.immich.is_configured:
            return None
        
        try:
            data = await self.immich.get_stats_for_report()
            
            if not data.get("available"):
                return None
            
            fields = [
                {
                    "name": "📷 Photos",
                    "value": f"{data['total_photos']:,}",
                    "inline": True,
                },
                {
                    "name": "🎥 Videos",
                    "value": f"{data['total_videos']:,}",
                    "inline": True,
                },
                {
                    "name": "💾 Storage",
                    "value": f"{data['storage_used_gb']:.1f} GB",
                    "inline": True,
                },
            ]
            
            if data.get("user_count", 0) > 0:
                fields.append({
                    "name": "👥 Users",
                    "value": str(data["user_count"]),
                    "inline": True,
                })
            
            return build_embed(
                title="📷 Immich Photos",
                color=0x4250AF,  # Immich brand color
                fields=fields,
                timestamp=False,
            )
            
        except Exception as e:
            logger.error(f"Error building Immich embed: {e}")
            return None
    
    async def _build_jellyfin_embed(self) -> dict[str, Any] | None:
        """Build Jellyfin stats embed."""
        if not self.jellyfin or not self.jellyfin.is_configured:
            return None
        
        try:
            data = await self.jellyfin.get_stats_for_report()
            
            if not data.get("available"):
                return None
            
            fields = [
                {
                    "name": "🎬 Movies",
                    "value": f"{data['movie_count']:,}",
                    "inline": True,
                },
                {
                    "name": "📺 Series",
                    "value": f"{data['series_count']:,}",
                    "inline": True,
                },
                {
                    "name": "👥 Users",
                    "value": str(data["user_count"]),
                    "inline": True,
                },
            ]
            
            # Recently added movies
            recent_movies = data.get("recent_movies", [])
            if recent_movies:
                movies_text = "\n".join(
                    f"• {m['name']}" + (f" ({m['year']})" if m.get('year') else "")
                    for m in recent_movies[:4]
                )
                fields.append({
                    "name": "🆕 Recently Added Movies",
                    "value": movies_text,
                    "inline": True,
                })
            
            # Recently added series
            recent_series = data.get("recent_series", [])
            if recent_series:
                series_text = "\n".join(
                    f"• {s['name']}" + (f" ({s['year']})" if s.get('year') else "")
                    for s in recent_series[:4]
                )
                fields.append({
                    "name": "🆕 Recently Added Series",
                    "value": series_text,
                    "inline": True,
                })
            
            # Active streams
            if data.get("active_streams", 0) > 0:
                now_playing_text = f"🔴 {data['active_streams']} active"
                if data.get("now_playing"):
                    now_playing_text += "\n" + "\n".join(
                        f"• {p['user']}: {p['title']}"
                        for p in data["now_playing"][:3]
                    )
                fields.append({
                    "name": "Currently Playing",
                    "value": now_playing_text,
                    "inline": False,
                })
            
            return build_embed(
                title="🎥 Jellyfin Library",
                color=0x00A4DC,  # Jellyfin brand color
                fields=fields,
                timestamp=False,
            )
            
        except Exception as e:
            logger.error(f"Error building Jellyfin embed: {e}")
            return None
    
    async def _build_downloads_embed(self) -> dict[str, Any] | None:
        """Build downloads (qBittorrent) embed."""
        if not self.qbittorrent or not self.qbittorrent.is_configured:
            return None
        
        try:
            data = await self.qbittorrent.get_stats_for_report()
            
            if not data.get("available"):
                return None
            
            fields = [
                {
                    "name": "📥 Downloading",
                    "value": str(data["downloading"]),
                    "inline": True,
                },
                {
                    "name": "📤 Seeding",
                    "value": str(data["seeding"]),
                    "inline": True,
                },
                {
                    "name": "✅ Completed",
                    "value": str(data["completed"]),
                    "inline": True,
                },
                {
                    "name": "⏸️ Paused",
                    "value": str(data.get("paused", 0)),
                    "inline": True,
                },
                {
                    "name": "📊 Ratio",
                    "value": f"{data.get('ratio', 0):.2f}",
                    "inline": True,
                },
                {
                    "name": "📈 Total Transfer",
                    "value": f"⬇️ {data['total_downloaded_tb']:.2f} TB\n⬆️ {data['total_uploaded_tb']:.2f} TB",
                    "inline": True,
                },
            ]
            
            # Recently completed torrents
            recently_completed = data.get("recently_completed", [])
            if recently_completed:
                completed_text = "\n".join(
                    f"• {t['name'][:40]}{'...' if len(t['name']) > 40 else ''}"
                    for t in recently_completed[:4]
                )
                fields.append({
                    "name": "🆕 Recently Completed",
                    "value": completed_text,
                    "inline": False,
                })
            
            return build_embed(
                title="📥 Downloads (qBittorrent)",
                color=0x2F67BA,  # qBittorrent brand color
                fields=fields,
                timestamp=False,
            )
            
        except Exception as e:
            logger.error(f"Error building downloads embed: {e}")
            return None
    
    def _build_alerts_embed(self) -> dict[str, Any] | None:
        """Build alerts summary embed."""
        try:
            stats = self.alert_manager.get_statistics()
            
            active = stats.get("active_alerts", 0)
            total = stats.get("total_triggers", 0)
            by_level = stats.get("by_level", {})
            
            # Determine status color
            if by_level.get("critical", 0) > 0:
                color = EmbedColor.CRITICAL
                status = "🚨 Critical issues present"
            elif by_level.get("warning", 0) > 0:
                color = EmbedColor.WARNING
                status = "⚠️ Warnings present"
            elif active > 0:
                color = EmbedColor.WARNING
                status = "⚠️ Active alerts"
            else:
                color = EmbedColor.SUCCESS
                status = "✅ All systems normal"
            
            fields = [
                {
                    "name": "Status",
                    "value": status,
                    "inline": True,
                },
                {
                    "name": "Active Alerts",
                    "value": str(active),
                    "inline": True,
                },
                {
                    "name": "Total This Week",
                    "value": str(total),
                    "inline": True,
                },
            ]
            
            return build_embed(
                title="🔔 Alert Summary",
                color=color,
                fields=fields,
                timestamp=False,
            )
            
        except Exception as e:
            logger.error(f"Error building alerts embed: {e}")
            return None
