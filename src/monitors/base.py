"""
Base monitor abstract class.

All monitors inherit from this class and implement the check() method.
This provides a consistent interface for the scheduler.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from config import Config
    from alerts.manager import AlertManager


logger = logging.getLogger(__name__)


class BaseMonitor(ABC):
    """
    Abstract base class for all monitors.
    
    Monitors are responsible for:
    1. Collecting metrics from their data source
    2. Processing readings through the AlertManager
    3. Providing data for weekly reports
    """
    
    def __init__(
        self,
        config: "Config",
        alert_manager: "AlertManager",
    ):
        """
        Initialize the monitor.
        
        Args:
            config: Application configuration
            alert_manager: Alert manager for processing readings
        """
        self.config = config
        self.alert_manager = alert_manager
        self._last_check_data: dict[str, Any] = {}
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this monitor."""
        pass
    
    @abstractmethod
    async def check(self) -> dict[str, Any]:
        """
        Perform a monitoring check.
        
        This method should:
        1. Collect current metrics
        2. Process them through alert_manager.process_reading()
        3. Return the collected data
        
        Returns:
            Dictionary with collected metrics
        """
        pass
    
    @abstractmethod
    async def get_report_data(self) -> dict[str, Any]:
        """
        Get data for weekly reports.
        
        Returns:
            Dictionary with data to include in reports
        """
        pass
    
    async def safe_check(self) -> dict[str, Any] | None:
        """
        Safely perform a check, catching and logging any errors.
        
        Returns:
            Check result or None if an error occurred
        """
        try:
            result = await self.check()
            self._last_check_data = result
            return result
        except Exception as e:
            logger.error(f"Error in {self.name} monitor: {e}", exc_info=True)
            return None
    
    def get_last_data(self) -> dict[str, Any]:
        """Get data from the last successful check."""
        return self._last_check_data
