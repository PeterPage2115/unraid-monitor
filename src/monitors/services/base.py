"""
Base HTTP client for service APIs.

Provides common functionality for all service clients:
- Async HTTP requests with aiohttp
- Timeout handling
- Error handling and logging
- Session management
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp


logger = logging.getLogger(__name__)


class BaseServiceClient:
    """
    Base class for service API clients.
    
    Provides common HTTP functionality with error handling.
    """
    
    def __init__(
        self,
        base_url: str | None,
        api_key: str | None = None,
        timeout: int = 10,
    ):
        """
        Initialize the service client.
        
        Args:
            base_url: Base URL of the service API
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
    
    @property
    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return bool(self.base_url)
    
    @property
    def name(self) -> str:
        """Service name for logging."""
        return self.__class__.__name__.replace("Client", "")
    
    def _get_headers(self) -> dict[str, str]:
        """
        Get HTTP headers for requests.
        
        Override in subclasses for service-specific headers.
        """
        return {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session
    
    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list | None:
        """
        Make an HTTP request to the service.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            json_data: JSON body for POST/PUT requests
        
        Returns:
            Parsed JSON response or None on error
        """
        if not self.is_configured:
            logger.warning(f"{self.name} is not configured")
            return None
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            session = await self._get_session()
            
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.error(f"{self.name}: Unauthorized - check API key")
                    return None
                elif response.status == 404:
                    logger.debug(f"{self.name}: Endpoint not found: {endpoint}")
                    return None
                else:
                    body = await response.text()
                    logger.error(f"{self.name} API error {response.status}: {body[:200]}")
                    return None
                    
        except aiohttp.ClientError as e:
            logger.error(f"{self.name} network error: {e}")
            return None
        except Exception as e:
            logger.error(f"{self.name} unexpected error: {e}")
            return None
    
    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list | None:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params)
    
    async def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list | None:
        """Make a POST request."""
        return await self._request("POST", endpoint, json_data=json_data)
    
    async def health_check(self) -> bool:
        """
        Check if the service is reachable.
        
        Override in subclasses for service-specific health checks.
        """
        if not self.is_configured:
            return False
        
        try:
            result = await self.get("/")
            return result is not None
        except Exception:
            return False
