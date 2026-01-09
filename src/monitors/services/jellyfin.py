"""
Jellyfin API client.

Jellyfin is a free and open-source media server.
API Documentation: https://api.jellyfin.org/
"""

from __future__ import annotations

import logging
from typing import Any

from monitors.services.base import BaseServiceClient


logger = logging.getLogger(__name__)


class JellyfinClient(BaseServiceClient):
    """
    Client for Jellyfin API.
    
    Provides access to media library statistics and playback information.
    """
    
    def __init__(
        self,
        base_url: str | None,
        api_key: str | None = None,
        timeout: int = 10,
    ):
        super().__init__(base_url, api_key, timeout)
    
    def _get_headers(self) -> dict[str, str]:
        """Jellyfin uses X-Emby-Token header (Jellyfin is fork of Emby)."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Emby-Token"] = self.api_key
        return headers
    
    async def health_check(self) -> bool:
        """Check if Jellyfin is reachable."""
        result = await self.get("/System/Info/Public")
        return result is not None
    
    async def get_system_info(self) -> dict[str, Any] | None:
        """Get system information."""
        return await self.get("/System/Info")
    
    async def get_item_counts(self) -> dict[str, Any] | None:
        """Get counts for all item types."""
        return await self.get("/Items/Counts")
    
    async def get_sessions(self) -> list[dict[str, Any]]:
        """Get active sessions (who's watching)."""
        result = await self.get("/Sessions")
        return result if isinstance(result, list) else []
    
    async def get_users(self) -> list[dict[str, Any]]:
        """Get all users."""
        result = await self.get("/Users")
        return result if isinstance(result, list) else []
    
    async def get_libraries(self) -> list[dict[str, Any]]:
        """Get all media libraries."""
        result = await self.get("/Library/VirtualFolders")
        return result if isinstance(result, list) else []
    
    async def get_activity_log(
        self,
        limit: int = 50,
    ) -> dict[str, Any] | None:
        """
        Get recent activity log.
        
        Args:
            limit: Maximum number of entries to return
        
        Returns:
            Activity log entries
        """
        params = {
            "limit": limit,
        }
        return await self.get("/System/ActivityLog/Entries", params=params)
    
    async def get_latest_items(
        self,
        user_id: str,
        item_type: str = "Movie",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get latest items added to the library.
        
        Args:
            user_id: User ID to get latest items for
            item_type: Type of items (Movie, Series, Episode)
            limit: Maximum number of items to return
        
        Returns:
            List of latest items
        """
        params = {
            "IncludeItemTypes": item_type,
            "Limit": limit,
            "Fields": "DateCreated",
        }
        result = await self.get(f"/Users/{user_id}/Items/Latest", params=params)
        return result if isinstance(result, list) else []
    
    async def get_stats_for_report(self) -> dict[str, Any]:
        """
        Get statistics for weekly report.
        
        Returns:
            Dictionary with:
            - movie_count: Total movies
            - series_count: Total TV series
            - episode_count: Total TV episodes
            - album_count: Total music albums
            - song_count: Total songs
            - active_streams: Currently active streams
            - user_count: Number of users
            - recent_movies: Recently added movies
            - recent_series: Recently added series
        """
        if not self.is_configured:
            return {"available": False}
        
        try:
            # Get item counts
            counts = await self.get_item_counts()
            
            if not counts:
                return {"available": False, "error": "Could not retrieve item counts"}
            
            # Get active sessions
            sessions = await self.get_sessions()
            active_streams = sum(
                1 for s in sessions
                if s.get("NowPlayingItem") is not None
            )
            
            # Get currently playing info
            now_playing = []
            for session in sessions:
                if session.get("NowPlayingItem"):
                    item = session["NowPlayingItem"]
                    now_playing.append({
                        "user": session.get("UserName", "Unknown"),
                        "title": item.get("Name", "Unknown"),
                        "type": item.get("Type", "Unknown"),
                        "client": session.get("Client", "Unknown"),
                    })
            
            # Get users
            users = await self.get_users()
            user_count = len(users)
            
            # Get first admin user for fetching latest items
            admin_user_id = None
            for user in users:
                if user.get("Policy", {}).get("IsAdministrator"):
                    admin_user_id = user.get("Id")
                    break
            
            # Get recently added movies and series
            recent_movies = []
            recent_series = []
            
            if admin_user_id:
                movies = await self.get_latest_items(admin_user_id, "Movie", 5)
                for m in movies:
                    recent_movies.append({
                        "name": m.get("Name", "Unknown"),
                        "year": m.get("ProductionYear"),
                        "date_added": m.get("DateCreated", ""),
                    })
                
                series = await self.get_latest_items(admin_user_id, "Series", 5)
                for s in series:
                    recent_series.append({
                        "name": s.get("Name", "Unknown"),
                        "year": s.get("ProductionYear"),
                        "date_added": s.get("DateCreated", ""),
                    })
            
            return {
                "available": True,
                "movie_count": counts.get("MovieCount", 0),
                "series_count": counts.get("SeriesCount", 0),
                "episode_count": counts.get("EpisodeCount", 0),
                "album_count": counts.get("AlbumCount", 0),
                "song_count": counts.get("SongCount", 0),
                "artist_count": counts.get("ArtistCount", 0),
                "active_streams": active_streams,
                "now_playing": now_playing,
                "user_count": user_count,
                "recent_movies": recent_movies,
                "recent_series": recent_series,
            }
            
        except Exception as e:
            logger.error(f"Error getting Jellyfin stats: {e}")
            return {"available": False, "error": str(e)}
