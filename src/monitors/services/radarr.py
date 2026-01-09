"""
Radarr API client.

Radarr is a movie collection manager for Usenet and BitTorrent users.
API Documentation: https://radarr.video/docs/api/
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from monitors.services.base import BaseServiceClient


logger = logging.getLogger(__name__)


class RadarrClient(BaseServiceClient):
    """
    Client for Radarr API v3.
    
    Provides access to movie collection statistics and history.
    """
    
    def __init__(
        self,
        base_url: str | None,
        api_key: str | None = None,
        timeout: int = 10,
    ):
        super().__init__(base_url, api_key, timeout)
    
    def _get_headers(self) -> dict[str, str]:
        """Radarr uses X-Api-Key header."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers
    
    async def health_check(self) -> bool:
        """Check if Radarr is reachable."""
        result = await self.get("/api/v3/system/status")
        return result is not None
    
    async def get_system_status(self) -> dict[str, Any] | None:
        """Get Radarr system status."""
        return await self.get("/api/v3/system/status")
    
    async def get_movies(self) -> list[dict[str, Any]]:
        """Get all movies in the library."""
        result = await self.get("/api/v3/movie")
        return result if isinstance(result, list) else []
    
    async def get_queue(self) -> dict[str, Any] | None:
        """Get current download queue."""
        return await self.get("/api/v3/queue", params={"pageSize": 100})
    
    async def get_history(
        self,
        page_size: int = 50,
        since_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get recent activity history.
        
        Args:
            page_size: Number of records to fetch
            since_date: Only get history since this date
        
        Returns:
            List of history records
        """
        params: dict[str, Any] = {
            "pageSize": page_size,
            "sortKey": "date",
            "sortDirection": "descending",
        }
        
        result = await self.get("/api/v3/history", params=params)
        
        if not result or not isinstance(result, dict):
            return []
        
        records = result.get("records", [])
        
        # Filter by date if specified
        if since_date:
            filtered = []
            for record in records:
                date_str = record.get("date", "")
                if date_str:
                    try:
                        record_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        if record_date >= since_date.replace(tzinfo=record_date.tzinfo):
                            filtered.append(record)
                    except ValueError:
                        pass
            return filtered
        
        return records
    
    async def get_disk_space(self) -> list[dict[str, Any]]:
        """Get disk space for root folders."""
        result = await self.get("/api/v3/diskspace")
        return result if isinstance(result, list) else []
    
    async def get_stats_for_report(self) -> dict[str, Any]:
        """
        Get statistics for weekly report.
        
        Returns:
            Dictionary with:
            - total_movies: Total movies in library
            - movies_with_files: Movies that have been downloaded
            - movies_missing: Movies not yet downloaded
            - downloaded_this_week: Movies downloaded in last 7 days
            - queue_count: Items currently in queue
            - disk_space: Storage information
        """
        if not self.is_configured:
            return {"available": False}
        
        try:
            # Get all movies
            movies = await self.get_movies()
            total = len(movies)
            with_files = sum(1 for m in movies if m.get("hasFile", False))
            missing = total - with_files
            
            # Get history for last week
            week_ago = datetime.now() - timedelta(days=7)
            history = await self.get_history(page_size=100, since_date=week_ago)
            
            # Count downloaded (imported) movies this week
            downloaded_this_week = sum(
                1 for h in history
                if h.get("eventType") in ("downloadFolderImported", "grabbed")
            )
            
            # Get queue
            queue = await self.get_queue()
            queue_count = queue.get("totalRecords", 0) if queue else 0
            
            # Get disk space
            disk_space = await self.get_disk_space()
            total_space = sum(d.get("totalSpace", 0) for d in disk_space)
            free_space = sum(d.get("freeSpace", 0) for d in disk_space)
            
            return {
                "available": True,
                "total_movies": total,
                "movies_with_files": with_files,
                "movies_missing": missing,
                "downloaded_this_week": downloaded_this_week,
                "queue_count": queue_count,
                "storage": {
                    "total_tb": total_space / (1024**4),
                    "free_tb": free_space / (1024**4),
                    "used_percent": ((total_space - free_space) / total_space * 100) if total_space > 0 else 0,
                },
            }
            
        except Exception as e:
            logger.error(f"Error getting Radarr stats: {e}")
            return {"available": False, "error": str(e)}
