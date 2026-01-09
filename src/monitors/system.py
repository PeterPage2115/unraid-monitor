"""
System monitor for host metrics.

Monitors:
- CPU usage
- Memory usage
- Disk usage
- Temperature sensors

Uses psutil with host mounts for accessing the host system metrics
from within a Docker container.
"""

from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

# CRITICAL: Set environment variables BEFORE importing psutil
# This allows psutil to read host metrics instead of container metrics
os.environ.setdefault("HOST_PROC", "/host/proc")
os.environ.setdefault("HOST_SYS", "/host/sys")

import psutil

from monitors.base import BaseMonitor
from alerts.models import MetricType, MetricReading

if TYPE_CHECKING:
    from config import Config
    from alerts.manager import AlertManager


logger = logging.getLogger(__name__)


class SystemMonitor(BaseMonitor):
    """
    Monitors host system metrics.
    
    Requires the following Docker volume mounts:
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
    """
    
    def __init__(
        self,
        config: "Config",
        alert_manager: "AlertManager",
    ):
        super().__init__(config, alert_manager)
        
        # Track historical data for averages
        self._cpu_history: list[float] = []
        self._memory_history: list[float] = []
        self._start_time = datetime.now()
    
    @property
    def name(self) -> str:
        return "System Monitor"
    
    async def check(self) -> dict[str, Any]:
        """
        Check all system metrics.
        
        Returns:
            Dictionary with CPU, memory, disk, and temperature data
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "cpu": await self._check_cpu(),
            "memory": await self._check_memory(),
            "disks": await self._check_disks(),
            "temperatures": await self._check_temperatures(),
        }
        
        return data
    
    async def _check_cpu(self) -> dict[str, Any]:
        """Check CPU usage."""
        # Get CPU percentage (blocking call with interval)
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Track history for averages
        self._cpu_history.append(cpu_percent)
        if len(self._cpu_history) > 100:  # Keep last 100 readings
            self._cpu_history.pop(0)
        
        # Get per-core usage
        per_cpu = psutil.cpu_percent(interval=0, percpu=True)
        
        # Get CPU frequency if available
        try:
            freq = psutil.cpu_freq()
            freq_current = freq.current if freq else None
        except Exception:
            freq_current = None
        
        # Create reading and process through alert manager
        reading = MetricReading(
            metric_type=MetricType.CPU,
            metric_id="cpu",
            name="CPU Usage",
            value=cpu_percent,
            unit="%",
            warning_threshold=self.config.thresholds.cpu.warning,
            critical_threshold=self.config.thresholds.cpu.critical,
        )
        
        await self.alert_manager.process_reading(reading)
        
        return {
            "percent": cpu_percent,
            "per_cpu": per_cpu,
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "frequency_mhz": freq_current,
        }
    
    async def _check_memory(self) -> dict[str, Any]:
        """Check memory usage."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Track history
        self._memory_history.append(mem.percent)
        if len(self._memory_history) > 100:
            self._memory_history.pop(0)
        
        # Create reading and process
        reading = MetricReading(
            metric_type=MetricType.MEMORY,
            metric_id="memory",
            name="Memory Usage",
            value=mem.percent,
            unit="%",
            warning_threshold=self.config.thresholds.memory.warning,
            critical_threshold=self.config.thresholds.memory.critical,
            context={
                "Used": f"{mem.used / (1024**3):.1f} GB",
                "Total": f"{mem.total / (1024**3):.1f} GB",
            }
        )
        
        await self.alert_manager.process_reading(reading)
        
        return {
            "percent": mem.percent,
            "used_bytes": mem.used,
            "total_bytes": mem.total,
            "available_bytes": mem.available,
            "swap_percent": swap.percent,
            "swap_used_bytes": swap.used,
            "swap_total_bytes": swap.total,
        }
    
    async def _check_disks(self) -> list[dict[str, Any]]:
        """Check disk usage for all mounted partitions."""
        disks = []
        
        # Get all disk partitions
        partitions = psutil.disk_partitions(all=False)
        
        for partition in partitions:
            try:
                # Skip special filesystems
                if partition.fstype in ("squashfs", "tmpfs", "devtmpfs", "overlay"):
                    continue
                
                usage = psutil.disk_usage(partition.mountpoint)
                
                disk_data = {
                    "mountpoint": partition.mountpoint,
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "percent": usage.percent,
                    "used_bytes": usage.used,
                    "total_bytes": usage.total,
                    "free_bytes": usage.free,
                }
                disks.append(disk_data)
                
                # Only alert for important mount points
                important_mounts = ["/", "/mnt/user", "/mnt/cache"]
                should_alert = any(
                    partition.mountpoint.startswith(m) 
                    for m in important_mounts
                )
                
                if should_alert:
                    # Create metric ID from mountpoint
                    metric_id = partition.mountpoint.replace("/", "_").strip("_") or "root"
                    
                    reading = MetricReading(
                        metric_type=MetricType.DISK,
                        metric_id=metric_id,
                        name=f"Disk {partition.mountpoint}",
                        value=usage.percent,
                        unit="%",
                        warning_threshold=self.config.thresholds.disk.warning,
                        critical_threshold=self.config.thresholds.disk.critical,
                        context={
                            "Free": f"{usage.free / (1024**3):.1f} GB",
                            "Total": f"{usage.total / (1024**3):.1f} GB",
                        }
                    )
                    
                    await self.alert_manager.process_reading(reading)
                    
            except PermissionError:
                logger.debug(f"Permission denied for {partition.mountpoint}")
            except Exception as e:
                logger.debug(f"Error checking disk {partition.mountpoint}: {e}")
        
        return disks
    
    def _should_monitor_sensor(self, sensor_name: str, label: str) -> bool:
        """
        Check if a temperature sensor should be monitored based on config.
        
        Args:
            sensor_name: The sensor name (e.g., 'coretemp', 'nct6798')
            label: The sensor label (e.g., 'Core 0', 'AUXTIN1')
        
        Returns:
            True if sensor should be monitored
        """
        whitelist = self.config.temperature_sensors.whitelist
        blacklist = self.config.temperature_sensors.blacklist
        
        # If whitelist is set, only allow those sensors
        if whitelist:
            for allowed in whitelist:
                if allowed.lower() in sensor_name.lower():
                    return True
            return False
        
        # Otherwise, check blacklist
        for blocked in blacklist:
            if blocked.lower() in label.lower() or blocked.lower() in sensor_name.lower():
                return False
        
        return True
    
    async def _check_temperatures(self) -> dict[str, list[dict[str, Any]]]:
        """Check temperature sensors."""
        temps = {}
        
        try:
            # Get all temperature sensors
            sensors = psutil.sensors_temperatures()
            
            if not sensors:
                logger.debug("No temperature sensors found")
                return temps
            
            for name, entries in sensors.items():
                sensor_temps = []
                
                for entry in entries:
                    label = entry.label or name
                    
                    # Skip sensors not in whitelist or in blacklist
                    if not self._should_monitor_sensor(name, label):
                        logger.debug(f"Skipping filtered sensor: {name} - {label}")
                        continue
                    
                    temp_data = {
                        "label": label,
                        "current": entry.current,
                        "high": entry.high,
                        "critical": entry.critical,
                    }
                    sensor_temps.append(temp_data)
                    
                    # Only alert for significant temperature readings
                    if entry.current > 0:  # Ignore invalid readings
                        metric_id = f"{name}_{label}".replace(" ", "_").lower()
                        
                        reading = MetricReading(
                            metric_type=MetricType.TEMPERATURE,
                            metric_id=metric_id,
                            name=f"Temp {label}",
                            value=entry.current,
                            unit="°C",
                            warning_threshold=self.config.thresholds.temperature.warning,
                            critical_threshold=self.config.thresholds.temperature.critical,
                        )
                        
                        await self.alert_manager.process_reading(reading)
                
                if sensor_temps:  # Only add if there are valid sensors
                    temps[name] = sensor_temps
                
        except Exception as e:
            logger.warning(f"Error reading temperatures: {e}")
        
        return temps
    
    async def get_report_data(self) -> dict[str, Any]:
        """Get system data for weekly report."""
        # Get current data
        current = await self.check()
        
        # Calculate averages from history
        cpu_avg = sum(self._cpu_history) / len(self._cpu_history) if self._cpu_history else 0
        mem_avg = sum(self._memory_history) / len(self._memory_history) if self._memory_history else 0
        
        # Calculate uptime
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.now().timestamp() - boot_time
        except Exception:
            uptime_seconds = 0
        
        # Find main disk (user share)
        main_disk = next(
            (d for d in current.get("disks", []) if d["mountpoint"] == "/mnt/user"),
            current.get("disks", [{}])[0] if current.get("disks") else {}
        )
        
        # Find cache disk
        cache_disk = next(
            (d for d in current.get("disks", []) if d["mountpoint"] == "/mnt/cache"),
            None
        )
        
        # All disk info for detailed view
        all_disks = []
        for disk in current.get("disks", []):
            mount = disk.get("mountpoint", "")
            # Skip unraid system mounts
            if mount.startswith("/boot") or mount == "/":
                continue
            all_disks.append({
                "mount": mount,
                "device": disk.get("device", ""),
                "percent": disk.get("percent", 0),
                "used_gb": disk.get("used_bytes", 0) / (1024**3),
                "total_gb": disk.get("total_bytes", 0) / (1024**3),
                "free_gb": disk.get("free_bytes", 0) / (1024**3),
            })
        
        # Get max temp
        max_temp = 0
        all_temps = []
        for sensor_name, sensor_temps in current.get("temperatures", {}).items():
            for temp in sensor_temps:
                if temp["current"] > max_temp:
                    max_temp = temp["current"]
                if temp["current"] > 0:
                    all_temps.append({
                        "sensor": sensor_name,
                        "label": temp["label"],
                        "current": temp["current"],
                        "high": temp.get("high"),
                        "critical": temp.get("critical"),
                    })
        
        return {
            "cpu": {
                "average": cpu_avg,
                "cores": current.get("cpu", {}).get("cores", 0),
                "threads": current.get("cpu", {}).get("threads", 0),
                "frequency_mhz": current.get("cpu", {}).get("frequency_mhz"),
            },
            "memory": {
                "average": mem_avg,
                "total_gb": current.get("memory", {}).get("total_bytes", 0) / (1024**3),
                "used_gb": current.get("memory", {}).get("used_bytes", 0) / (1024**3),
                "available_gb": current.get("memory", {}).get("available_bytes", 0) / (1024**3),
                "swap_percent": current.get("memory", {}).get("swap_percent", 0),
            },
            "disk": {
                "main_percent": main_disk.get("percent", 0),
                "main_total_tb": main_disk.get("total_bytes", 0) / (1024**4),
                "main_free_tb": main_disk.get("free_bytes", 0) / (1024**4),
                "main_used_tb": main_disk.get("used_bytes", 0) / (1024**4),
                "cache_percent": cache_disk.get("percent", 0) if cache_disk else None,
                "cache_total_gb": cache_disk.get("total_bytes", 0) / (1024**3) if cache_disk else None,
                "cache_free_gb": cache_disk.get("free_bytes", 0) / (1024**3) if cache_disk else None,
                "all_disks": all_disks,
            },
            "temperature": {
                "max": max_temp,
                "all_temps": all_temps,
            },
            "uptime_seconds": uptime_seconds,
        }
