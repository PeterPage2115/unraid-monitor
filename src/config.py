"""
Configuration management for Unraid Monitor.

Loads configuration from:
1. YAML file (settings.yaml) - thresholds, intervals, behavior
2. Environment variables - secrets (API keys, webhook URLs)

Environment variables take precedence over YAML for any overlapping settings.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import yaml


logger = logging.getLogger(__name__)


# =============================================================================
# Default configuration values
# =============================================================================

DEFAULT_CONFIG = {
    "monitoring": {
        "system_interval_seconds": 300,
        "docker_interval_seconds": 60,
        "services_interval_seconds": 3600,
    },
    "thresholds": {
        "cpu": {"warning": 80, "critical": 95},
        "memory": {"warning": 85, "critical": 95},
        "disk": {"warning": 80, "critical": 95},
        "temperature": {"warning": 75, "critical": 90},  # Higher thresholds for NVMe
    },
    "alerts": {
        "cooldown_minutes": 30,
        "recovery_enabled": True,
        "hysteresis_percent": 5,
    },
    "weekly_report": {
        "enabled": True,
        "day": "sunday",
        "hour": 9,
        "minute": 0,
    },
    "docker": {
        "monitor_restarts": True,
        "restart_threshold": 3,
        "restart_window_minutes": 60,
        "ignored_containers": ["unraid-monitor"],
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
    "temperature_sensors": {
        "whitelist": ["coretemp", "nvme"],  # Only CPU and NVMe
        "blacklist": [],
    },
}


# =============================================================================
# Data classes for typed configuration
# =============================================================================

@dataclass
class ThresholdConfig:
    """Threshold configuration for a single metric."""
    warning: int
    critical: int


@dataclass
class ThresholdsConfig:
    """All threshold configurations."""
    cpu: ThresholdConfig
    memory: ThresholdConfig
    disk: ThresholdConfig
    temperature: ThresholdConfig
    
    @classmethod
    def from_dict(cls, data: dict) -> "ThresholdsConfig":
        return cls(
            cpu=ThresholdConfig(**data.get("cpu", DEFAULT_CONFIG["thresholds"]["cpu"])),
            memory=ThresholdConfig(**data.get("memory", DEFAULT_CONFIG["thresholds"]["memory"])),
            disk=ThresholdConfig(**data.get("disk", DEFAULT_CONFIG["thresholds"]["disk"])),
            temperature=ThresholdConfig(**data.get("temperature", DEFAULT_CONFIG["thresholds"]["temperature"])),
        )


@dataclass
class MonitoringConfig:
    """Monitoring interval configuration."""
    system_interval_seconds: int = 300
    docker_interval_seconds: int = 60
    services_interval_seconds: int = 3600


@dataclass
class AlertsConfig:
    """Alert behavior configuration."""
    cooldown_minutes: int = 30
    recovery_enabled: bool = True
    hysteresis_percent: int = 5


@dataclass
class WeeklyReportConfig:
    """Weekly report scheduling configuration."""
    enabled: bool = True
    day: str = "sunday"
    hour: int = 9
    minute: int = 0


@dataclass
class DockerConfig:
    """Docker monitoring configuration."""
    monitor_restarts: bool = True
    restart_threshold: int = 3
    restart_window_minutes: int = 60
    ignored_containers: list[str] = field(default_factory=lambda: ["unraid-monitor"])


@dataclass
class ServiceConfig:
    """Configuration for a single service (Radarr, Sonarr, etc.)."""
    url: str | None = None
    api_key: str | None = None
    username: str | None = None
    password: str | None = None
    
    @property
    def is_configured(self) -> bool:
        """Check if the service has minimum required configuration."""
        return bool(self.url)


@dataclass
class ServicesConfig:
    """All service configurations."""
    radarr: ServiceConfig = field(default_factory=ServiceConfig)
    sonarr: ServiceConfig = field(default_factory=ServiceConfig)
    immich: ServiceConfig = field(default_factory=ServiceConfig)
    jellyfin: ServiceConfig = field(default_factory=ServiceConfig)
    qbittorrent: ServiceConfig = field(default_factory=ServiceConfig)


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class TemperatureSensorsConfig:
    """Temperature sensor filtering configuration."""
    whitelist: list[str] = field(default_factory=lambda: ["coretemp", "nvme"])
    blacklist: list[str] = field(default_factory=list)


# =============================================================================
# Main configuration class
# =============================================================================

@dataclass
class Config:
    """
    Main configuration container.
    
    Loads from YAML file and environment variables.
    Environment variables take precedence.
    """
    
    # Required
    discord_webhook_url: str = ""
    
    # Optional Discord settings
    discord_user_id: str = ""  # User ID to ping on critical alerts
    discord_report_channel_id: str = ""  # Channel ID for weekly reports (uses thread)
    
    # Timezone
    timezone: str = "Europe/Warsaw"
    
    # Sub-configurations
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    thresholds: ThresholdsConfig = field(default_factory=lambda: ThresholdsConfig.from_dict({}))
    alerts: AlertsConfig = field(default_factory=AlertsConfig)
    weekly_report: WeeklyReportConfig = field(default_factory=WeeklyReportConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)
    services: ServicesConfig = field(default_factory=ServicesConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    temperature_sensors: TemperatureSensorsConfig = field(default_factory=TemperatureSensorsConfig)
    
    def validate(self) -> list[str]:
        """
        Validate the configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.discord_webhook_url:
            errors.append("DISCORD_WEBHOOK_URL is required")
        elif not self.discord_webhook_url.startswith("https://discord.com/api/webhooks/"):
            errors.append("DISCORD_WEBHOOK_URL must be a valid Discord webhook URL")
        
        # Validate thresholds
        for metric in ["cpu", "memory", "disk", "temperature"]:
            threshold = getattr(self.thresholds, metric)
            if threshold.warning >= threshold.critical:
                errors.append(f"Threshold {metric}: warning ({threshold.warning}) must be less than critical ({threshold.critical})")
        
        # Validate weekly report day
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if self.weekly_report.day.lower() not in valid_days:
            errors.append(f"Weekly report day must be one of: {', '.join(valid_days)}")
        
        return errors


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Deep merge two dictionaries.
    
    Values from 'override' take precedence over 'base'.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config if config else {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML config: {e}")
        return {}


def _load_services_from_env() -> ServicesConfig:
    """Load service configurations from environment variables."""
    return ServicesConfig(
        radarr=ServiceConfig(
            url=os.getenv("RADARR_URL"),
            api_key=os.getenv("RADARR_API_KEY"),
        ),
        sonarr=ServiceConfig(
            url=os.getenv("SONARR_URL"),
            api_key=os.getenv("SONARR_API_KEY"),
        ),
        immich=ServiceConfig(
            url=os.getenv("IMMICH_URL"),
            api_key=os.getenv("IMMICH_API_KEY"),
        ),
        jellyfin=ServiceConfig(
            url=os.getenv("JELLYFIN_URL"),
            api_key=os.getenv("JELLYFIN_API_KEY"),
        ),
        qbittorrent=ServiceConfig(
            url=os.getenv("QBITTORRENT_URL"),
            username=os.getenv("QBITTORRENT_USERNAME"),
            password=os.getenv("QBITTORRENT_PASSWORD"),
        ),
    )


def load_config(config_dir: Path | str | None = None) -> Config:
    """
    Load configuration from YAML file and environment variables.
    
    Args:
        config_dir: Directory containing settings.yaml. 
                   Defaults to /app/config or ./config
    
    Returns:
        Fully loaded and merged Config object
    
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    # Determine config directory
    if config_dir is None:
        # Check common locations
        if Path("/app/config").exists():
            config_dir = Path("/app/config")
        else:
            config_dir = Path("./config")
    else:
        config_dir = Path(config_dir)
    
    # Load YAML config
    yaml_path = config_dir / "settings.yaml"
    yaml_config = _load_yaml_config(yaml_path)
    
    # Merge with defaults
    merged_config = _deep_merge(DEFAULT_CONFIG, yaml_config)
    
    # Build Config object
    config = Config(
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
        discord_user_id=os.getenv("DISCORD_USER_ID", ""),
        discord_report_channel_id=os.getenv("DISCORD_REPORT_CHANNEL_ID", ""),
        timezone=os.getenv("TZ", "Europe/Warsaw"),
        monitoring=MonitoringConfig(**merged_config.get("monitoring", {})),
        thresholds=ThresholdsConfig.from_dict(merged_config.get("thresholds", {})),
        alerts=AlertsConfig(**merged_config.get("alerts", {})),
        weekly_report=WeeklyReportConfig(**merged_config.get("weekly_report", {})),
        docker=DockerConfig(**merged_config.get("docker", {})),
        services=_load_services_from_env(),
        logging=LoggingConfig(**merged_config.get("logging", {})),
        temperature_sensors=TemperatureSensorsConfig(**merged_config.get("temperature_sensors", {})),
    )
    
    # Validate
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
    
    logger.info("Configuration loaded successfully")
    return config


def setup_logging(config: Config) -> None:
    """
    Set up logging based on configuration.
    
    Args:
        config: Loaded configuration object
    """
    level = getattr(logging, config.logging.level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format=config.logging.format,
        handlers=[
            logging.StreamHandler(),
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    logger.info(f"Logging configured at {config.logging.level} level")
