# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0.4] - 2026-01-19

### Fixed
- Web UI Services panel now correctly parses API response object (was expecting array)
- Web UI Memory display now shows actual used/total values (was showing 0)
- Web UI Uptime now displays correctly (added uptime_seconds to API response)
- Services now show proper status with better formatting

---

## [1.0.3] - 2026-01-19

### Added
- Disk monitoring configuration (include/exclude mounts, ignore filesystem types)
- Web UI Storage card showing all monitored disks with progress bars
- Documentation for Unraid disk mount structure

### Changed
- Disk alerts now respect configurable mount include/exclude lists
- Disk monitoring defaults now target Unraid mounts (/mnt/user, /mnt/cache, /mnt/disk*)
- Web UI now displays disk list dynamically instead of single storage metric
- README updated with disk monitoring requirements and /mnt mount explanation

### Fixed
- Web UI authentication now properly handles missing password configuration
- HTTPBasic auth set to auto_error=False for optional authentication

---

## [1.0.2] - 2026-01-19

### Changed
- Centralized application version in `src/__init__.py`
- All modules now import `__version__` from the package root
- Updated Dockerfile LABEL version to 1.0.2

### Removed
- Internal-only docs from repo tracking (TODO.md, SECURITY_AUDIT.md, copilot-instructions)

---

## [1.0.1] - 2026-01-18

### Security
- Updated aiohttp from 3.11.11 to 3.13.3 to address security vulnerabilities:
  - Fixed proxy authorization headers not being passed when reusing connections (407 errors)
  - Fixed multipart reading failing when encountering empty body parts

### Changed
- Updated jinja2 from 3.1.5 to 3.1.6 (patch update)
- Updated PyYAML from 6.0.2 to 6.0.3 (patch update)
- Updated python-multipart from 0.0.20 to 0.0.21 (patch update)
- Updated tzlocal from 5.2 to 5.3.1 (minor update)
- Updated SQLAlchemy from 2.0.36 to 2.0.45 (patch updates)

---

## [1.0.0] - 2026-01-18

### Added
- Project roadmap documentation (ROADMAP.md)
- Implementation tracking document (TODO.md)
- Contributing guidelines (CONTRIBUTING.md)
- Security policy (SECURITY.md)
- GitHub issue and PR templates (.github/ISSUE_TEMPLATE/)
- GitHub pull request template (.github/PULL_REQUEST_TEMPLATE.md)
- GitHub funding configuration (.github/FUNDING.yml)
- Password hashing for Web UI with bcrypt (passlib + bcrypt)
- HTTP Basic Authentication for all Web UI endpoints (except /health)
- Password hash generator script (generate_password.py)
- Development dependencies file (requirements-dev.txt with pytest, black, mypy)

### Changed
- **BREAKING**: APScheduler downgraded from 4.0.0a5 (unstable) to 3.11.2 (stable)
  - Changed from `AsyncScheduler` (4.x) to `AsyncIOScheduler` (3.x)
  - Scheduler API updated: removed `async with` context manager, added explicit `start()` + `shutdown()`
  - Keep-alive loop pattern: `while self._running: await asyncio.sleep(1)`
  - Internal change only - no configuration impact for users
- All dependencies pinned to exact versions (`==`) for reproducible builds
- bcrypt pinned to 4.2.1 (compatibility with passlib 1.7.4, avoids 5.x incompatibility)
- Updated Docker Hub username: `yourusername` → `peterpage2115`
- Docker container user management: uses Alpine's `ping` group (GID 999) for docker.sock access
- Web UI now requires authentication when `WEB_PASSWORD` environment variable is set
- docker-compose.yml: added `group_add: ["999"]` for proper Docker socket permissions

### Fixed
- **CRITICAL**: Signal handler no longer calls `loop.stop()` - allows graceful shutdown to complete
  - Previously: SIGTERM/SIGINT would abort cleanup, leaving scheduler/HTTP sessions open
  - Now: `monitor.stop()` completes properly, closes all resources, sends shutdown notification
