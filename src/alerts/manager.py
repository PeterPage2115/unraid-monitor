"""
Alert Manager - Core alerting logic.

Handles:
- Tracking alert state (active/inactive)
- Cooldown between repeated alerts
- Recovery notifications when metrics return to normal
- State persistence to survive restarts
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Awaitable

from alerts.models import AlertLevel, AlertState, MetricReading

if TYPE_CHECKING:
    from discord_client import DiscordClient
    from config import AlertsConfig


logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manages alert state, cooldowns, and notifications.
    
    Features:
    - Cooldown: Don't spam Discord with repeated alerts
    - Escalation: Upgrade warning -> critical if threshold increases
    - Recovery: Notify when metric returns to normal
    - Hysteresis: Prevent flapping by requiring value to drop below threshold-buffer
    - Persistence: Save state to disk to survive container restarts
    """
    
    def __init__(
        self,
        discord_client: "DiscordClient",
        config: "AlertsConfig",
        state_file: Path | str | None = None,
    ):
        """
        Initialize the AlertManager.
        
        Args:
            discord_client: Discord webhook client for sending notifications
            config: Alert configuration (cooldown, recovery settings)
            state_file: Path to JSON file for persisting state
        """
        self.discord = discord_client
        self.config = config
        
        # State storage
        self._states: dict[str, AlertState] = {}
        
        # Persistence
        if state_file:
            self.state_file = Path(state_file)
        else:
            self.state_file = Path("/app/data/alert_state.json")
        
        # Load existing state if available
        self._load_state()
    
    # =========================================================================
    # State management
    # =========================================================================
    
    def _load_state(self) -> None:
        """Load alert state from disk."""
        if not self.state_file.exists():
            logger.debug("No existing alert state file found")
            return
        
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for key, state_data in data.items():
                self._states[key] = AlertState.from_dict(state_data)
            
            logger.info(f"Loaded {len(self._states)} alert states from disk")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse alert state file: {e}")
        except Exception as e:
            logger.error(f"Failed to load alert state: {e}")
    
    def _save_state(self) -> None:
        """Save alert state to disk."""
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                key: state.to_dict()
                for key, state in self._states.items()
            }
            
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved {len(self._states)} alert states to disk")
            
        except Exception as e:
            logger.error(f"Failed to save alert state: {e}")
    
    def get_state(self, alert_key: str) -> AlertState | None:
        """Get the current state for an alert key."""
        return self._states.get(alert_key)
    
    def get_active_alerts(self) -> list[AlertState]:
        """Get all currently active alerts."""
        return [s for s in self._states.values() if s.is_active]
    
    # =========================================================================
    # Cooldown logic
    # =========================================================================
    
    def _is_in_cooldown(self, state: AlertState) -> bool:
        """
        Check if an alert is in cooldown period.
        
        Args:
            state: Alert state to check
        
        Returns:
            True if still in cooldown, False if can send alert
        """
        if state.last_alert_sent is None:
            return False
        
        cooldown = timedelta(minutes=self.config.cooldown_minutes)
        time_since_last = datetime.now() - state.last_alert_sent
        
        return time_since_last < cooldown
    
    def _should_escalate(self, state: AlertState, new_level: AlertLevel) -> bool:
        """
        Check if alert should escalate (e.g., warning -> critical).
        
        Escalation bypasses cooldown.
        """
        if not state.is_active:
            return False
        
        # Critical > Warning, so if new level is higher, escalate
        return new_level == AlertLevel.CRITICAL and state.level == AlertLevel.WARNING
    
    # =========================================================================
    # Core alert processing
    # =========================================================================
    
    async def process_reading(self, reading: MetricReading) -> bool:
        """
        Process a metric reading and send alerts if needed.
        
        This is the main entry point for the alerting system.
        
        Args:
            reading: The metric reading to process
        
        Returns:
            True if an alert was sent
        """
        alert_key = f"{reading.metric_type.value}_{reading.metric_id}"
        current_level = reading.get_alert_level()
        
        # Get or create state
        state = self._states.get(alert_key)
        if state is None:
            state = AlertState(alert_key=alert_key)
            self._states[alert_key] = state
        
        # Update current value
        state.current_value = reading.value
        
        alert_sent = False
        
        if current_level is not None:
            # Value is above threshold - potential alert
            alert_sent = await self._handle_threshold_exceeded(
                state=state,
                reading=reading,
                level=current_level,
            )
        else:
            # Value is below threshold - check for recovery
            if state.is_active:
                alert_sent = await self._handle_recovery(
                    state=state,
                    reading=reading,
                )
        
        # Persist state
        self._save_state()
        
        return alert_sent
    
    async def _handle_threshold_exceeded(
        self,
        state: AlertState,
        reading: MetricReading,
        level: AlertLevel,
    ) -> bool:
        """Handle a metric that has exceeded its threshold."""
        
        now = datetime.now()
        
        # Update state
        state.threshold_value = (
            reading.critical_threshold if level == AlertLevel.CRITICAL
            else reading.warning_threshold
        )
        state.context = reading.context
        
        # Check if this is a new alert or escalation
        is_new_alert = not state.is_active
        is_escalation = self._should_escalate(state, level)
        
        if is_new_alert:
            # First time crossing threshold
            state.is_active = True
            state.first_triggered = now
            state.level = level
            state.trigger_count = 1
            
            logger.info(f"New alert: {state.alert_key} at level {level.value}")
            
            return await self._send_alert(state, reading, level)
        
        elif is_escalation:
            # Escalating from warning to critical
            state.level = level
            state.trigger_count += 1
            
            logger.info(f"Escalating alert: {state.alert_key} to {level.value}")
            
            return await self._send_alert(
                state, reading, level,
                title_prefix="Escalated: ",
            )
        
        elif not self._is_in_cooldown(state):
            # Repeat alert after cooldown
            state.trigger_count += 1
            
            logger.debug(f"Repeat alert: {state.alert_key} (count: {state.trigger_count})")
            
            return await self._send_alert(
                state, reading, level,
                include_duration=True,
            )
        
        # In cooldown, don't send
        return False
    
    async def _handle_recovery(
        self,
        state: AlertState,
        reading: MetricReading,
    ) -> bool:
        """Handle recovery when metric returns to normal."""
        
        # Check hysteresis - value must be below threshold minus buffer
        if reading.is_above_threshold(self.config.hysteresis_percent):
            # Still in hysteresis zone, don't recover yet
            return False
        
        # Recovery!
        logger.info(f"Recovery: {state.alert_key}")
        
        alert_sent = False
        
        if self.config.recovery_enabled:
            # Calculate how long the alert was active
            duration = ""
            if state.first_triggered:
                delta = datetime.now() - state.first_triggered
                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                if hours > 0:
                    duration = f"{hours}h {minutes}m"
                else:
                    duration = f"{minutes}m"
            
            alert_sent = await self.discord.send_alert(
                level="recovery",
                title=f"{reading.name} Recovered",
                description=f"Value has returned to normal levels.",
                current_value=f"{reading.value:.1f}{reading.unit}",
                threshold=f"< {state.threshold_value:.0f}{reading.unit}" if state.threshold_value else None,
                extra_fields=[
                    {"name": "Duration", "value": duration, "inline": True},
                    {"name": "Peak Level", "value": state.level.value.title() if state.level else "Unknown", "inline": True},
                ] if duration else None,
            )
        
        # Reset state
        state.is_active = False
        state.first_triggered = None
        state.level = AlertLevel.WARNING
        
        return alert_sent
    
    async def _send_alert(
        self,
        state: AlertState,
        reading: MetricReading,
        level: AlertLevel,
        title_prefix: str = "",
        include_duration: bool = False,
    ) -> bool:
        """Send an alert to Discord."""
        
        extra_fields = []
        
        if include_duration and state.first_triggered:
            delta = datetime.now() - state.first_triggered
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                duration = f"{hours}h {minutes}m"
            else:
                duration = f"{minutes}m"
            extra_fields.append({"name": "Duration", "value": duration, "inline": True})
        
        if state.trigger_count > 1:
            extra_fields.append({"name": "Occurrences", "value": str(state.trigger_count), "inline": True})
        
        # Add any context from the reading
        for key, value in reading.context.items():
            extra_fields.append({"name": key, "value": str(value), "inline": True})
        
        success = await self.discord.send_alert(
            level=level.value,
            title=f"{title_prefix}{reading.name} {level.value.title()}",
            current_value=f"{reading.value:.1f}{reading.unit}",
            threshold=f"{state.threshold_value:.0f}{reading.unit}" if state.threshold_value else None,
            extra_fields=extra_fields if extra_fields else None,
        )
        
        if success:
            state.last_alert_sent = datetime.now()
        
        return success
    
    # =========================================================================
    # Container-specific alerts
    # =========================================================================
    
    async def process_container_alert(
        self,
        container_name: str,
        issue_type: str,
        description: str,
        level: AlertLevel = AlertLevel.WARNING,
        extra_fields: list[dict] | None = None,
    ) -> bool:
        """
        Process a Docker container alert.
        
        Args:
            container_name: Name of the container
            issue_type: Type of issue (stopped, unhealthy, restarting)
            description: Description of the issue
            level: Alert level
            extra_fields: Additional fields for the embed
        
        Returns:
            True if alert was sent
        """
        alert_key = f"container_{container_name}_{issue_type}"
        
        state = self._states.get(alert_key)
        if state is None:
            state = AlertState(alert_key=alert_key)
            self._states[alert_key] = state
        
        # Check cooldown
        if state.is_active and self._is_in_cooldown(state):
            return False
        
        # Send alert
        success = await self.discord.send_alert(
            level=level.value,
            title=f"Container {issue_type.title()}: {container_name}",
            description=description,
            extra_fields=extra_fields,
        )
        
        if success:
            now = datetime.now()
            if not state.is_active:
                state.is_active = True
                state.first_triggered = now
                state.trigger_count = 1
            else:
                state.trigger_count += 1
            
            state.level = level
            state.last_alert_sent = now
            self._save_state()
        
        return success
    
    async def clear_container_alert(
        self,
        container_name: str,
        issue_type: str,
    ) -> bool:
        """
        Clear a container alert (container recovered).
        
        Args:
            container_name: Name of the container
            issue_type: Type of issue that was resolved
        
        Returns:
            True if recovery notification was sent
        """
        alert_key = f"container_{container_name}_{issue_type}"
        
        state = self._states.get(alert_key)
        if state is None or not state.is_active:
            return False
        
        alert_sent = False
        
        if self.config.recovery_enabled:
            alert_sent = await self.discord.send_alert(
                level="recovery",
                title=f"Container Recovered: {container_name}",
                description=f"The container is now {issue_type.replace('_', ' ')} resolved.",
            )
        
        state.is_active = False
        state.first_triggered = None
        self._save_state()
        
        return alert_sent
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_statistics(self) -> dict:
        """Get alert statistics for reporting."""
        active_count = len([s for s in self._states.values() if s.is_active])
        total_triggers = sum(s.trigger_count for s in self._states.values())
        
        by_level = {
            "warning": len([s for s in self._states.values() if s.is_active and s.level == AlertLevel.WARNING]),
            "critical": len([s for s in self._states.values() if s.is_active and s.level == AlertLevel.CRITICAL]),
        }
        
        return {
            "active_alerts": active_count,
            "total_triggers": total_triggers,
            "by_level": by_level,
            "states": {k: v.to_dict() for k, v in self._states.items()},
        }
