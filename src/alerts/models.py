"""
Alert data models.

Defines enums and dataclasses for alert management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AlertLevel(Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    RECOVERY = "recovery"
    
    @property
    def emoji(self) -> str:
        """Get emoji for this alert level."""
        emojis = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.CRITICAL: "🚨",
            AlertLevel.RECOVERY: "✅",
        }
        return emojis.get(self, "ℹ️")
    
    @property
    def color_hex(self) -> int:
        """Get Discord color for this alert level."""
        colors = {
            AlertLevel.INFO: 0x3498DB,      # Blue
            AlertLevel.WARNING: 0xF39C12,   # Orange
            AlertLevel.CRITICAL: 0xE74C3C,  # Red
            AlertLevel.RECOVERY: 0x2ECC71,  # Green
        }
        return colors.get(self, 0x3498DB)
    
    def __lt__(self, other: "AlertLevel") -> bool:
        """Compare alert levels for severity ordering."""
        order = [AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.CRITICAL]
        if self not in order or other not in order:
            return False
        return order.index(self) < order.index(other)


class MetricType(Enum):
    """Types of metrics being monitored."""
    
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    TEMPERATURE = "temperature"
    DOCKER_CONTAINER = "docker_container"
    DOCKER_RESTART = "docker_restart"
    SERVICE_HEALTH = "service_health"
    ARRAY_STATUS = "array_status"


@dataclass
class AlertState:
    """
    Represents the current state of an alert.
    
    Tracks whether an alert is active, when it was last triggered,
    and how many times it has fired.
    """
    
    # Unique key for this alert (e.g., "cpu_high", "disk_sda_high")
    alert_key: str
    
    # Current metric value that triggered the alert
    current_value: float | None = None
    
    # Threshold that was exceeded
    threshold_value: float | None = None
    
    # Alert level (warning, critical)
    level: AlertLevel = AlertLevel.WARNING
    
    # Is the alert currently active (value above threshold)?
    is_active: bool = False
    
    # When was the alert first triggered?
    first_triggered: datetime | None = None
    
    # When was the last alert sent to Discord?
    last_alert_sent: datetime | None = None
    
    # How many times has this alert been triggered?
    trigger_count: int = 0
    
    # Additional context about the alert
    context: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary for persistence."""
        return {
            "alert_key": self.alert_key,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "level": self.level.value if self.level else None,
            "is_active": self.is_active,
            "first_triggered": self.first_triggered.isoformat() if self.first_triggered else None,
            "last_alert_sent": self.last_alert_sent.isoformat() if self.last_alert_sent else None,
            "trigger_count": self.trigger_count,
            "context": self.context,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlertState":
        """Deserialize state from dictionary."""
        return cls(
            alert_key=data["alert_key"],
            current_value=data.get("current_value"),
            threshold_value=data.get("threshold_value"),
            level=AlertLevel(data["level"]) if data.get("level") else AlertLevel.WARNING,
            is_active=data.get("is_active", False),
            first_triggered=datetime.fromisoformat(data["first_triggered"]) if data.get("first_triggered") else None,
            last_alert_sent=datetime.fromisoformat(data["last_alert_sent"]) if data.get("last_alert_sent") else None,
            trigger_count=data.get("trigger_count", 0),
            context=data.get("context", {}),
        )


@dataclass
class MetricReading:
    """
    A single metric reading from monitoring.
    
    Contains the raw value, thresholds, and metadata about the metric.
    """
    
    # Type of metric
    metric_type: MetricType
    
    # Unique identifier (e.g., "cpu", "disk_/mnt/user", "temp_sda")
    metric_id: str
    
    # Human-readable name
    name: str
    
    # Current value
    value: float
    
    # Unit of measurement
    unit: str = "%"
    
    # Warning threshold
    warning_threshold: float | None = None
    
    # Critical threshold
    critical_threshold: float | None = None
    
    # Additional context
    context: dict[str, Any] = field(default_factory=dict)
    
    # Timestamp of reading
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_alert_level(self) -> AlertLevel | None:
        """
        Determine if this reading should trigger an alert.
        
        Returns:
            AlertLevel if threshold exceeded, None otherwise
        """
        if self.critical_threshold is not None and self.value >= self.critical_threshold:
            return AlertLevel.CRITICAL
        if self.warning_threshold is not None and self.value >= self.warning_threshold:
            return AlertLevel.WARNING
        return None
    
    def is_above_threshold(self, hysteresis_percent: float = 0) -> bool:
        """
        Check if value is above any threshold.
        
        Args:
            hysteresis_percent: Buffer below threshold for recovery
        
        Returns:
            True if above threshold (minus hysteresis)
        """
        effective_warning = (self.warning_threshold or 0) - hysteresis_percent
        return self.value >= effective_warning


@dataclass
class ContainerStatus:
    """Status of a Docker container."""
    
    name: str
    status: str  # running, exited, paused, restarting
    health: str | None = None  # healthy, unhealthy, starting, None
    image: str = ""
    created: datetime | None = None
    started_at: datetime | None = None
    restart_count: int = 0
    cpu_percent: float = 0.0
    memory_usage: int = 0
    memory_limit: int = 0
    
    @property
    def memory_percent(self) -> float:
        """Calculate memory usage percentage."""
        if self.memory_limit > 0:
            return (self.memory_usage / self.memory_limit) * 100
        return 0.0
    
    @property
    def is_running(self) -> bool:
        """Check if container is running."""
        return self.status.lower() == "running"
    
    @property
    def is_healthy(self) -> bool:
        """Check if container is healthy (or has no health check)."""
        return self.health is None or self.health.lower() == "healthy"
