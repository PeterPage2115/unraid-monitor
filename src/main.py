"""
Unraid Monitor - Main entry point.

This is the main application that:
1. Loads configuration
2. Initializes all monitors and services
3. Sets up the scheduler for periodic checks
4. Runs until stopped
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

# APScheduler imports
from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# Local imports
from config import load_config, setup_logging, Config
from discord_client import DiscordClient
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
        self._scheduler: AsyncScheduler | None = None
        
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
    
    async def start(self) -> None:
        """Start the monitor."""
        logger.info("Starting Unraid Monitor...")
        self._running = True
        
        # Send startup notification
        await self.discord.send_startup_message()
        
        # Create scheduler
        async with AsyncScheduler() as scheduler:
            self._scheduler = scheduler
            
            # Schedule system monitoring
            await scheduler.add_schedule(
                self._run_system_check,
                IntervalTrigger(seconds=self.config.monitoring.system_interval_seconds),
                id="system_monitor",
            )
            logger.info(f"System monitor scheduled every {self.config.monitoring.system_interval_seconds}s")
            
            # Schedule Docker monitoring
            await scheduler.add_schedule(
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
                
                await scheduler.add_schedule(
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
            
            logger.info("Unraid Monitor is running. Press Ctrl+C to stop.")
            
            # Run scheduler until stopped
            await scheduler.run_until_stopped()
    
    async def stop(self) -> None:
        """Stop the monitor gracefully."""
        logger.info("Stopping Unraid Monitor...")
        self._running = False
        
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
    logger.info("Unraid Monitor v1.0.0")
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
        asyncio.create_task(monitor.stop())
        loop.stop()
    
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
