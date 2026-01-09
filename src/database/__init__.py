"""
Database module for Unraid Monitor.

Provides SQLite-based storage for:
- Application settings
- Alert history
- Statistics

Usage:
    from database import Database
    
    db = Database("/app/data/unraid-monitor.db")
    await db.initialize()
    
    settings = await db.get_settings()
    await db.save_settings({"cpu_warning": 80})
"""

from .connection import Database
from .models import Settings, AlertRecord, ServiceStatus

__all__ = [
    "Database",
    "Settings",
    "AlertRecord",
    "ServiceStatus",
]
