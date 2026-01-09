"""
Notification providers for Unraid Monitor.

This module provides a pluggable notification system that supports
multiple backends (Discord, Telegram, Slack, Email, etc.)

Usage:
    from notifications import get_provider, NotificationProvider
    
    provider = get_provider("discord", config)
    await provider.send_alert(alert)
"""

from .base import NotificationProvider, Alert, Report, ReportSection, AlertLevel
from .factory import get_provider, list_providers, get_provider_from_config
from .discord import DiscordProvider, EmbedColor, build_embed
from .utils import (
    format_bytes,
    format_percentage,
    format_temperature,
    format_uptime,
    create_progress_bar,
    create_colored_progress_bar,
    create_storage_bar,
)

__all__ = [
    # Base classes
    "NotificationProvider",
    "Alert",
    "Report",
    "ReportSection",
    "AlertLevel",
    # Factory
    "get_provider",
    "list_providers",
    "get_provider_from_config",
    # Discord (for backward compatibility)
    "DiscordProvider",
    "EmbedColor",
    "build_embed",
    # Formatters
    "format_bytes",
    "format_percentage",
    "format_temperature",
    "format_uptime",
    "create_progress_bar",
    "create_colored_progress_bar",
    "create_storage_bar",
]
