"""
Web UI module for Unraid Monitor.

Provides a FastAPI-based web interface for:
- Dashboard with real-time system status
- Settings management
- Manual actions (test, force report)
- Log viewing
- Service connection testing
"""

from .app import create_app, WebUI

__all__ = ["create_app", "WebUI"]
