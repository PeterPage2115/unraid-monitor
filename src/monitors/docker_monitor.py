"""
Docker container monitor.

Monitors:
- Container status (running, stopped, etc.)
- Container health checks
- Restart counts
- Resource usage (CPU, memory)

Uses the Docker SDK (docker-py) via the mounted Docker socket.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import docker
from docker.errors import DockerException

from monitors.base import BaseMonitor
from alerts.models import AlertLevel, ContainerStatus

if TYPE_CHECKING:
    from config import Config
    from alerts.manager import AlertManager


logger = logging.getLogger(__name__)


class DockerMonitor(BaseMonitor):
    """
    Monitors Docker containers on the host.
    
    Requires Docker socket mount:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    """
    
    def __init__(
        self,
        config: "Config",
        alert_manager: "AlertManager",
    ):
        super().__init__(config, alert_manager)
        
        self._client: docker.DockerClient | None = None
        
        # Track container states for detecting changes
        self._previous_states: dict[str, ContainerStatus] = {}
        
        # Track restart counts over time window
        self._restart_history: dict[str, list[datetime]] = {}
    
    @property
    def name(self) -> str:
        return "Docker Monitor"
    
    def _get_client(self) -> docker.DockerClient:
        """Get or create Docker client."""
        if self._client is None:
            try:
                self._client = docker.from_env()
                logger.debug("Docker client connected")
            except DockerException as e:
                logger.error(f"Failed to connect to Docker: {e}")
                raise
        return self._client
    
    def _is_ignored(self, container_name: str) -> bool:
        """Check if container should be ignored."""
        ignored = self.config.docker.ignored_containers
        
        # Clean up container name (remove leading /)
        clean_name = container_name.lstrip("/")
        
        return clean_name in ignored or container_name in ignored
    
    async def check(self) -> dict[str, Any]:
        """
        Check all Docker containers.
        
        Returns:
            Dictionary with container statuses and summary
        """
        try:
            client = self._get_client()
        except DockerException:
            return {"error": "Failed to connect to Docker", "containers": []}
        
        containers_data = []
        summary = {
            "total": 0,
            "running": 0,
            "stopped": 0,
            "unhealthy": 0,
            "restarting": 0,
        }
        
        try:
            # Get all containers (including stopped)
            containers = client.containers.list(all=True)
            
            for container in containers:
                name = container.name
                
                # Skip ignored containers
                if self._is_ignored(name):
                    logger.debug(f"Skipping ignored container: {name}")
                    continue
                
                # Get container status
                status = await self._get_container_status(container)
                containers_data.append(status.__dict__)
                
                # Update summary
                summary["total"] += 1
                
                if status.status.lower() == "running":
                    summary["running"] += 1
                elif status.status.lower() == "exited":
                    summary["stopped"] += 1
                elif status.status.lower() == "restarting":
                    summary["restarting"] += 1
                
                if status.health and status.health.lower() == "unhealthy":
                    summary["unhealthy"] += 1
                
                # Check for state changes and issues
                await self._check_container_issues(name, status)
                
                # Store current state
                self._previous_states[name] = status
                
        except DockerException as e:
            logger.error(f"Error listing containers: {e}")
            return {"error": str(e), "containers": []}
        
        return {
            "timestamp": datetime.now().isoformat(),
            "containers": containers_data,
            "summary": summary,
        }
    
    async def _get_container_status(self, container) -> ContainerStatus:
        """Get detailed status for a container."""
        # Basic info
        name = container.name
        status = container.status
        
        # Get health if available
        health = None
        try:
            health_data = container.attrs.get("State", {}).get("Health", {})
            if health_data:
                health = health_data.get("Status")
        except Exception:
            pass
        
        # Get image info
        try:
            image_tags = container.image.tags
            image = image_tags[0] if image_tags else str(container.image.id)[:12]
        except Exception:
            image = "unknown"
        
        # Get timestamps
        created = None
        started_at = None
        try:
            created_str = container.attrs.get("Created", "")
            if created_str:
                # Docker uses RFC3339 format
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            
            started_str = container.attrs.get("State", {}).get("StartedAt", "")
            if started_str and not started_str.startswith("0001"):
                started_at = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.debug(f"Error parsing container timestamps: {e}")
        
        # Get restart count
        restart_count = container.attrs.get("RestartCount", 0)
        
        # Get resource stats (only for running containers)
        cpu_percent = 0.0
        memory_usage = 0
        memory_limit = 0
        
        if status.lower() == "running":
            try:
                stats = container.stats(stream=False)
                
                # Calculate CPU percentage
                cpu_delta = (
                    stats["cpu_stats"]["cpu_usage"]["total_usage"]
                    - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                )
                system_delta = (
                    stats["cpu_stats"]["system_cpu_usage"]
                    - stats["precpu_stats"]["system_cpu_usage"]
                )
                
                if system_delta > 0:
                    num_cpus = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1]))
                    cpu_percent = (cpu_delta / system_delta) * num_cpus * 100
                
                # Get memory usage
                memory_usage = stats["memory_stats"].get("usage", 0)
                memory_limit = stats["memory_stats"].get("limit", 0)
                
            except Exception as e:
                logger.debug(f"Error getting container stats for {name}: {e}")
        
        return ContainerStatus(
            name=name,
            status=status,
            health=health,
            image=image,
            created=created,
            started_at=started_at,
            restart_count=restart_count,
            cpu_percent=cpu_percent,
            memory_usage=memory_usage,
            memory_limit=memory_limit,
        )
    
    async def _check_container_issues(
        self,
        name: str,
        current: ContainerStatus,
    ) -> None:
        """Check for container issues and send alerts."""
        previous = self._previous_states.get(name)
        
        # Check 1: Container stopped unexpectedly
        if current.status.lower() in ("exited", "dead"):
            # Only alert if it was previously running
            if previous and previous.is_running:
                await self.alert_manager.process_container_alert(
                    container_name=name,
                    issue_type="stopped",
                    description=f"Container '{name}' has stopped unexpectedly.",
                    level=AlertLevel.WARNING,
                    extra_fields=[
                        {"name": "Image", "value": current.image, "inline": True},
                        {"name": "Status", "value": current.status, "inline": True},
                    ],
                )
        
        # Check 2: Container became unhealthy
        if current.health and current.health.lower() == "unhealthy":
            # Only alert on transition to unhealthy
            if previous is None or previous.health != "unhealthy":
                await self.alert_manager.process_container_alert(
                    container_name=name,
                    issue_type="unhealthy",
                    description=f"Container '{name}' health check is failing.",
                    level=AlertLevel.WARNING,
                    extra_fields=[
                        {"name": "Image", "value": current.image, "inline": True},
                    ],
                )
        
        # Check 3: Recover from unhealthy
        if current.health and current.health.lower() == "healthy":
            if previous and previous.health == "unhealthy":
                await self.alert_manager.clear_container_alert(name, "unhealthy")
        
        # Check 4: Container restarting frequently
        if self.config.docker.monitor_restarts:
            await self._check_restart_frequency(name, current)
        
        # Check 5: Container recovered (started running again)
        if current.is_running and previous and not previous.is_running:
            await self.alert_manager.clear_container_alert(name, "stopped")
    
    async def _check_restart_frequency(
        self,
        name: str,
        status: ContainerStatus,
    ) -> None:
        """Check if container is restarting too frequently."""
        previous = self._previous_states.get(name)
        
        # Detect restart by comparing restart counts
        if previous and status.restart_count > previous.restart_count:
            # Record this restart
            if name not in self._restart_history:
                self._restart_history[name] = []
            
            self._restart_history[name].append(datetime.now())
            
            # Clean old entries outside the window
            window = timedelta(minutes=self.config.docker.restart_window_minutes)
            cutoff = datetime.now() - window
            self._restart_history[name] = [
                t for t in self._restart_history[name] if t > cutoff
            ]
            
            # Check if threshold exceeded
            recent_restarts = len(self._restart_history[name])
            if recent_restarts >= self.config.docker.restart_threshold:
                await self.alert_manager.process_container_alert(
                    container_name=name,
                    issue_type="restart_loop",
                    description=f"Container '{name}' has restarted {recent_restarts} times in the last {self.config.docker.restart_window_minutes} minutes.",
                    level=AlertLevel.CRITICAL,
                    extra_fields=[
                        {"name": "Restarts", "value": str(recent_restarts), "inline": True},
                        {"name": "Window", "value": f"{self.config.docker.restart_window_minutes} min", "inline": True},
                        {"name": "Image", "value": status.image, "inline": True},
                    ],
                )
    
    async def get_report_data(self) -> dict[str, Any]:
        """Get Docker data for weekly report."""
        current = await self.check()
        
        if "error" in current:
            return {
                "available": False,
                "error": current["error"],
            }
        
        summary = current.get("summary", {})
        containers = current.get("containers", [])
        
        # Find top resource consumers
        running_containers = [c for c in containers if c.get("status") == "running"]
        
        top_cpu = sorted(
            running_containers,
            key=lambda c: c.get("cpu_percent", 0),
            reverse=True
        )[:3]
        
        top_memory = sorted(
            running_containers,
            key=lambda c: c.get("memory_usage", 0),
            reverse=True
        )[:3]
        
        return {
            "available": True,
            "summary": summary,
            "top_cpu_containers": [
                {"name": c["name"], "cpu": f"{c['cpu_percent']:.1f}%"}
                for c in top_cpu
            ],
            "top_memory_containers": [
                {"name": c["name"], "memory_mb": c["memory_usage"] / (1024**2)}
                for c in top_memory
            ],
        }
