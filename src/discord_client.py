"""
Discord webhook client for sending notifications and reports.

Uses aiohttp for async HTTP requests to Discord webhooks.
Supports rich embeds with formatting, colors, and fields.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import aiohttp


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Discord embed colors (hex values)
class EmbedColor(Enum):
    """Discord embed colors for different alert levels."""
    INFO = 0x3498DB       # Blue
    SUCCESS = 0x2ECC71    # Green
    WARNING = 0xF39C12    # Orange
    CRITICAL = 0xE74C3C   # Red
    RECOVERY = 0x2ECC71   # Green (same as success)
    PURPLE = 0x9B59B6     # Purple (for reports)
    DARK = 0x2C3E50       # Dark blue-gray


# Emoji prefixes for alert levels
LEVEL_EMOJI = {
    "info": "ℹ️",
    "success": "✅",
    "warning": "⚠️",
    "critical": "🚨",
    "recovery": "✅",
}

# Discord webhook limits
MAX_EMBEDS_PER_MESSAGE = 10
MAX_FIELDS_PER_EMBED = 25
MAX_FIELD_NAME_LENGTH = 256
MAX_FIELD_VALUE_LENGTH = 1024
MAX_EMBED_DESCRIPTION_LENGTH = 4096
MAX_EMBED_TITLE_LENGTH = 256


# =============================================================================
# Embed builder helpers
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
    """
    Build a Discord embed dictionary.
    
    Args:
        title: Embed title (max 256 chars)
        description: Embed description (max 4096 chars)
        color: Embed color (EmbedColor enum or hex int)
        fields: List of field dicts with name, value, inline keys
        footer: Footer text
        thumbnail_url: URL to thumbnail image
        timestamp: Whether to add current timestamp
        author: Author dict with name, icon_url, url keys
    
    Returns:
        Discord embed dictionary
    """
    embed: dict[str, Any] = {
        "title": title[:MAX_EMBED_TITLE_LENGTH],
    }
    
    if description:
        embed["description"] = description[:MAX_EMBED_DESCRIPTION_LENGTH]
    
    # Handle color
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


def build_alert_embed(
    level: str,
    title: str,
    description: str | None = None,
    current_value: str | None = None,
    threshold: str | None = None,
    metric_name: str | None = None,
    extra_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build a standardized alert embed.
    
    Args:
        level: Alert level (info, warning, critical, recovery)
        title: Alert title
        description: Optional description
        current_value: Current metric value
        threshold: Threshold that was exceeded
        metric_name: Name of the metric being monitored
        extra_fields: Additional fields to include
    
    Returns:
        Discord embed dictionary
    """
    emoji = LEVEL_EMOJI.get(level, "ℹ️")
    
    # Map level to color
    color_map = {
        "info": EmbedColor.INFO,
        "warning": EmbedColor.WARNING,
        "critical": EmbedColor.CRITICAL,
        "recovery": EmbedColor.RECOVERY,
        "success": EmbedColor.SUCCESS,
    }
    color = color_map.get(level, EmbedColor.INFO)
    
    fields = []
    
    if current_value is not None:
        fields.append({"name": "Current", "value": current_value, "inline": True})
    
    if threshold is not None:
        fields.append({"name": "Threshold", "value": threshold, "inline": True})
    
    if metric_name is not None:
        fields.append({"name": "Metric", "value": metric_name, "inline": True})
    
    if extra_fields:
        fields.extend(extra_fields)
    
    return build_embed(
        title=f"{emoji} {title}",
        description=description,
        color=color,
        fields=fields if fields else None,
        footer="Unraid Monitor",
    )


# =============================================================================
# Discord webhook client
# =============================================================================

