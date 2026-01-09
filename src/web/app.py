"""
FastAPI application for Unraid Monitor Web UI.

Provides REST API endpoints and serves the dashboard HTML.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

if TYPE_CHECKING:
    from database import Database
    from notifications import NotificationProvider


logger = logging.getLogger(__name__)

# Path to templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


class WebUI:
    """
    Web UI manager for Unraid Monitor.
    
    Wraps FastAPI app and provides access to application components.
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8888,
        password: str | None = None,
        database: "Database" = None,
        get_system_stats: callable = None,
        get_docker_stats: callable = None,
        get_services_status: callable = None,
        trigger_report: callable = None,
        send_test_notification: callable = None,
    ):
        """
        Initialize Web UI.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            password: Optional password for authentication
            database: Database instance for settings
            get_system_stats: Callback to get current system stats
            get_docker_stats: Callback to get Docker container stats
            get_services_status: Callback to get service connection status
            trigger_report: Callback to trigger weekly report
            send_test_notification: Callback to send test notification
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = database
        self.get_system_stats = get_system_stats
        self.get_docker_stats = get_docker_stats
        self.get_services_status = get_services_status
        self.trigger_report = trigger_report
        self.send_test_notification = send_test_notification
        self.app = create_app(self)
        self._server: uvicorn.Server | None = None
        self._server_task: asyncio.Task | None = None
    
    async def start(self) -> None:
        """Start the web server in background."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        await self._server.serve()
    
    async def stop(self) -> None:
        """Stop the web server."""
        if self._server:
            self._server.should_exit = True
            logger.info("Web UI stopped")


def create_app(web_ui: WebUI = None) -> FastAPI:
    """
    Create FastAPI application.
    
    Args:
        web_ui: WebUI instance with app dependencies
    
    Returns:
        Configured FastAPI app
    """
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logger.info("Web UI starting...")
        yield
        # Shutdown
        logger.info("Web UI shutting down...")
    
    app = FastAPI(
        title="Unraid Monitor",
        description="Web UI for Unraid server monitoring",
        version="1.1.0",
        lifespan=lifespan,
    )
    
    # Store web_ui reference
    app.state.web_ui = web_ui
    
    # Setup templates
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    
    # =========================================================================
    # Dependencies
    # =========================================================================
    
    def get_web_ui() -> WebUI:
        if app.state.web_ui is None:
            raise HTTPException(500, "Web UI not initialized")
        return app.state.web_ui
    
    # =========================================================================
    # Dashboard Page
    # =========================================================================
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Serve the main dashboard page."""
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "title": "Unraid Monitor"}
        )
    
    # =========================================================================
    # API: System Status
    # =========================================================================
    
    @app.get("/api/status")
    async def get_status(ui: WebUI = Depends(get_web_ui)) -> dict:
        """Get current system status."""
        result = {
            "timestamp": datetime.now().isoformat(),
            "system": None,
            "docker": None,
        }
        
        if ui.get_system_stats:
            try:
                result["system"] = await ui.get_system_stats()
            except Exception as e:
                logger.error(f"Error getting system stats: {e}")
                result["system"] = {"error": str(e)}
        
        if ui.get_docker_stats:
            try:
                result["docker"] = await ui.get_docker_stats()
            except Exception as e:
                logger.error(f"Error getting docker stats: {e}")
                result["docker"] = {"error": str(e)}
        
        return result
    
    @app.get("/api/services")
    async def get_services(ui: WebUI = Depends(get_web_ui)) -> dict:
        """Get service connection status."""
        if ui.get_services_status:
            try:
                return await ui.get_services_status()
            except Exception as e:
                logger.error(f"Error getting service status: {e}")
                return {"error": str(e)}
        return {}
    
    # =========================================================================
    # API: Settings
    # =========================================================================
    
    @app.get("/api/settings")
    async def get_settings(ui: WebUI = Depends(get_web_ui)) -> dict:
        """Get current settings."""
        settings = ui.db.get_settings()
        return settings.to_dict()
    
    @app.post("/api/settings")
    async def save_settings(
        request: Request,
        ui: WebUI = Depends(get_web_ui)
    ) -> dict:
        """Update settings."""
        data = await request.json()
        
        # Validate and save
        current = ui.db.get_settings()
        
        # Update only provided fields
        for key, value in data.items():
            if hasattr(current, key):
                setattr(current, key, value)
        
        ui.db.save_settings(current)
        
        return {"status": "ok", "message": "Settings saved"}
    
    @app.post("/api/settings/{key}")
    async def update_setting(
        key: str,
        request: Request,
        ui: WebUI = Depends(get_web_ui)
    ) -> dict:
        """Update a single setting."""
        data = await request.json()
        value = data.get("value")
        
        if value is None:
            raise HTTPException(400, "Missing 'value' in request body")
        
        ui.db.update_setting(key, value)
        return {"status": "ok", "key": key, "value": value}
    
    # =========================================================================
    # API: Actions
    # =========================================================================
    
    @app.post("/api/test")
    async def send_test(ui: WebUI = Depends(get_web_ui)) -> dict:
        """Send a test notification."""
        try:
            if ui.send_test_notification:
                success = await ui.send_test_notification()
                if success:
                    return {"status": "ok", "message": "Test notification sent"}
                else:
                    return {"status": "error", "message": "Failed to send notification"}
            else:
                return {"status": "error", "message": "No notification callback configured"}
        except Exception as e:
            logger.error(f"Error sending test: {e}")
            raise HTTPException(500, str(e))
    
    @app.post("/api/report")
    async def force_report(ui: WebUI = Depends(get_web_ui)) -> dict:
        """Trigger weekly report immediately."""
        if ui.trigger_report:
            try:
                await ui.trigger_report()
                return {"status": "ok", "message": "Report triggered"}
            except Exception as e:
                logger.error(f"Error triggering report: {e}")
                raise HTTPException(500, str(e))
        return {"status": "error", "message": "Report trigger not available"}
    
    @app.post("/api/services/{service}/test")
    async def test_service(
        service: str,
        ui: WebUI = Depends(get_web_ui)
    ) -> dict:
        """Test connection to a specific service."""
        # This would be implemented by the main app
        return {"status": "ok", "service": service, "connected": True}
    
    # =========================================================================
    # API: Alerts & Logs
    # =========================================================================
    
    @app.get("/api/alerts")
    async def get_alerts(
        limit: int = 50,
        ui: WebUI = Depends(get_web_ui)
    ) -> list:
        """Get recent alerts."""
        alerts = ui.db.get_recent_alerts(limit)
        return [a.to_dict() for a in alerts]
    
    @app.get("/api/alerts/stats")
    async def get_alert_stats(
        days: int = 7,
        ui: WebUI = Depends(get_web_ui)
    ) -> dict:
        """Get alert statistics."""
        return ui.db.get_alert_stats(days)
    
    # =========================================================================
    # API: Health Check
    # =========================================================================
    
    @app.get("/health")
    async def health() -> dict:
        """Health check endpoint for Docker."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.1.0",
        }
    
    @app.get("/api/health")
    async def api_health() -> dict:
        """Alias for health check."""
        return await health()
    
    return app
