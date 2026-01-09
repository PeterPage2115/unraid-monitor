"""
Factory for creating notification providers.

Supports automatic provider selection based on configuration.
"""

from __future__ import annotations

import logging
from typing import Any, Type

from .base import NotificationProvider
from .discord import DiscordProvider


logger = logging.getLogger(__name__)


# Registry of available providers
PROVIDERS: dict[str, Type[NotificationProvider]] = {
    "discord": DiscordProvider,
}


def list_providers() -> list[str]:
    """Return list of available provider names."""
    return list(PROVIDERS.keys())


def get_provider(
    provider_name: str,
    **kwargs: Any,
) -> NotificationProvider:
    """
    Create a notification provider instance.
    
    Args:
        provider_name: Name of the provider ('discord', 'telegram', etc.)
        **kwargs: Provider-specific configuration
    
    Returns:
        Configured NotificationProvider instance
    
    Raises:
        ValueError: If provider_name is not supported
    
    Example:
        provider = get_provider(
            "discord",
            webhook_url="https://discord.com/...",
            user_id="123456789",
        )
    """
    provider_name = provider_name.lower()
    
    if provider_name not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Available providers: {available}"
        )
    
    provider_class = PROVIDERS[provider_name]
    
    try:
        provider = provider_class(**kwargs)
        logger.info(f"Created notification provider: {provider_name}")
        return provider
    except TypeError as e:
        logger.error(f"Invalid configuration for {provider_name}: {e}")
        raise ValueError(f"Invalid configuration for {provider_name}: {e}")


def get_provider_from_config(config: Any) -> NotificationProvider:
    """
    Create a provider from application config.
    
    This reads from the standard config object and creates
    the appropriate provider based on settings.
    
    Args:
        config: Application configuration object
    
    Returns:
        Configured NotificationProvider instance
    """
    # Default to Discord for now
    provider_name = getattr(config, "notification_provider", "discord")
    
    if provider_name == "discord":
        return DiscordProvider(
            webhook_url=config.discord.webhook_url,
            user_id=config.discord.user_id,
            report_channel_id=getattr(config.discord, "report_channel_id", None),
        )
    
    # Future: Add other providers
    # elif provider_name == "telegram":
    #     return TelegramProvider(...)
    
    raise ValueError(f"Unsupported provider in config: {provider_name}")


def register_provider(name: str, provider_class: Type[NotificationProvider]) -> None:
    """
    Register a custom notification provider.
    
    This allows extending the system with custom providers without
    modifying the core code.
    
    Args:
        name: Provider name (e.g., 'custom_slack')
        provider_class: Provider class implementing NotificationProvider
    
    Example:
        class MyCustomProvider(NotificationProvider):
            ...
        
        register_provider("custom", MyCustomProvider)
    """
    if not issubclass(provider_class, NotificationProvider):
        raise TypeError(
            f"Provider class must inherit from NotificationProvider, "
            f"got {provider_class}"
        )
    
    PROVIDERS[name.lower()] = provider_class
    logger.info(f"Registered custom provider: {name}")
