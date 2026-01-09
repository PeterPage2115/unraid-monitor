"""
Base classes and interfaces for notification providers.

All notification providers must implement the NotificationProvider interface.
This allows easy swapping between Discord, Telegram, Slack, Email, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"
    RECOVERY = "recovery"


@dataclass
class Alert:
    """
    Represents an alert to be sent via notification provider.
    
    Attributes:
        level: Severity level (info, warning, critical, recovery)
        title: Alert title
        description: Optional detailed description
        metric_name: Name of the metric being monitored
        current_value: Current value that triggered the alert
        threshold: Threshold that was exceeded
        extra_fields: Additional key-value pairs for context
        timestamp: When the alert was generated
    """
    level: AlertLevel | str
    title: str
    description: str | None = None
    metric_name: str | None = None
    current_value: str | None = None
    threshold: str | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Convert string level to enum if needed."""
        if isinstance(self.level, str):
            try:
                self.level = AlertLevel(self.level.lower())
            except ValueError:
                self.level = AlertLevel.INFO


@dataclass
class ReportSection:
    """
    A section within a report.
    
    Attributes:
        title: Section title
        description: Optional section description
        fields: List of field dicts with name, value, inline keys
        color: Section color (provider-specific interpretation)
    """
    title: str
    description: str | None = None
    fields: list[dict[str, Any]] = field(default_factory=list)
    color: str = "info"  # info, success, warning, critical, purple


@dataclass
class Report:
    """
    Represents a full report to be sent via notification provider.
    
    Attributes:
        title: Report title
        sections: List of report sections
        generated_at: When the report was generated
    """
    title: str
    sections: list[ReportSection] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    
    def add_section(
        self,
        title: str,
        description: str | None = None,
        fields: list[dict[str, Any]] | None = None,
        color: str = "info",
    ) -> ReportSection:
        """Add a new section to the report."""
        section = ReportSection(
            title=title,
            description=description,
            fields=fields or [],
            color=color,
        )
        self.sections.append(section)
        return section


class NotificationProvider(ABC):
    """
    Abstract base class for notification providers.
    
    All notification backends (Discord, Telegram, Slack, etc.) must
    implement this interface to be usable by Unraid Monitor.
    
    Example:
        class TelegramProvider(NotificationProvider):
            async def send_alert(self, alert: Alert) -> bool:
                # Send to Telegram
                ...
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'discord', 'telegram')."""
        ...
    
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        ...
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (e.g., establish connections)."""
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up resources (e.g., close connections)."""
        ...
    
    @abstractmethod
    async def send_alert(self, alert: Alert) -> bool:
        """
        Send an alert notification.
        
        Args:
            alert: The alert to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        ...
    
    @abstractmethod
    async def send_report(self, report: Report) -> bool:
        """
        Send a full report.
        
        Args:
            report: The report to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        ...
    
    @abstractmethod
    async def send_test(self, message: str = "Test notification") -> bool:
        """
        Send a test notification to verify configuration.
        
        Args:
            message: Test message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        ...
    
    async def send_startup(self) -> bool:
        """Send a startup notification. Override if supported."""
        return await self.send_test("🚀 Unraid Monitor started")
    
    async def send_shutdown(self) -> bool:
        """Send a shutdown notification. Override if supported."""
        return await self.send_test("🛑 Unraid Monitor stopped")
    
    async def __aenter__(self) -> "NotificationProvider":
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