- Scheduler stability issues by moving to stable APScheduler 3.11.2 release
- Docker group GID conflict in Alpine (attempted to create GID 999, but `ping` group exists)
- Password hashing compatibility issue (passlib 1.7.4 incompatible with bcrypt 5.x)
- Dockerfile user creation flow to work with existing Alpine groups

### Security
- Web UI password comparison now uses bcrypt hashing ($2b$12$...) instead of plain-text
- All API endpoints protected by HTTP Basic Auth when password is configured
- Health endpoints (/health, /api/health) remain unauthenticated for Docker HEALTHCHECK
- Container runs as non-root user (appuser, UID 1000) with minimal group permissions

---

## [1.0.0] - TBD (Target: February 2026)

### Added
- Initial stable release of Unraid Monitor
- Discord webhook integration with rich embeds
- System monitoring (CPU, RAM, disk, temperatures)
- Docker container monitoring (status, health checks, restarts)
- Alert manager with cooldown, escalation, and recovery detection
- Service integrations: Radarr, Sonarr, Immich, Jellyfin, qBittorrent
- Weekly Discord reports with comprehensive statistics
- Basic web dashboard with real-time status
- SQLite persistence for alerts and settings
- Comprehensive configuration via YAML and environment variables
- Docker deployment with multi-stage builds
- Integration test suite (test_bot.py)
- Complete documentation (README, copilot-instructions)

### Security
- Password hashing for web UI authentication (bcrypt)
- Secure environment variable handling for API keys

### Fixed
- APScheduler dependency stabilized (using stable 3.10.x branch)
- Docker container runs as non-root user with docker group membership
- Pinned dependency versions for reproducible builds

---

## Version History

### Pre-1.0 Development (2025-2026)
- Initial development and architecture design
- Core monitoring features implementation
- Discord integration and alerting system
- Service client implementations
- Web UI foundation with FastAPI
- Database layer with SQLAlchemy
- Testing infrastructure

---

## Upcoming Releases (Planned)

### [1.1.0] - Q2 2026 (Phase 2 Start)
- Enhanced Web UI with htmx and Alpine.js
- Historical data storage and visualization
- Array status monitoring for Unraid RAID arrays
- Multi-webhook support (route alerts by severity)
- Discord rate limiting with exponential backoff
- Pytest unit test suite with 70%+ coverage
- GitHub Actions CI/CD pipeline

### [1.2.0] - Q3 2026
- Telegram notification provider
- Plugin system for community-contributed monitors
- Improved mobile-responsive design
- Additional example configurations

### [2.0.0] - Q4 2026 (Phase 3)
- Slack and Email notification providers
- Prometheus metrics endpoint for Grafana integration
- Advanced alerting features (grouping, silence rules, dependencies)
- Progressive Web App (PWA) capabilities
- Internationalization support (i18n)
- Community plugin marketplace

---

## Notes

### Versioning Strategy
- **Major (X.0.0)**: Breaking changes, architecture changes, new major features
- **Minor (x.Y.0)**: New features, enhancements, non-breaking changes
- **Patch (x.y.Z)**: Bug fixes, security patches, documentation updates

### Support Policy
- **Latest version**: Full support (bug fixes, features, security updates)
- **Previous minor**: Security updates only for 6 months
- **Older versions**: No official support (community assistance available)

### Breaking Changes Policy
Breaking changes will:
1. Be announced in release notes and Discord server
2. Include migration guide in documentation
3. Provide deprecation warnings in previous minor version when possible
4. Be avoided in patch releases

---

## Links

- **Repository**: https://github.com/peterpage2115/unraid-monitor
- **Docker Hub**: https://hub.docker.com/r/peterpage2115/unraid-monitor
- **Discord**: [Invite link - TBD]
- **Issues**: https://github.com/peterpage2115/unraid-monitor/issues
- **Discussions**: https://github.com/peterpage2115/unraid-monitor/discussions

---

[Unreleased]: https://github.com/peterpage2115/unraid-monitor/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/peterpage2115/unraid-monitor/releases/tag/v1.0.2
[1.0.0]: https://github.com/peterpage2115/unraid-monitor/releases/tag/v1.0.0
