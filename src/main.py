"""
Unraid Monitor - Main entry point.

This is the main application that:
1. Loads configuration
2. Initializes all monitors and services
3. Sets up the scheduler for periodic checks
4. Starts Web UI for management
5. Runs until stopped
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Import version from package root
try:
    from __init__ import __version__
except ImportError:
    __version__ = "1.0.2"  # Fallback

# APScheduler imports (stable 3.x)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# Local imports
from config import load_config, setup_logging, Config
from discord_client import DiscordClient
from database import Database
from notifications import DiscordProvider, get_provider_from_config
from web import WebUI
from alerts.manager import AlertManager
from monitors.system import SystemMonitor
from monitors.docker_monitor import DockerMonitor
from monitors.services.radarr import RadarrClient
from monitors.services.sonarr import SonarrClient
from monitors.services.immich import ImmichClient
from monitors.services.jellyfin import JellyfinClient
from monitors.services.qbittorrent import QBittorrentClient
from reports.weekly import WeeklyReportGenerator


logger = logging.getLogger(__name__)


class UnraidMonitor:
    """
    Main application class.
    
    Coordinates all monitoring activities and scheduling.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self._running = False
        self._scheduler: AsyncIOScheduler | None = None
        self._web_task: asyncio.Task | None = None
        
        # Initialize Database
        data_dir = Path(os.environ.get("DATA_DIR", "/app/data"))
        self.db = Database(data_dir / "unraid_monitor.db")
        self.db.initialize()
        logger.info("Database initialized")
        
        # Initialize Discord client
        self.discord = DiscordClient(
            webhook_url=config.discord_webhook_url,
            user_id=config.discord_user_id or None,
            report_channel_id=config.discord_report_channel_id or None,
        )
        
        # Initialize alert manager
        self.alert_manager = AlertManager(
            discord_client=self.discord,
            config=config.alerts,
            state_file=Path("/app/data/alert_state.json"),
        )
        
        # Initialize monitors
        self.system_monitor = SystemMonitor(config, self.alert_manager)
        self.docker_monitor = DockerMonitor(config, self.alert_manager)
        
        # Initialize service clients
        self.radarr = RadarrClient(
            base_url=config.services.radarr.url,
            api_key=config.services.radarr.api_key,
        )
        self.sonarr = SonarrClient(
            base_url=config.services.sonarr.url,
            api_key=config.services.sonarr.api_key,
        )
        self.immich = ImmichClient(
            base_url=config.services.immich.url,
            api_key=config.services.immich.api_key,
        )
        self.jellyfin = JellyfinClient(
            base_url=config.services.jellyfin.url,
            api_key=config.services.jellyfin.api_key,
        )
        self.qbittorrent = QBittorrentClient(
            base_url=config.services.qbittorrent.url,
            username=config.services.qbittorrent.username,
            password=config.services.qbittorrent.password,
        )
        
        # Initialize report generator
        self.report_generator = WeeklyReportGenerator(
            config=config,
            discord=self.discord,
            alert_manager=self.alert_manager,
            system_monitor=self.system_monitor,
            docker_monitor=self.docker_monitor,
            radarr=self.radarr,
            sonarr=self.sonarr,
            immich=self.immich,
            jellyfin=self.jellyfin,
            qbittorrent=self.qbittorrent,
        )
        
        # Initialize Web UI
        web_port = int(os.environ.get("WEB_PORT", "8888"))
        web_password = os.environ.get("WEB_PASSWORD", "")
        self.web_ui = WebUI(
            host="0.0.0.0",
            port=web_port,
            password=web_password if web_password else None,
            database=self.db,
            get_system_stats=self._get_system_stats_for_web,
            get_docker_stats=self._get_docker_stats_for_web,
            get_services_status=self._get_services_status_for_web,
            trigger_report=self._trigger_report_for_web,
            send_test_notification=self._send_test_notification_for_web,
        )
        logger.info(f"Web UI configured on port {web_port}")
    
    # ==================== Web UI Callbacks ====================
    
    async def _get_system_stats_for_web(self) -> dict[str, Any]:
        """Get system stats for Web UI."""
        try:
            # Use last cached data or run a fresh check
            stats = self.system_monitor.get_last_data()
            if not stats:
                stats = await self.system_monitor.check()

            disks = stats.get("disks", [])
            main_disk = next(
                (d for d in disks if d.get("mountpoint") == "/mnt/user"),
                disks[0] if disks else {}
            )
            
            return {
                "cpu_percent": stats.get("cpu", {}).get("percent", 0),
                "memory_percent": stats.get("memory", {}).get("percent", 0),
                "memory_used": stats.get("memory", {}).get("used", 0),
                "memory_total": stats.get("memory", {}).get("total", 0),
                "disk_percent": main_disk.get("percent", 0),
                "disks": disks,
                "temperatures": stats.get("temperatures", {}),
                "timestamp": stats.get("timestamp", ""),
            }
        except Exception as e:
            logger.error(f"Error getting system stats for web: {e}")
            return {}
    
    async def _get_docker_stats_for_web(self) -> dict[str, Any]:
        """Get Docker stats for Web UI."""
        try:
            # Use last cached data or run a fresh check
            data = self.docker_monitor.get_last_data()
            if not data:
                data = await self.docker_monitor.check()
            
            containers = data.get("containers", [])
            summary = data.get("summary", {})
            
            return {
                "containers": [
                    {
                        "name": c.get("name", "Unknown"),
                        "status": c.get("status", "unknown"),
                        "image": c.get("image", ""),
                        "health": c.get("health", ""),
                        "uptime": c.get("uptime", ""),
                    }
                    for c in containers
                ],
                "total": summary.get("total", len(containers)),
                "running": summary.get("running", 0),
                "stopped": summary.get("stopped", 0),
                "unhealthy": summary.get("unhealthy", 0),
            }
        except Exception as e:
            logger.error(f"Error getting Docker stats for web: {e}")
            return {"containers": [], "total": 0, "running": 0}
    
    async def _get_services_status_for_web(self) -> dict[str, dict[str, Any]]:
        """Get services connection status for Web UI."""
        services = {}
        
        # Check each service
        service_checks = [
            ("radarr", self.radarr, self.config.services.radarr.is_configured),
            ("sonarr", self.sonarr, self.config.services.sonarr.is_configured),
            ("immich", self.immich, self.config.services.immich.is_configured),
            ("jellyfin", self.jellyfin, self.config.services.jellyfin.is_configured),
            ("qbittorrent", self.qbittorrent, self.config.services.qbittorrent.is_configured),
        ]
        
        for name, client, is_configured in service_checks:
            if not is_configured:
                services[name] = {"configured": False, "connected": False}
                continue
            
            try:
                # Try to get health from service
                connected = await client.health_check()
                services[name] = {"configured": True, "connected": connected}
            except Exception:
                services[name] = {"configured": True, "connected": False}
        
        return services
    
    async def _trigger_report_for_web(self) -> bool:
        """Trigger weekly report generation from Web UI."""
        try:
            await self._run_weekly_report()
            return True
        except Exception as e:
            logger.error(f"Error triggering report from web: {e}")
            return False
    
    async def _send_test_notification_for_web(self) -> bool:
        """Send test notification from Web UI."""
        try:
            await self.discord.send_message(
                title="🧪 Test Notification",
                description="This is a test notification from the Web UI.",
                color=0x00FF00,
            )
            return True
        except Exception as e:
            logger.error(f"Error sending test notification: {e}")
            return False
    
    # ==================== Core Methods ====================
    
    async def start(self) -> None:
        """Start the monitor."""
        logger.info("Starting Unraid Monitor...")
        self._running = True
        
        # Start Web UI in background
        self._web_task = asyncio.create_task(self.web_ui.start())
        logger.info(f"Web UI started on http://0.0.0.0:{self.web_ui.port}")
        
        # Send startup notification
        await self.discord.send_startup_message()
        
        # Create scheduler (APScheduler 3.x stable)
        self._scheduler = AsyncIOScheduler()
        
        # Schedule system monitoring
        self._scheduler.add_job(
            self._run_system_check,
            IntervalTrigger(seconds=self.config.monitoring.system_interval_seconds),
            id="system_monitor",
        )
        logger.info(f"System monitor scheduled every {self.config.monitoring.system_interval_seconds}s")
        
        # Schedule Docker monitoring
        self._scheduler.add_job(
            self._run_docker_check,
            IntervalTrigger(seconds=self.config.monitoring.docker_interval_seconds),
            id="docker_monitor",
        )
        logger.info(f"Docker monitor scheduled every {self.config.monitoring.docker_interval_seconds}s")
        
        # Schedule weekly report
        if self.config.weekly_report.enabled:
            # Map day name to cron day_of_week
            day_map = {
                "monday": "mon",
                "tuesday": "tue",
                "wednesday": "wed",
                "thursday": "thu",
                "friday": "fri",
                "saturday": "sat",
                "sunday": "sun",
            }
            day = day_map.get(self.config.weekly_report.day.lower(), "sun")
            
            self._scheduler.add_job(
                self._run_weekly_report,
                CronTrigger(
                    day_of_week=day,
                    hour=self.config.weekly_report.hour,
                    minute=self.config.weekly_report.minute,
                ),
                id="weekly_report",
            )
            logger.info(
                f"Weekly report scheduled for {self.config.weekly_report.day} "
                f"at {self.config.weekly_report.hour:02d}:{self.config.weekly_report.minute:02d}"
            )
        
        # Run initial checks
        logger.info("Running initial checks...")
        await self._run_system_check()
        await self._run_docker_check()
        
        # Start scheduler
        self._scheduler.start()
        logger.info("Unraid Monitor is running. Press Ctrl+C to stop.")
        
        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop the monitor gracefully."""
        logger.info("Stopping Unraid Monitor...")
        self._running = False
        
        # Stop scheduler
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
        
        # Stop Web UI
        if self._web_task and not self._web_task.done():
            await self.web_ui.stop()
            self._web_task.cancel()
            try:
                await self._web_task
            except asyncio.CancelledError:
                pass
            logger.info("Web UI stopped")
        
        # Send shutdown notification
        await self.discord.send_shutdown_message()
        
        # Close HTTP sessions
        await self.discord.close()
        await self.radarr.close()
        await self.sonarr.close()
        await self.immich.close()
        await self.jellyfin.close()
        await self.qbittorrent.close()
        
        logger.info("Unraid Monitor stopped.")
    
    async def _run_system_check(self) -> None:
        """Run system monitoring check."""
        try:
            logger.debug("Running system check...")
            await self.system_monitor.safe_check()
        except Exception as e:
            logger.error(f"Error in system check: {e}", exc_info=True)
    
    async def _run_docker_check(self) -> None:
        """Run Docker monitoring check."""
        try:
            logger.debug("Running Docker check...")
            await self.docker_monitor.safe_check()
        except Exception as e:
            logger.error(f"Error in Docker check: {e}", exc_info=True)
    
    async def _run_weekly_report(self) -> None:
        """Generate and send weekly report."""
        try:
            logger.info("Generating weekly report...")
            await self.report_generator.generate_and_send()
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}", exc_info=True)


async def main() -> None:
    """Main entry point."""
    # Load configuration
    try:
        config = load_config()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Setup logging
    setup_logging(config)
    
    logger.info("=" * 60)
    logger.info(f"Unraid Monitor v{__version__}")
    logger.info("=" * 60)
    logger.info(f"Timezone: {config.timezone}")
    logger.info(f"System check interval: {config.monitoring.system_interval_seconds}s")
    logger.info(f"Docker check interval: {config.monitoring.docker_interval_seconds}s")
    logger.info(f"Weekly report: {'enabled' if config.weekly_report.enabled else 'disabled'}")
    
    # Log configured services
    services = []
    if config.services.radarr.is_configured:
        services.append("Radarr")
    if config.services.sonarr.is_configured:
        services.append("Sonarr")
    if config.services.immich.is_configured:
        services.append("Immich")
    if config.services.jellyfin.is_configured:
        services.append("Jellyfin")
    if config.services.qbittorrent.is_configured:
        services.append("qBittorrent")
    
    if services:
        logger.info(f"Configured services: {', '.join(services)}")
    else:
        logger.info("No optional services configured (reports will be limited)")
    
    logger.info("=" * 60)
    
    # Create monitor
    monitor = UnraidMonitor(config)
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    def signal_handler(sig):
        logger.info(f"Received signal {sig}, shutting down...")
        # Don't call loop.stop() - let monitor.stop() complete gracefully
        asyncio.create_task(monitor.stop())
    
    # Register signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())
