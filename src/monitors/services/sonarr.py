"""
Sonarr API client.

Sonarr is a TV series collection manager for Usenet and BitTorrent users.
API Documentation: https://sonarr.tv/docs/api/
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from monitors.services.base import BaseServiceClient


logger = logging.getLogger(__name__)


class SonarrClient(BaseServiceClient):
    """
    Client for Sonarr API v3.
    
    Provides access to TV series collection statistics and history.
    """
    
    def __init__(
        self,
        base_url: str | None,
        api_key: str | None = None,
        timeout: int = 10,
    ):
        super().__init__(base_url, api_key, timeout)
    
    def _get_headers(self) -> dict[str, str]:
        """Sonarr uses X-Api-Key header."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers
    
    async def health_check(self) -> bool:
        """Check if Sonarr is reachable."""
        result = await self.get("/api/v3/system/status")
        return result is not None
    
    async def get_series(self) -> list[dict[str, Any]]:
        """Get all TV series in the library."""
        result = await self.get("/api/v3/series")
        return result if isinstance(result, list) else []
    
    async def get_queue(self) -> dict[str, Any] | None:
        """Get current download queue."""
        return await self.get("/api/v3/queue", params={"pageSize": 100})
    
    async def get_history(
        self,
        page_size: int = 100,
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
    
    async def get_calendar(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get upcoming episodes.
        
        Args:
            start: Start date (default: today)
            end: End date (default: 7 days from now)
        
        Returns:
            List of upcoming episodes
        """
        if start is None:
            start = datetime.now()
        if end is None:
            end = start + timedelta(days=7)
        
        params = {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
        }
        
        result = await self.get("/api/v3/calendar", params=params)
        return result if isinstance(result, list) else []
    
    async def get_disk_space(self) -> list[dict[str, Any]]:
        """Get disk space for root folders."""
        result = await self.get("/api/v3/diskspace")
        return result if isinstance(result, list) else []
    
    async def get_stats_for_report(self) -> dict[str, Any]:
        """
        Get statistics for weekly report.
        
        Returns:
            Dictionary with:
            - total_series: Total TV series in library
            - total_episodes: Total episodes tracked
            - episodes_with_files: Episodes that have been downloaded
            - downloaded_this_week: Episodes downloaded in last 7 days
            - upcoming_episodes: Episodes airing in next 7 days
            - queue_count: Items currently in queue
        """
        if not self.is_configured:
            return {"available": False}
        
        try:
            # Get all series
            series_list = await self.get_series()
            total_series = len(series_list)
            
            # Count episodes from statistics object
            total_episodes = 0
            episodes_with_files = 0
            total_all_episodes = 0
            total_size = 0
            
            for s in series_list:
                stats = s.get("statistics", {})
                total_episodes += stats.get("episodeCount", 0)
                episodes_with_files += stats.get("episodeFileCount", 0)
                total_all_episodes += stats.get("totalEpisodeCount", 0)
                total_size += stats.get("sizeOnDisk", 0)
            
            # Get history for last week
            week_ago = datetime.now() - timedelta(days=7)
            history = await self.get_history(page_size=200, since_date=week_ago)
            
            # Count downloaded episodes this week
            downloaded_this_week = sum(
                1 for h in history
                if h.get("eventType") in ("downloadFolderImported", "grabbed")
            )
            
            # Get upcoming episodes with details
            upcoming = await self.get_calendar()
            upcoming_count = len(upcoming)
            
            # Get series names for upcoming episodes
            series_dict = {s.get("id"): s.get("title", "Unknown") for s in series_list}
            upcoming_details = []
            for ep in upcoming[:5]:  # Limit to 5 for display
                series_name = series_dict.get(ep.get("seriesId"), "Unknown")
                upcoming_details.append({
                    "series": series_name,
                    "season": ep.get("seasonNumber", 0),
                    "episode": ep.get("episodeNumber", 0),
                    "title": ep.get("title", "TBA"),
                    "air_date": ep.get("airDate", ""),
                })
            
            # Get queue
            queue = await self.get_queue()
            queue_count = queue.get("totalRecords", 0) if queue else 0
            
            # Get disk space
            disk_space = await self.get_disk_space()
            total_space = sum(d.get("totalSpace", 0) for d in disk_space)
            free_space = sum(d.get("freeSpace", 0) for d in disk_space)
            
            return {
                "available": True,
                "total_series": total_series,
                "total_episodes": total_episodes,  # Monitored episodes
                "episodes_with_files": episodes_with_files,  # Downloaded episodes
                "total_all_episodes": total_all_episodes,  # All episodes (including unaired)
                "downloaded_this_week": downloaded_this_week,
                "upcoming_episodes": upcoming_count,
                "upcoming_details": upcoming_details,  # Detailed list of upcoming
                "queue_count": queue_count,
                "size_on_disk_gb": total_size / (1024**3),
                "storage": {
                    "total_tb": total_space / (1024**4),
                    "free_tb": free_space / (1024**4),
                    "used_percent": ((total_space - free_space) / total_space * 100) if total_space > 0 else 0,
                },
            }
            
        except Exception as e:
            logger.error(f"Error getting Sonarr stats: {e}")
            return {"available": False, "error": str(e)}
