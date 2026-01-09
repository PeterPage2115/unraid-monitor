# Copilot / AI Agent Instructions for Unraid Monitor

This file gives concise, actionable guidance for AI coding agents to be productive in this repository.

## Quick context (big picture)
- What it is: a Dockerized Discord monitoring bot for Unraid servers that collects host metrics, Docker/container status, and optional media-service stats, and posts alerts/reports to a Discord webhook.
- Main runtime: Async Python using asyncio + aiohttp; scheduled tasks via APScheduler (AsyncScheduler).
- Entry point: `src/main.py` (class `UnraidMonitor`) — initializes `DiscordClient`, `AlertManager`, monitors, and service clients.

## Key directories & files
- `src/` - main source code
  - `src/main.py` — application lifecycle and scheduler
  - `src/config.py` — loading & validation of configuration (YAML + env vars; env vars take precedence)
  - `src/discord_client.py` — webhook client, embed builders, formatting helpers
  - `src/alerts/` — alert state logic and persistence (`alerts.manager.AlertManager`)
  - `src/monitors/` — monitors (system, docker) and `services/` for external APIs (Radarr, Sonarr, Immich, Jellyfin, qBittorrent)
  - `src/reports/weekly.py` — report composition and sending
  - `src/test_bot.py` — integration smoke tests & helpers (use for local checks)
- `config/settings.yaml` — default behavior / thresholds (merged with DEFAULT_CONFIG in code)
- `Dockerfile`, `docker-compose.yml` — container / runtime configuration

## Developer workflows & commands (explicit)
- Run locally (development): set PYTHONPATH so `src` is importable and run code directly:
  - Windows: `set PYTHONPATH=src` then `python src/test_bot.py --help`
  - In-container: `docker exec -it unraid-monitor python test_bot.py --help`
- Run main application in Docker: `docker-compose up -d` (see `docker-compose.yml` volumes and env examples in README)
- Smoke tests: use `src/test_bot.py` to test webhook, alerts, system, docker (note: Docker tests require Docker socket; system metrics require host mounts)

## Configuration & runtime notes (critical)
- Config precedence: DEFAULT_CONFIG <- `config/settings.yaml` <- environment variables (env wins).
- Required env: `DISCORD_WEBHOOK_URL` (validated by `config.Config.validate()`); service API keys (RADARR_API_KEY, SONARR_API_KEY, etc.) are optional.
- Persistence: alert states are persisted to `/app/data/alert_state.json` (see `AlertManager` constructor and `_save_state()`), ensure the volume is writable if running in container.
- Host metrics from inside container: `SystemMonitor` expects host mounts `/proc:/host/proc` and `/sys:/host/sys` and sets `HOST_PROC`/`HOST_SYS` env **before** importing psutil — do not move or lazily import psutil without preserving this requirement.
- Docker monitoring requires the Docker socket mounted (`/var/run/docker.sock`) and the `docker` Python SDK; tests will fail on Windows or when socket is missing.

## Conventions & patterns to follow (project-specific)
- Async-first: All network / IO uses `async` and `aiohttp`; new service clients should subclass `monitors.services.base.BaseServiceClient` and use `get()` / `post()` helpers and `close()` sessions.
- Monitors implement `BaseMonitor`: required methods `name`, `async check()` and `async get_report_data()`; use `safe_check()` when scheduled (it logs errors and keeps last data in `_last_check_data`).
- Alert flow: create `alerts.models.MetricReading` and call `alert_manager.process_reading(reading)`; rely on `AlertManager` for cooldown, hysteresis, escalation, and persistence — don't reimplement cooldown logic in monitors.
- Config objects: add new config options to `DEFAULT_CONFIG` in `src/config.py` and consume via dataclasses; environment variable names should match existing patterns (e.g., `RADARR_URL`, `RADARR_API_KEY`).
- Discord embeds: use helpers in `src/discord_client.py` (`build_embed`, `build_alert_embed`) to preserve consistent formatting and rate-limit behavior.

## Adding a new monitor or service — concrete example
- New monitor: create `src/monitors/<thing>.py` subclassing `BaseMonitor`. Implement `name`, `check()` (process readings with AlertManager), and `get_report_data()` used by weekly reports.
- New service client: subclass `BaseServiceClient`, override `_get_headers()` if needed, implement `get_stats_for_report()` and `health_check()`; close sessions with `await client.close()` when done.

## Testing & debug tips
- Use `src/test_bot.py` to run localized integration tests: `python src/test_bot.py webhook|system|docker|services|report`.
- For debugging async code, run functions directly in an `asyncio` session or set logging to DEBUG (`config.logging.level` in `settings.yaml` or set env `LOGGING_LEVEL=DEBUG`).
- When adding HTTP calls, follow existing error handling: return `None` on non-200 statuses, log 401/404 specially to make misconfiguration obvious.

## Known limitations & environment caveats
- Some features are expected to fail on Windows (Docker socket access, psutil host mounts). The code handles failures gracefully but tests may show expected errors.
- Rate limiting: Discord webhook returns 429 — `DiscordClient.send_message()` logs and does not automatically retry; maintain idempotency for batch sends.

## Useful references (files to inspect)
- `src/main.py` — scheduler and lifecycle
- `src/config.py` — config loading & validation (DEFAULT_CONFIG) — shows thresholds and defaults
- `src/discord_client.py` — embed formats, helpers (`format_bytes`, progress bars)
- `src/alerts/manager.py` — alerting logic (cooldown, recovery, persistence)
- `src/monitors/base.py` — monitor contract
- `src/monitors/*` and `src/monitors/services/*` — examples for implementation patterns
- `src/test_bot.py` — local/in-container integration tests and usage examples

---

If anything here is unclear or you'd like more detailed snippets (e.g., unit-test scaffolding or a code example for adding a specific monitor), say which area and I'll expand the instructions. ✅
