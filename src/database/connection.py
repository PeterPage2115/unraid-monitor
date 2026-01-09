"""
SQLite database connection and operations.

Provides async-compatible database operations using aiosqlite.
Handles schema creation, migrations, and CRUD operations.
"""

from __future__ import annotations

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any
import sqlite3
import threading

from .models import Settings, AlertRecord, ServiceStatus, SystemStats


logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager for Unraid Monitor.
    
    Uses synchronous sqlite3 (thread-safe) as aiosqlite adds complexity.
    All operations are quick enough that async isn't needed.
    
    Features:
    - Auto-creates schema on first run
    - Settings persistence with defaults
    - Alert history with pagination
    - Thread-safe operations
    """
    
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: str | Path = "/app/data/unraid-monitor.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._settings_cache: Settings | None = None
    
    def initialize(self) -> None:
        """Create database and tables if they don't exist."""
        # Ensure directory exists with proper permissions
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.warning(f"Cannot create directory {self.db_path.parent}, using /tmp")
            self.db_path = Path("/tmp/unraid_monitor.db")
        
        try:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0,
            )
            self._conn.row_factory = sqlite3.Row
            
            self._create_tables()
            self._ensure_defaults()
            
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.OperationalError as e:
            logger.warning(f"Cannot open database at {self.db_path}: {e}, trying /tmp")
            self.db_path = Path("/tmp/unraid_monitor.db")
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0,
            )
            self._conn.row_factory = sqlite3.Row
            self._create_tables()
            self._ensure_defaults()
            logger.info(f"Database initialized at {self.db_path} (fallback)")
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def _create_tables(self) -> None:
        """Create database tables."""
        with self._lock:
            cursor = self._conn.cursor()
            
            # Settings table (key-value store)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Alert history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    metric_name TEXT,
                    current_value TEXT,
                    threshold TEXT,
                    resolved INTEGER DEFAULT 0,
                    resolved_at TEXT
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_timestamp 
                ON alert_history(timestamp DESC)
            """)
            
            # Schema version
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            cursor.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("schema_version", str(self.SCHEMA_VERSION))
            )
            
            self._conn.commit()
    
    def _ensure_defaults(self) -> None:
        """Ensure default settings exist."""
        defaults = Settings()
        current = self._get_settings_dict()
        
        # Add any missing settings
        for key, value in defaults.to_dict().items():
            if key not in current:
                self._set_setting(key, value)
    
    # =========================================================================
    # Settings Operations
    # =========================================================================
    
    def _get_settings_dict(self) -> dict[str, Any]:
        """Get all settings as dictionary."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()
        
        result = {}
        for row in rows:
            key, value = row["key"], row["value"]
            # Try to parse as JSON (for complex types)
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                result[key] = value
        
        return result
    
    def _set_setting(self, key: str, value: Any) -> None:
        """Set a single setting."""
        # Convert to JSON for storage
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        elif isinstance(value, bool):
            value_str = json.dumps(value)  # True/False as true/false
        else:
            value_str = str(value)
        
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO settings (key, value, updated_at) 
                   VALUES (?, ?, ?)""",
                (key, value_str, datetime.now().isoformat())
            )
            self._conn.commit()
        
        # Invalidate cache
        self._settings_cache = None
    
    def get_settings(self) -> Settings:
        """
        Get application settings.
        
        Returns cached settings if available.
        """
        if self._settings_cache is not None:
            return self._settings_cache
        
        data = self._get_settings_dict()
        self._settings_cache = Settings.from_dict(data)
        return self._settings_cache
    
    def save_settings(self, settings: Settings | dict[str, Any]) -> None:
        """
        Save settings to database.
        
        Args:
            settings: Settings object or dictionary of settings
        """
        if isinstance(settings, Settings):
            data = settings.to_dict()
        else:
            data = settings
        
        for key, value in data.items():
            self._set_setting(key, value)
        
        # Invalidate cache
        self._settings_cache = None
        logger.info("Settings saved to database")
    
    def update_setting(self, key: str, value: Any) -> None:
        """Update a single setting."""
        self._set_setting(key, value)
        logger.debug(f"Setting updated: {key} = {value}")
    
    # =========================================================================
    # Alert History Operations
    # =========================================================================
    
    def add_alert(self, alert: AlertRecord) -> int:
        """
        Add an alert to history.
        
        Returns:
            ID of the inserted alert
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """INSERT INTO alert_history 
                   (timestamp, level, title, description, metric_name, 
                    current_value, threshold, resolved, resolved_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert.timestamp.isoformat(),
                    alert.level,
                    alert.title,
                    alert.description,
                    alert.metric_name,
                    alert.current_value,
                    alert.threshold,
                    1 if alert.resolved else 0,
                    alert.resolved_at.isoformat() if alert.resolved_at else None,
                )
            )
            self._conn.commit()
            return cursor.lastrowid
    
    def get_recent_alerts(self, limit: int = 50) -> list[AlertRecord]:
        """Get most recent alerts."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT * FROM alert_history ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
        
        alerts = []
        for row in rows:
            alerts.append(AlertRecord(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                level=row["level"],
                title=row["title"],
                description=row["description"] or "",
                metric_name=row["metric_name"] or "",
                current_value=row["current_value"] or "",
                threshold=row["threshold"] or "",
                resolved=bool(row["resolved"]),
                resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            ))
        
        return alerts
    
    def get_alert_stats(self, days: int = 7) -> dict[str, int]:
        """
        Get alert statistics for the last N days.
        
        Returns:
            Dictionary with counts by level
        """
        since = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        since = since.replace(day=since.day - days + 1)
        
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """SELECT level, COUNT(*) as count FROM alert_history 
                   WHERE timestamp >= ? GROUP BY level""",
                (since.isoformat(),)
            )
            rows = cursor.fetchall()
        
        stats = {"info": 0, "warning": 0, "critical": 0, "recovery": 0, "total": 0}
        for row in rows:
            stats[row["level"]] = row["count"]
            stats["total"] += row["count"]
        
        return stats
    
    def resolve_alert(self, alert_id: int) -> None:
        """Mark an alert as resolved."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "UPDATE alert_history SET resolved = 1, resolved_at = ? WHERE id = ?",
                (datetime.now().isoformat(), alert_id)
            )
            self._conn.commit()
    
    def cleanup_old_alerts(self, keep_days: int = 30) -> int:
        """
        Delete alerts older than specified days.
        
        Returns:
            Number of deleted records
        """
        cutoff = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff = cutoff.replace(day=cutoff.day - keep_days)
        
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "DELETE FROM alert_history WHERE timestamp < ?",
                (cutoff.isoformat(),)
            )
            deleted = cursor.rowcount
            self._conn.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old alerts")
        
        return deleted
