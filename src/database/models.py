"""
Database models for SQLite storage.

These dataclasses represent the data structures stored in the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
import json


@dataclass
class Settings:
    """
    Application settings stored in database.
    
    These can be modified via Web UI without restarting.
    """
    # Alert thresholds
    cpu_warning: int = 80
    cpu_critical: int = 95
    ram_warning: int = 85
    ram_critical: int = 95
    disk_warning: int = 80
    disk_critical: int = 95
    temp_warning: int = 75
    temp_critical: int = 90
    
    # Monitoring intervals (seconds)
    system_interval: int = 60
    docker_interval: int = 120
    
    # Weekly report schedule
    report_day: str = "sunday"  # monday, tuesday, ..., sunday
    report_hour: int = 9
    report_minute: int = 0
    report_enabled: bool = True
    
    # Alert settings
    alert_cooldown: int = 300  # seconds
    recovery_notify: bool = True
    
    # Temperature sensor whitelist (JSON string in DB)
    temp_sensors: str = '["coretemp", "nvme"]'
    
    # Web UI settings
    web_enabled: bool = True
    web_port: int = 8888
    web_password: str = ""  # Empty = no auth required
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @property
    def temp_sensors_list(self) -> list[str]:
        """Get temperature sensors as list."""
        try:
            return json.loads(self.temp_sensors)
        except (json.JSONDecodeError, TypeError):
            return ["coretemp", "nvme"]
    
    @temp_sensors_list.setter
    def temp_sensors_list(self, sensors: list[str]) -> None:
        """Set temperature sensors from list."""
        self.temp_sensors = json.dumps(sensors)


@dataclass
class AlertRecord:
    """
    Historical alert record.
    
    Stored for statistics and history viewing.
    """
    id: int | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    level: str = "info"  # info, warning, critical, recovery
    title: str = ""
    description: str = ""
    metric_name: str = ""
    current_value: str = ""
    threshold: str = ""
    resolved: bool = False
    resolved_at: datetime | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat() if self.timestamp else None
        data["resolved_at"] = self.resolved_at.isoformat() if self.resolved_at else None
        return data


@dataclass
class ServiceStatus:
    """
    Service connection status for dashboard.
    """
    name: str
    url: str = ""
    connected: bool = False
    last_check: datetime | None = None
    error: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "connected": self.connected,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "error": self.error,
        }


@dataclass
class SystemStats:
    """
    Current system statistics for dashboard.
    """
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    disk_percent: float = 0.0
    disk_used_tb: float = 0.0
    disk_total_tb: float = 0.0
    cpu_temp: float | None = None
    nvme_temp: float | None = None
    uptime_seconds: float = 0.0
    docker_running: int = 0
    docker_total: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data
