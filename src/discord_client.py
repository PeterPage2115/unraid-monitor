"""
Discord client - Backward compatibility layer.

This module re-exports from the new notifications package
for backward compatibility with existing code.

New code should import directly from notifications:
    from notifications import DiscordProvider, build_embed, EmbedColor
"""

from __future__ import annotations

# Re-export everything from notifications package
from notifications.discord import (
    DiscordProvider,
    EmbedColor,
    build_embed,
    LEVEL_EMOJI,
    LEVEL_TO_COLOR,
    MAX_EMBEDS_PER_MESSAGE,
    MAX_FIELDS_PER_EMBED,
    MAX_FIELD_NAME_LENGTH,
    MAX_FIELD_VALUE_LENGTH,
    MAX_EMBED_DESCRIPTION_LENGTH,
    MAX_EMBED_TITLE_LENGTH,
)

from notifications.utils import (
    format_bytes,
    format_percentage,
    format_temperature,
    format_uptime,
    create_progress_bar,
    create_colored_progress_bar,
    create_storage_bar,
)

# Alias for backward compatibility
DiscordClient = DiscordProvider

__all__ = [
    # Main class
    "DiscordClient",
    "DiscordProvider",
    # Embed helpers
    "EmbedColor",
    "build_embed",
    # Constants
    "LEVEL_EMOJI",
    "LEVEL_TO_COLOR",
    "MAX_EMBEDS_PER_MESSAGE",
    "MAX_FIELDS_PER_EMBED",
    "MAX_FIELD_NAME_LENGTH",
    "MAX_FIELD_VALUE_LENGTH",
    "MAX_EMBED_DESCRIPTION_LENGTH",
    "MAX_EMBED_TITLE_LENGTH",
    # Formatters
    "format_bytes",
    "format_percentage",
    "format_temperature",
    "format_uptime",
    "create_progress_bar",
    "create_colored_progress_bar",
    "create_storage_bar",
]
