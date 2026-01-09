"""
Immich API client.

Immich is a self-hosted photo and video backup solution.
API Documentation: https://immich.app/docs/api
"""

from __future__ import annotations

import logging
from typing import Any

from monitors.services.base import BaseServiceClient


logger = logging.getLogger(__name__)


class ImmichClient(BaseServiceClient):
    """
    Client for Immich API.
    
    Provides access to photo/video library statistics.
    """
    
    def __init__(
        self,
        base_url: str | None,
        api_key: str | None = None,
        timeout: int = 10,
    ):
        super().__init__(base_url, api_key, timeout)
    
    def _get_headers(self) -> dict[str, str]:
        """Immich uses x-api-key header."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers
    
    async def health_check(self) -> bool:
        """Check if Immich is reachable."""
        result = await self.get("/api/server-info/ping")
        return result is not None and result.get("res") == "pong"
    
    async def get_server_statistics(self) -> dict[str, Any] | None:
        """Get server statistics (photos, videos, usage)."""
        return await self.get("/api/server-info/statistics")
    
    async def get_server_version(self) -> dict[str, Any] | None:
        """Get server version info."""
        return await self.get("/api/server-info/version")
    
    async def get_server_storage(self) -> dict[str, Any] | None:
        """Get storage information."""
        # Try newer endpoint first
        result = await self.get("/api/server-info/storage")
        if result is None:
            # Fall back to older endpoint
            result = await self.get("/api/server-info/stats")
        return result
    
    async def get_users(self) -> list[dict[str, Any]]:
        """Get all users (admin only)."""
        result = await self.get("/api/users")
        return result if isinstance(result, list) else []
    
    async def get_stats_for_report(self) -> dict[str, Any]:
        """
        Get statistics for weekly report.
        
        Returns:
            Dictionary with:
            - total_photos: Total photos in library
            - total_videos: Total videos in library
            - storage_used_gb: Storage used in GB
            - user_count: Number of users
        """
        if not self.is_configured:
            return {"available": False}
        
        try:
            # Get server statistics
            stats = await self.get_server_statistics()
            
            if not stats:
                # Try alternative approach if statistics endpoint fails
                return await self._get_stats_fallback()
            
            # Parse statistics response
            total_photos = stats.get("photos", 0)
            total_videos = stats.get("videos", 0)
            usage_bytes = stats.get("usage", 0)
            
            # Get user stats if available
            users_by_usage = stats.get("usageByUser", [])
            user_count = len(users_by_usage) if users_by_usage else 0
            
            # If no user count from stats, try users endpoint
            if user_count == 0:
                try:
                    users = await self.get_users()
                    user_count = len(users)
                except Exception:
                    pass
            
            return {
                "available": True,
                "total_photos": total_photos,
                "total_videos": total_videos,
                "total_assets": total_photos + total_videos,
                "storage_used_gb": usage_bytes / (1024**3),
                "storage_used_tb": usage_bytes / (1024**4),
                "user_count": user_count,
            }
            
        except Exception as e:
            logger.error(f"Error getting Immich stats: {e}")
            return {"available": False, "error": str(e)}
    
    async def _get_stats_fallback(self) -> dict[str, Any]:
        """Fallback method to get stats if main endpoint fails."""
        try:
            # Try storage endpoint
            storage = await self.get_server_storage()
            
            if storage:
                return {
                    "available": True,
                    "total_photos": storage.get("photos", 0),
                    "total_videos": storage.get("videos", 0),
                    "total_assets": storage.get("photos", 0) + storage.get("videos", 0),
                    "storage_used_gb": storage.get("usage", 0) / (1024**3),
                    "storage_used_tb": storage.get("usage", 0) / (1024**4),
                    "user_count": 0,
                }
            
            return {"available": False, "error": "Could not retrieve statistics"}
            
        except Exception as e:
            return {"available": False, "error": str(e)}