class DiscordClient:
    """
    Async Discord webhook client.
    
    Handles sending messages and embeds to Discord via webhooks.
    Includes rate limiting awareness and error handling.
    """
    
    def __init__(
        self,
        webhook_url: str,
        timeout: int = 10,
        user_id: str | None = None,
        report_channel_id: str | None = None,
    ):
        """
        Initialize the Discord client.
        
        Args:
            webhook_url: Discord webhook URL
            timeout: Request timeout in seconds
            user_id: Discord user ID to ping on critical alerts
            report_channel_id: Channel ID for weekly reports
        """
        self.webhook_url = webhook_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.user_id = user_id
        self.report_channel_id = report_channel_id
        self._session: aiohttp.ClientSession | None = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session
    
    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def send_message(
        self,
        content: str | None = None,
        embeds: list[dict[str, Any]] | None = None,
        username: str = "Unraid Monitor",
        avatar_url: str | None = None,
    ) -> bool:
        """
        Send a message to Discord.
        
        Args:
            content: Text content of the message
            embeds: List of embed dictionaries
            username: Override webhook username
            avatar_url: Override webhook avatar
        
        Returns:
            True if message was sent successfully
        """
        if not content and not embeds:
            logger.warning("Attempted to send empty message to Discord")
            return False
        
        payload: dict[str, Any] = {
            "username": username,
        }
        
        if content:
            payload["content"] = content
        
        if embeds:
            # Limit to max embeds
            payload["embeds"] = embeds[:MAX_EMBEDS_PER_MESSAGE]
        
        if avatar_url:
            payload["avatar_url"] = avatar_url
        
        try:
            session = await self._get_session()
            async with session.post(self.webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.debug("Message sent successfully to Discord")
                    return True
                elif response.status == 429:
                    # Rate limited
                    retry_after = response.headers.get("Retry-After", "unknown")
                    logger.warning(f"Discord rate limited, retry after: {retry_after}s")
                    return False
                else:
                    body = await response.text()
                    logger.error(f"Discord webhook error {response.status}: {body}")
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error sending to Discord: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to Discord: {e}")
            return False
    
    async def send_alert(
        self,
        level: str,
        title: str,
        description: str | None = None,
        current_value: str | None = None,
        threshold: str | None = None,
        metric_name: str | None = None,
        extra_fields: list[dict[str, Any]] | None = None,
    ) -> bool:
        """
        Send a standardized alert to Discord.
        
        Args:
            level: Alert level (info, warning, critical, recovery)
            title: Alert title
            description: Optional description
            current_value: Current metric value
            threshold: Threshold that was exceeded
            metric_name: Name of the metric
            extra_fields: Additional fields
        
        Returns:
            True if sent successfully
        """
        embed = build_alert_embed(
            level=level,
            title=title,
            description=description,
            current_value=current_value,
            threshold=threshold,
            metric_name=metric_name,
            extra_fields=extra_fields,
        )
        
        # Ping user on critical alerts
        content = None
        if level == "critical" and self.user_id:
            content = f"<@{self.user_id}>"
        
        return await self.send_message(content=content, embeds=[embed])
    
    async def send_report(
        self,
        title: str,
        sections: list[dict[str, Any]],
    ) -> bool:
        """
        Send a multi-embed report to Discord.
        
        Args:
            title: Report title (sent as first embed)
            sections: List of section dicts with title, fields, color keys
        
        Returns:
            True if sent successfully
        """
        embeds = []
        
        # Header embed
        embeds.append(build_embed(
            title=f"📊 {title}",
            description=f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            color=EmbedColor.PURPLE,
            timestamp=True,
        ))
        
        # Section embeds
        for section in sections:
            color = section.get("color", EmbedColor.INFO)
            if isinstance(color, str):
                color = getattr(EmbedColor, color.upper(), EmbedColor.INFO)
            
            embeds.append(build_embed(
                title=section.get("title", "Section"),
                description=section.get("description"),
                color=color,
                fields=section.get("fields"),
                timestamp=False,
            ))
        
        # Send in batches if needed
        success = True
        for i in range(0, len(embeds), MAX_EMBEDS_PER_MESSAGE):
            batch = embeds[i:i + MAX_EMBEDS_PER_MESSAGE]
            if not await self.send_message(embeds=batch):
                success = False
        
        return success
    
    async def send_startup_message(self) -> bool:
        """Send a startup notification."""
        embed = build_embed(
            title="🚀 Unraid Monitor Started",
            description="Monitoring is now active. You will receive alerts when thresholds are exceeded.",
            color=EmbedColor.SUCCESS,
            fields=[
                {"name": "Status", "value": "Online", "inline": True},
                {"name": "Version", "value": "1.0.0", "inline": True},
            ],
        )
        return await self.send_message(embeds=[embed])
    
    async def send_shutdown_message(self) -> bool:
        """Send a shutdown notification."""
        embed = build_embed(
            title="🛑 Unraid Monitor Stopped",
            description="Monitoring has been stopped.",
            color=EmbedColor.WARNING,
        )
        return await self.send_message(embeds=[embed])


# =============================================================================
# Utility functions
# =============================================================================

def format_bytes(bytes_value: int | float) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_value) < 1024:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} PB"


def format_percentage(value: float) -> str:
    """Format percentage value."""
    return f"{value:.1f}%"


def format_temperature(celsius: float) -> str:
    """Format temperature in Celsius."""
    return f"{celsius:.0f}°C"


def format_uptime(seconds: float) -> str:
    """Format uptime in human readable format."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or not parts:
        parts.append(f"{minutes}m")
    
    return " ".join(parts)


def create_progress_bar(
    percent: float,
    length: int = 10,
    filled_char: str = "█",
    empty_char: str = "░",
    show_percent: bool = True,
) -> str:
    """
    Create a visual progress bar using Unicode characters.
    
    Args:
        percent: Percentage (0-100)
        length: Number of characters in the bar
        filled_char: Character for filled portion
        empty_char: Character for empty portion
        show_percent: Whether to append percentage value
    
    Returns:
        String like "████████░░ 80%"
    """
    percent = max(0, min(100, percent))
    filled = int(length * percent / 100)
    bar = filled_char * filled + empty_char * (length - filled)
    
    if show_percent:
        return f"{bar} {percent:.0f}%"
    return bar


def create_colored_progress_bar(
    percent: float,
    length: int = 10,
    show_percent: bool = True,
) -> str:
    """
    Create a colored progress bar with thresholds.
    Uses different emoji based on percentage level.
    
    Args:
        percent: Percentage (0-100)
        length: Number of segments
        show_percent: Whether to append percentage value
    
    Returns:
        String with colored bar
    """
    percent = max(0, min(100, percent))
    filled = int(length * percent / 100)
    
    # Choose color based on level
    if percent >= 90:
        filled_char = "🟥"  # Red - critical
    elif percent >= 75:
        filled_char = "🟧"  # Orange - warning
    elif percent >= 50:
        filled_char = "🟨"  # Yellow - moderate
    else:
        filled_char = "🟩"  # Green - good
    
    empty_char = "⬜"
    
    bar = filled_char * filled + empty_char * (length - filled)
    
    if show_percent:
        return f"{bar} {percent:.0f}%"
    return bar


def create_storage_bar(
    used_percent: float,
    length: int = 8,
) -> str:
    """
    Create a storage usage bar optimized for disk space.
    
    Args:
        used_percent: Percentage used (0-100)
        length: Number of segments
    
    Returns:
        Colored storage bar
    """
    return create_colored_progress_bar(used_percent, length, show_percent=True)
