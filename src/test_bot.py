#!/usr/bin/env python3
"""
Test script for Unraid Monitor.

Run from within the container or locally with PYTHONPATH set:
    docker exec -it unraid-monitor python test_bot.py --help
    
Or locally:
    set PYTHONPATH=src
    python src/test_bot.py --help
"""

import asyncio
import argparse
import sys
import os

# Add src to path if running locally
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, setup_logging
from discord_client import DiscordClient, build_embed, EmbedColor


async def test_webhook(config):
    """Test basic webhook connectivity."""
    print("🔗 Testing Discord webhook...")
    
    discord = DiscordClient(
        webhook_url=config.discord_webhook_url,
        user_id=config.discord_user_id or None,
    )
    
    embed = build_embed(
        title="🧪 Test Message",
        description="This is a test message from Unraid Monitor.",
        color=EmbedColor.INFO,
        fields=[
            {"name": "Status", "value": "✅ Webhook working!", "inline": True},
            {"name": "Test Type", "value": "Basic connectivity", "inline": True},
        ]
    )
    
    success = await discord.send_message(embeds=[embed])
    await discord.close()
    
    if success:
        print("✅ Webhook test successful!")
    else:
        print("❌ Webhook test failed!")
    
    return success


async def test_alert_warning(config):
    """Test warning alert (no ping)."""
    print("⚠️ Testing WARNING alert...")
    
    discord = DiscordClient(
        webhook_url=config.discord_webhook_url,
        user_id=config.discord_user_id or None,
    )
    
    success = await discord.send_alert(
        level="warning",
        title="Test Warning Alert",
        description="This is a test WARNING alert. You should NOT be pinged.",
        current_value="85%",
        threshold="80%",
        metric_name="Test Metric",
    )
    await discord.close()
    
    if success:
        print("✅ Warning alert sent!")
    else:
        print("❌ Warning alert failed!")
    
    return success


async def test_alert_critical(config):
    """Test critical alert (with ping)."""
    print("🚨 Testing CRITICAL alert (you should be pinged)...")
    
    discord = DiscordClient(
        webhook_url=config.discord_webhook_url,
        user_id=config.discord_user_id or None,
    )
    
    success = await discord.send_alert(
        level="critical",
        title="Test Critical Alert",
        description="This is a test CRITICAL alert. You SHOULD be pinged!",
        current_value="98%",
        threshold="95%",
        metric_name="Test Metric",
    )
    await discord.close()
    
    if success:
        print("✅ Critical alert sent!")
        if config.discord_user_id:
            print(f"   📱 You should have been pinged (@{config.discord_user_id})")
        else:
            print("   ⚠️ No user ID configured - no ping sent")
    else:
        print("❌ Critical alert failed!")
    
    return success


async def test_alert_recovery(config):
    """Test recovery alert."""
    print("✅ Testing RECOVERY alert...")
    
    discord = DiscordClient(
        webhook_url=config.discord_webhook_url,
        user_id=config.discord_user_id or None,
    )
    
    success = await discord.send_alert(
        level="recovery",
        title="Test Recovery Alert",
        description="This is a test RECOVERY alert. The issue has been resolved.",
        current_value="45%",
        threshold="80%",
        metric_name="Test Metric",
    )
    await discord.close()
    
    if success:
        print("✅ Recovery alert sent!")
    else:
        print("❌ Recovery alert failed!")
    
    return success


async def test_system_metrics(config):
    """Test system metrics collection (may fail on Windows)."""
    print("📊 Testing system metrics collection...")
    
    try:
        from monitors.system import SystemMonitor
        from alerts.manager import AlertManager
        
        discord = DiscordClient(
            webhook_url=config.discord_webhook_url,
            user_id=config.discord_user_id or None,
        )
        alert_manager = AlertManager(discord, config.alerts)
        monitor = SystemMonitor(config, alert_manager)
        
        metrics = await monitor.get_report_data()
        
        print("\n📈 System Metrics:")
        print(f"   CPU Usage: {metrics.get('cpu', {}).get('current', 'N/A')}%")
        print(f"   RAM Usage: {metrics.get('memory', {}).get('percent', 'N/A')}%")
        
        mem = metrics.get('memory', {})
        if mem:
            used_gb = mem.get('used_bytes', 0) / (1024**3)
            total_gb = mem.get('total_bytes', 0) / (1024**3)
            print(f"   RAM Used: {used_gb:.1f} GB / {total_gb:.1f} GB")
        
        if 'disks' in metrics:
            print("\n   💾 Disk Usage:")
            for disk in metrics['disks']:
                print(f"      {disk.get('mountpoint', '?')}: {disk.get('percent', 'N/A')}%")
        
        temps = metrics.get('temperatures', {})
        if temps:
            print("\n   🌡️ Temperatures:")
            for sensor, readings in temps.items():
                if readings:
                    print(f"      {sensor}: {readings[0].get('current', 'N/A')}°C")
        else:
            print("\n   🌡️ Temperatures: Not available")
        
        await discord.close()
        print("\n✅ System metrics test successful!")
        return True
        
    except Exception as e:
        print(f"❌ System metrics test failed: {e}")
        return False


