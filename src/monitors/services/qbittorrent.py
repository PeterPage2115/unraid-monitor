"""
qBittorrent API client.

qBittorrent is a free and open-source BitTorrent client.
API Documentation: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from monitors.services.base import BaseServiceClient


logger = logging.getLogger(__name__)


class QBittorrentClient(BaseServiceClient):
    """
    Client for qBittorrent Web API.
    
    Uses cookie-based authentication after login.
    """
    
    def __init__(
        self,
        base_url: str | None,
        username: str | None = None,
        password: str | None = None,
        timeout: int = 10,
    ):
        # qBittorrent doesn't use API key, uses session cookies
        super().__init__(base_url, api_key=None, timeout=timeout)
        self.username = username
        self.password = password
        self._authenticated = False
        self._cookies: dict[str, str] = {}
    
    @property
    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return bool(self.base_url)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get session with cookies."""
        if self._session is None or self._session.closed:
            # Create session with cookie jar
            # unsafe=True allows cookies for IP addresses (not just domains)
            jar = aiohttp.CookieJar(unsafe=True)
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                cookie_jar=jar,
            )
        return self._session
    
    async def _ensure_authenticated(self) -> bool:
        """Ensure we have an authenticated session."""
        if self._authenticated:
            return True
        
        if not self.base_url:
            return False
        
        try:
            session = await self._get_session()
            
            # Login endpoint
            login_url = f"{self.base_url}/api/v2/auth/login"
            data = {
                "username": self.username or "",
                "password": self.password or "",
            }
            
            async with session.post(login_url, data=data) as response:
                if response.status == 200:
                    text = await response.text()
                    if text.strip().lower() == "ok.":
                        self._authenticated = True
                        logger.debug("qBittorrent authentication successful")
                        return True
                    else:
                        logger.warning(f"qBittorrent login failed: {text}")
                        return False
                else:
                    logger.warning(f"qBittorrent login error: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"qBittorrent authentication error: {e}")
            return False
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        _retry: bool = False,
    ) -> dict[str, Any] | list | None:
        """Make authenticated request to qBittorrent."""
        if not await self._ensure_authenticated():
            return None
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            session = await self._get_session()
            
            async with session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            ) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        return await response.json()
                    else:
                        # Some endpoints return plain text
                        text = await response.text()
                        try:
                            import json
                            return json.loads(text)
                        except Exception:
                            return {"text": text}
                elif response.status == 403 and not _retry:
                    # Session expired, try to re-authenticate once
                    self._authenticated = False
                    if await self._ensure_authenticated():
                        return await self._request(method, endpoint, params, json_data, _retry=True)
                    return None
                else:
                    logger.error(f"qBittorrent API error {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"qBittorrent request error: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check if qBittorrent is reachable."""
        result = await self.get("/api/v2/app/version")
        return result is not None
    
    async def get_app_version(self) -> str | None:
        """Get qBittorrent version."""
        result = await self.get("/api/v2/app/version")
        if result and isinstance(result, dict):
            return result.get("text")
        return None
    
    async def get_transfer_info(self) -> dict[str, Any] | None:
        """Get global transfer information."""
        return await self.get("/api/v2/transfer/info")
    
    async def get_torrents(
        self,
        filter_status: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get list of torrents.
        
        Args:
            filter_status: Filter by status (all, downloading, seeding, completed, etc.)
        
        Returns:
            List of torrent info dictionaries
        """
        params = {}
        if filter_status:
            params["filter"] = filter_status
        
        result = await self.get("/api/v2/torrents/info", params=params)
        return result if isinstance(result, list) else []
    
    async def get_stats_for_report(self) -> dict[str, Any]:
        """
        Get statistics for weekly report.
        
        Returns:
            Dictionary with:
            - total_torrents: Total number of torrents
            - downloading: Currently downloading
            - seeding: Currently seeding
            - completed: Completed torrents
            - paused: Paused torrents
            - stalled: Stalled torrents
            - download_speed: Current download speed (bytes/s)
            - upload_speed: Current upload speed (bytes/s)
            - total_downloaded: All-time downloaded (bytes)
            - total_uploaded: All-time uploaded (bytes)
            - ratio: Global share ratio
        """
        if not self.is_configured:
            return {"available": False}
        
        try:
            # Get transfer info
            transfer = await self.get_transfer_info()
            
            if not transfer:
                return {"available": False, "error": "Could not retrieve transfer info"}
            
            # Get torrent counts by status
            all_torrents = await self.get_torrents()
            downloading = await self.get_torrents(filter_status="downloading")
            seeding = await self.get_torrents(filter_status="seeding")
            completed = await self.get_torrents(filter_status="completed")
            paused = await self.get_torrents(filter_status="paused")
            stalled = await self.get_torrents(filter_status="stalled")
            active = await self.get_torrents(filter_status="active")
            
            # Calculate ratio
            total_downloaded = transfer.get("dl_info_data", 0)
            total_uploaded = transfer.get("up_info_data", 0)
            ratio = total_uploaded / total_downloaded if total_downloaded > 0 else 0
            
            # Get recently completed (completed in last 7 days based on completion_on)
            from datetime import datetime, timedelta
            week_ago = datetime.now().timestamp() - (7 * 24 * 60 * 60)
            recently_completed = []
            for t in all_torrents:
                completion = t.get("completion_on", 0)
                if completion > week_ago and completion > 0:
                    recently_completed.append({
                        "name": t.get("name", "Unknown")[:50],  # Truncate long names
                        "size_gb": t.get("size", 0) / (1024**3),
                        "ratio": t.get("ratio", 0),
                    })
            
            # Sort by completion time (most recent first) and limit to 5
            recently_completed = recently_completed[:5]
            
            return {
                "available": True,
                "total_torrents": len(all_torrents),
                "downloading": len(downloading),
                "seeding": len(seeding),
                "completed": len(completed),
                "paused": len(paused),
                "stalled": len(stalled),
                "active": len(active),
                "download_speed": transfer.get("dl_info_speed", 0),
                "upload_speed": transfer.get("up_info_speed", 0),
                "total_downloaded_tb": total_downloaded / (1024**4),
                "total_uploaded_tb": total_uploaded / (1024**4),
                "session_downloaded_gb": total_downloaded / (1024**3),
                "session_uploaded_gb": total_uploaded / (1024**3),
                "ratio": ratio,
                "recently_completed": recently_completed,
            }
            
        except Exception as e:
            logger.error(f"Error getting qBittorrent stats: {e}")
            return {"available": False, "error": str(e)}
