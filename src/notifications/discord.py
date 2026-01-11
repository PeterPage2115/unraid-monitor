"""
Discord notification provider.

Implements NotificationProvider interface for Discord webhooks.
Migrated from the original discord_client.py with the same functionality.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import aiohttp

from .base import NotificationProvider, Alert, Report, AlertLevel


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

VERSION = "1.1.2"


class EmbedColor(Enum):
    """Discord embed colors for different alert levels."""
    INFO = 0x3498DB       # Blue
    SUCCESS = 0x2ECC71    # Green
    WARNING = 0xF39C12    # Orange
    CRITICAL = 0xE74C3C   # Red
    RECOVERY = 0x2ECC71   # Green
    PURPLE = 0x9B59B6     # Purple (for reports)
    DARK = 0x2C3E50       # Dark blue-gray


LEVEL_EMOJI = {
    AlertLevel.INFO: "ℹ️",
    AlertLevel.SUCCESS: "✅",
    AlertLevel.WARNING: "⚠️",
    AlertLevel.CRITICAL: "🚨",
    AlertLevel.RECOVERY: "✅",
}

LEVEL_TO_COLOR = {
    AlertLevel.INFO: EmbedColor.INFO,
    AlertLevel.WARNING: EmbedColor.WARNING,
    AlertLevel.CRITICAL: EmbedColor.CRITICAL,
    AlertLevel.RECOVERY: EmbedColor.RECOVERY,
    AlertLevel.SUCCESS: EmbedColor.SUCCESS,
}

COLOR_MAP = {
    "info": EmbedColor.INFO,
    "success": EmbedColor.SUCCESS,
    "warning": EmbedColor.WARNING,
    "critical": EmbedColor.CRITICAL,
    "recovery": EmbedColor.RECOVERY,
    "purple": EmbedColor.PURPLE,
}

# Discord limits
MAX_EMBEDS_PER_MESSAGE = 10
MAX_FIELDS_PER_EMBED = 25
MAX_FIELD_NAME_LENGTH = 256
MAX_FIELD_VALUE_LENGTH = 1024
MAX_EMBED_DESCRIPTION_LENGTH = 4096
MAX_EMBED_TITLE_LENGTH = 256


# =============================================================================
# Embed builders
# =============================================================================

def build_embed(
    title: str,
    description: str | None = None,
    color: EmbedColor | int = EmbedColor.INFO,
    fields: list[dict[str, Any]] | None = None,
    footer: str | None = None,
    thumbnail_url: str | None = None,
    timestamp: bool = True,
    author: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a Discord embed dictionary."""
    embed: dict[str, Any] = {
        "title": title[:MAX_EMBED_TITLE_LENGTH],
    }
    
    if description:
        embed["description"] = description[:MAX_EMBED_DESCRIPTION_LENGTH]
    
    if isinstance(color, EmbedColor):
        embed["color"] = color.value
    else:
        embed["color"] = color
    
    if fields:
        embed["fields"] = [
            {
                "name": f["name"][:MAX_FIELD_NAME_LENGTH],
                "value": str(f["value"])[:MAX_FIELD_VALUE_LENGTH],
                "inline": f.get("inline", True),
            }
            for f in fields[:MAX_FIELDS_PER_EMBED]
        ]
    
    if footer:
        embed["footer"] = {"text": footer}
    
    if thumbnail_url:
        embed["thumbnail"] = {"url": thumbnail_url}
    
    if timestamp:
        embed["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    if author:
        embed["author"] = author
    
    return embed


# =============================================================================
# Discord Provider
# =============================================================================

class DiscordProvider(NotificationProvider):
    """
    Discord webhook notification provider.
    
    Sends alerts and reports to Discord via webhooks.
    Supports rich embeds, user mentions, and rate limiting.
    """
    
    def __init__(
        self,
        webhook_url: str,
        user_id: str | None = None,
        report_channel_id: str | None = None,
        timeout: int = 10,
        bot_name: str = "Unraid Monitor",
    ):
        """
        Initialize Discord provider.
        
        Args:
            webhook_url: Discord webhook URL
            user_id: User ID to ping on critical alerts
            report_channel_id: Optional separate channel for reports
            timeout: Request timeout in seconds
            bot_name: Display name for the webhook
        """
        self.webhook_url = webhook_url
        self.user_id = user_id
        self.report_channel_id = report_channel_id
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.bot_name = bot_name
        self._session: aiohttp.ClientSession | None = None
    
    @property
    def name(self) -> str:
        return "discord"
    
    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url and "discord.com/api/webhooks" in self.webhook_url)
    
    async def initialize(self) -> None:
        """Create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def close(self) -> None:
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create session."""
        if self._session is None or self._session.closed:
            await self.initialize()
        return self._session  # type: ignore
    
    async def _send_webhook(
        self,
        content: str | None = None,
        embeds: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Send a webhook message."""
        if not content and not embeds:
            return False
        
        payload: dict[str, Any] = {"username": self.bot_name}
        
        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds[:MAX_EMBEDS_PER_MESSAGE]
        
        try:
            session = await self._get_session()
            async with session.post(self.webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.debug("Discord message sent successfully")
                    return True
                elif response.status == 429:
                    retry_after = response.headers.get("Retry-After", "?")
                    logger.warning(f"Discord rate limited, retry after: {retry_after}s")
                    return False
                else:
                    body = await response.text()
                    logger.error(f"Discord error {response.status}: {body}")
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"Discord network error: {e}")
            return False
        except Exception as e:
            logger.error(f"Discord unexpected error: {e}")
            return False
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert to Discord."""
        level = alert.level if isinstance(alert.level, AlertLevel) else AlertLevel.INFO
        
        emoji = LEVEL_EMOJI.get(level, "ℹ️")
        color = LEVEL_TO_COLOR.get(level, EmbedColor.INFO)
        
        fields = []
        if alert.current_value:
            fields.append({"name": "Current", "value": alert.current_value, "inline": True})
        if alert.threshold:
            fields.append({"name": "Threshold", "value": alert.threshold, "inline": True})
        if alert.metric_name:
            fields.append({"name": "Metric", "value": alert.metric_name, "inline": True})
        
        for key, value in alert.extra_fields.items():
            fields.append({"name": key, "value": str(value), "inline": True})
        
        embed = build_embed(
            title=f"{emoji} {alert.title}",
            description=alert.description,
            color=color,
            fields=fields if fields else None,
            footer="Unraid Monitor",
        )
        
        # Ping user on critical
        content = None
        if level == AlertLevel.CRITICAL and self.user_id:
            content = f"<@{self.user_id}>"
        
        return await self._send_webhook(content=content, embeds=[embed])
    
    async def send_report(self, report: Report) -> bool:
        """Send a report to Discord."""
        embeds = []
        
        # Header
        embeds.append(build_embed(
            title=f"📊 {report.title}",
            description=f"Generated on {report.generated_at.strftime('%Y-%m-%d %H:%M')}",
            color=EmbedColor.PURPLE,
        ))
        
        # Sections
        for section in report.sections:
            color = COLOR_MAP.get(section.color, EmbedColor.INFO)
            embeds.append(build_embed(
                title=section.title,
                description=section.description,
                color=color,
                fields=section.fields,
                timestamp=False,
            ))
        
        # Send in batches
        success = True
        for i in range(0, len(embeds), MAX_EMBEDS_PER_MESSAGE):
            batch = embeds[i:i + MAX_EMBEDS_PER_MESSAGE]
            if not await self._send_webhook(embeds=batch):
                success = False
        
        return success
    
    async def send_test(self, message: str = "Test notification") -> bool:
        """Send a test message."""
        embed = build_embed(
            title="🔔 Test Notification",
            description=message,
            color=EmbedColor.INFO,
            footer="Unraid Monitor",
        )
        return await self._send_webhook(embeds=[embed])
    
    async def send_startup(self) -> bool:
        """Send startup notification."""
        embed = build_embed(
            title="🚀 Unraid Monitor Started",
            description="Monitoring is now active.",
            color=EmbedColor.SUCCESS,
            fields=[
                {"name": "Status", "value": "Online", "inline": True},
                {"name": "Version", "value": VERSION, "inline": True},
            ],
            footer="Unraid Monitor",
        )
        return await self._send_webhook(embeds=[embed])
    
    async def send_shutdown(self) -> bool:
        """Send shutdown notification."""
        embed = build_embed(
            title="🛑 Unraid Monitor Stopped",
            description="Monitoring has been stopped.",
            color=EmbedColor.WARNING,
            footer="Unraid Monitor",
        )
        return await self._send_webhook(embeds=[embed])
    
    # =========================================================================
    # Legacy compatibility methods (for existing code)
    # =========================================================================
    
    async def send_message(
        self,
        content: str | None = None,
        embeds: list[dict[str, Any]] | None = None,
        username: str | None = None,
        avatar_url: str | None = None,
    ) -> bool:
        """Legacy method for backward compatibility."""
        return await self._send_webhook(content=content, embeds=embeds)
    
    async def send_startup_message(self) -> bool:
        """Legacy method for backward compatibility."""
        return await self.send_startup()
    
    async def send_shutdown_message(self) -> bool:
        """Legacy method for backward compatibility."""
        return await self.send_shutdown()
