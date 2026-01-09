"""
Utility functions for formatting values in notifications.

These helpers are used by notification providers and report generators
to format data consistently across the application.
"""

from __future__ import annotations


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
    """
    percent = max(0, min(100, percent))
    filled = int(length * percent / 100)
    
    if percent >= 90:
        filled_char = "🟥"
    elif percent >= 75:
        filled_char = "🟧"
    elif percent >= 50:
        filled_char = "🟨"
    else:
        filled_char = "🟩"
    
    empty_char = "⬜"
    bar = filled_char * filled + empty_char * (length - filled)
    
    if show_percent:
        return f"{bar} {percent:.0f}%"
    return bar


def create_storage_bar(used_percent: float, length: int = 8) -> str:
    """Create a storage usage bar optimized for disk space."""
    return create_colored_progress_bar(used_percent, length, show_percent=True)