async def test_docker(config):
    """Test Docker monitoring (will fail on Windows)."""
    print("🐳 Testing Docker monitoring...")
    
    try:
        from monitors.docker_monitor import DockerMonitor
        from alerts.manager import AlertManager
        
        discord = DiscordClient(
            webhook_url=config.discord_webhook_url,
            user_id=config.discord_user_id or None,
        )
        alert_manager = AlertManager(discord, config.alerts)
        monitor = DockerMonitor(config, alert_manager)
        
        containers = await monitor.get_report_data()
        
        print(f"\n🐳 Found {len(containers)} containers:")
        for container in containers:
            status = container.get('status', 'unknown')
            emoji = "🟢" if status == 'running' else "🔴"
            name = container.get('name', 'unknown')
            health = container.get('health', 'N/A')
            print(f"   {emoji} {name}: {status} ({health})")
        
        await discord.close()
        print("\n✅ Docker test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Docker test failed: {e}")
        print("   (This is expected on Windows - Docker socket not available)")
        return False


async def test_services(config):
    """Test service API connections."""
    print("🔌 Testing service connections...")
    
    results = {}
    
    # Radarr
    if config.services.radarr.is_configured and config.services.radarr.api_key:
        print("\n📽️ Testing Radarr...")
        try:
            from monitors.services.radarr import RadarrClient
            client = RadarrClient(
                config.services.radarr.url,
                config.services.radarr.api_key
            )
            stats = await client.get_stats_for_report()
            await client.close()
            
            if stats:
                print(f"   ✅ Radarr connected!")
                print(f"   Movies: {stats.get('total_movies', 'N/A')}")
                results['radarr'] = True
            else:
                print("   ⚠️ Radarr returned no data")
                results['radarr'] = False
        except Exception as e:
            print(f"   ❌ Radarr failed: {e}")
            results['radarr'] = False
    
    # Sonarr
    if config.services.sonarr.is_configured and config.services.sonarr.api_key:
        print("\n📺 Testing Sonarr...")
        try:
            from monitors.services.sonarr import SonarrClient
            client = SonarrClient(
                config.services.sonarr.url,
                config.services.sonarr.api_key
            )
            stats = await client.get_stats_for_report()
            await client.close()
            
            if stats:
                print(f"   ✅ Sonarr connected!")
                print(f"   Series: {stats.get('total_series', 'N/A')}")
                results['sonarr'] = True
            else:
                print("   ⚠️ Sonarr returned no data")
                results['sonarr'] = False
        except Exception as e:
            print(f"   ❌ Sonarr failed: {e}")
            results['sonarr'] = False
    
    # Immich
    if config.services.immich.is_configured and config.services.immich.api_key:
        print("\n📷 Testing Immich...")
        try:
            from monitors.services.immich import ImmichClient
            client = ImmichClient(
                config.services.immich.url,
                config.services.immich.api_key
            )
            stats = await client.get_stats_for_report()
            await client.close()
            
            if stats:
                print(f"   ✅ Immich connected!")
                print(f"   Photos: {stats.get('photos', 'N/A')}")
                results['immich'] = True
            else:
                print("   ⚠️ Immich returned no data")
                results['immich'] = False
        except Exception as e:
            print(f"   ❌ Immich failed: {e}")
            results['immich'] = False
    
    # Jellyfin
    if config.services.jellyfin.is_configured and config.services.jellyfin.api_key:
        print("\n🎬 Testing Jellyfin...")
        try:
            from monitors.services.jellyfin import JellyfinClient
            client = JellyfinClient(
                config.services.jellyfin.url,
                config.services.jellyfin.api_key
            )
            stats = await client.get_stats_for_report()
            await client.close()
            
            if stats:
                print(f"   ✅ Jellyfin connected!")
                print(f"   Movies: {stats.get('movies', 'N/A')}")
                results['jellyfin'] = True
            else:
                print("   ⚠️ Jellyfin returned no data")
                results['jellyfin'] = False
        except Exception as e:
            print(f"   ❌ Jellyfin failed: {e}")
            results['jellyfin'] = False
    
    # qBittorrent
    if config.services.qbittorrent.is_configured and config.services.qbittorrent.password:
        print("\n📥 Testing qBittorrent...")
        try:
            from monitors.services.qbittorrent import QBittorrentClient
            client = QBittorrentClient(
                config.services.qbittorrent.url,
                config.services.qbittorrent.username,
                config.services.qbittorrent.password
            )
            stats = await client.get_stats_for_report()
            await client.close()
            
            if stats:
                print(f"   ✅ qBittorrent connected!")
                print(f"   Active torrents: {stats.get('active_torrents', 'N/A')}")
                results['qbittorrent'] = True
            else:
                print("   ⚠️ qBittorrent returned no data")
                results['qbittorrent'] = False
        except Exception as e:
            print(f"   ❌ qBittorrent failed: {e}")
            results['qbittorrent'] = False
    
    if results:
        success = sum(results.values())
        total = len(results)
        print(f"\n📊 Services test: {success}/{total} passed")
    else:
        print("\n⚠️ No services configured with API keys")
    
    return all(results.values()) if results else True


async def test_weekly_report(config):
    """Generate and send a test weekly report."""
    print("📊 Generating test weekly report...")
    
    try:
        from reports.weekly import WeeklyReportGenerator
        from monitors.system import SystemMonitor
        from monitors.docker_monitor import DockerMonitor
        from monitors.services.radarr import RadarrClient
        from monitors.services.sonarr import SonarrClient
        from monitors.services.immich import ImmichClient
        from monitors.services.jellyfin import JellyfinClient
        from monitors.services.qbittorrent import QBittorrentClient
        from alerts.manager import AlertManager
        
        discord = DiscordClient(
            webhook_url=config.discord_webhook_url,
            user_id=config.discord_user_id or None,
        )
        alert_manager = AlertManager(discord, config.alerts)
        
        # Initialize monitors
        system_monitor = SystemMonitor(config, alert_manager)
        docker_monitor = DockerMonitor(config, alert_manager)
        
        # Initialize service clients
        service_clients = {}
        
        if config.services.radarr.is_configured and config.services.radarr.api_key:
            service_clients['radarr'] = RadarrClient(
                config.services.radarr.url,
                config.services.radarr.api_key
            )
        
        if config.services.sonarr.is_configured and config.services.sonarr.api_key:
            service_clients['sonarr'] = SonarrClient(
                config.services.sonarr.url,
                config.services.sonarr.api_key
            )
        
        if config.services.immich.is_configured and config.services.immich.api_key:
            service_clients['immich'] = ImmichClient(
                config.services.immich.url,
                config.services.immich.api_key
            )
        
        if config.services.jellyfin.is_configured and config.services.jellyfin.api_key:
            service_clients['jellyfin'] = JellyfinClient(
                config.services.jellyfin.url,
                config.services.jellyfin.api_key
            )
        
        if config.services.qbittorrent.is_configured and config.services.qbittorrent.password:
            service_clients['qbittorrent'] = QBittorrentClient(
                config.services.qbittorrent.url,
                config.services.qbittorrent.username,
                config.services.qbittorrent.password
            )
        
        # Create report generator
        report_generator = WeeklyReportGenerator(
            config=config,
            discord=discord,
            alert_manager=alert_manager,
            system_monitor=system_monitor,
            docker_monitor=docker_monitor,
            **service_clients
        )
        
        # Generate and send report
        success = await report_generator.generate_and_send()
        
        # Cleanup
        for client in service_clients.values():
            await client.close()
        await discord.close()
        
        if success:
            print("✅ Weekly report sent successfully!")
        else:
            print("❌ Weekly report failed to send")
        
        return success
        
    except Exception as e:
        print(f"❌ Weekly report test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test Unraid Monitor functionality")
    parser.add_argument(
        "test",
        nargs="?",
        default="all",
        choices=["all", "webhook", "warning", "critical", "recovery", "system", "docker", "services", "report"],
        help="Which test to run (default: all)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧪 Unraid Monitor Test Suite")
    print("=" * 60)
    
    # Load config
    try:
        config = load_config()
        setup_logging(config)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)
    
    print(f"\n📋 Configuration:")
    print(f"   Webhook: {'✅ Configured' if config.discord_webhook_url else '❌ Missing'}")
    print(f"   User ID: {config.discord_user_id or 'Not set'}")
    print(f"   Report Channel: {config.discord_report_channel_id or 'Not set'}")
    print()
    
    tests = {
        "webhook": test_webhook,
        "warning": test_alert_warning,
        "critical": test_alert_critical,
        "recovery": test_alert_recovery,
        "system": test_system_metrics,
        "docker": test_docker,
        "services": test_services,
        "report": test_weekly_report,
    }
    
    if args.test == "all":
        results = {}
        for name, test_func in tests.items():
            print(f"\n{'=' * 40}")
            results[name] = await test_func(config)
        
        print("\n" + "=" * 60)
        print("📊 Test Summary:")
        print("=" * 60)
        for name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {name}: {status}")
    else:
        await tests[args.test](config)
    
    print("\n" + "=" * 60)
    print("🏁 Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
