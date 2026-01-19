# Unraid Monitor — Development Roadmap

**Last Updated**: January 19, 2026  
**Current Version**: 1.0.2  
**Project Focus**: Homelab-first, Community-driven Discord monitoring for Unraid servers

---

## Vision Statement

Unraid Monitor aims to be **the best monitoring solution for Unraid homelab users** who want:
- Lightweight, out-of-the-box monitoring without complex setup (no Grafana/Prometheus overhead)
- Native Discord integration with rich alerts and weekly reports
- Media stack awareness (Radarr, Sonarr, Jellyfin, etc.)
- Community-driven extensibility through plugins

**Target Audience**: Homelab enthusiasts running Unraid 7.x with media servers and Docker containers  
**Anti-Goals**: Enterprise features (LDAP, HA, commercial SLA), heavy resource usage, complex configuration

---

## Three-Phase Development Plan

### Phase 1: Stabilization & v1.0 Release (2-3 weeks)
**Goal**: Fix critical issues, ship production-ready v1.0, prepare community infrastructure

**Status**: 🟡 In Progress  
**Target Release**: February 2026  
**Unraid Support**: 7.0+ (latest stable: 7.2.3)

#### Critical Fixes
- [x] **APScheduler Dependency** — Migrated to `3.11.2` stable (AsyncIOScheduler 3.x API)
- [x] **Password Hashing** — Implemented `passlib[bcrypt]` with HTTP Basic Auth
- [x] **Pin Dependencies** — All versions pinned with `==` in requirements.txt
- [x] **Docker Non-Root** — Running as `appuser` (UID 1000) with docker group (GID 999)

#### Community Infrastructure
- [x] `CONTRIBUTING.md` — Code style, PR process, code of conduct
- [x] `CHANGELOG.md` — Version tracking with Keep a Changelog format
- [x] `SECURITY.md` — Vulnerability disclosure policy
- [x] `.github/ISSUE_TEMPLATE/` — Bug report, feature request, question templates
- [x] `.github/PULL_REQUEST_TEMPLATE.md` — PR checklist
- [ ] Discord Server — Community support channels (planned)
- [ ] Ko-fi / GitHub Sponsors — Donation setup (planned)

#### Release v1.0.0
- [ ] Create git tag `v1.0.0` with release notes
- [ ] Build multi-arch Docker images (amd64, arm64)
- [ ] Push to Docker Hub: `peterpage2115/unraid-monitor:1.0.0` and `:latest`
- [ ] Announcement posts on r/unraid, r/homelab, r/selfhosted, Discord server
- [ ] Update README badges (version, Docker pulls, Discord invite)

---

### Phase 2: Enhancement (2-3 months)
**Goal**: Improved Web UI, historical data, testing suite, community growth

**Status**: 🔴 Not Started  
**Target Completion**: April-May 2026

#### Web UI Modernization (htmx + Alpine.js + Chart.js)
**Decision**: Use htmx for reactivity instead of full React/Vue — lighter, simpler, sufficient for homelab dashboards

- [ ] Add htmx, Alpine.js, Chart.js to base template (CDN links)
- [ ] Rewrite `dashboard.html` with auto-refresh status cards (`hx-get="/api/status" hx-trigger="every 5s"`)
- [ ] Add partial HTML endpoints: `/api/status`, `/api/containers`, `/api/alerts/recent`
- [ ] Implement dark mode toggle with Alpine.js + localStorage
- [ ] Add minimalist CSS framework (Pico.css or Water.css)
- [ ] Make UI mobile-responsive (media queries)

#### Historical Data Storage
- [ ] Add `MetricHistory` model to `src/database/models.py`
  - Fields: `timestamp, metric_name, value, unit`
  - Index: `(metric_name, timestamp)`
- [ ] Save key metrics after `safe_check()` in system/docker monitors
  - Metrics: CPU %, RAM %, disk usage, container count
- [ ] Implement retention policy: delete data older than 30 days (nightly cleanup job)
- [ ] Add API endpoint: `GET /api/metrics/history?name=cpu_percent&hours=24`
- [ ] Display Chart.js line charts in dashboard (24h CPU/RAM/disk trends)

#### Monitoring Enhancements
- [x] Disk space monitoring (alerts + report)

#### Array Status Monitoring
- [ ] Implement `get_array_status()` in `src/monitors/system.py`
  - Parse `/proc/mdstat` for RAID status (sync, degraded, errors)
  - Read `/sys/block/md*/md/mismatch_cnt` for parity errors
  - Check Unraid-specific paths if available
- [ ] Add alerting for degraded arrays (`AlertSeverity.CRITICAL`)
- [ ] Include "Array Health" section in weekly reports

#### Testing Infrastructure
- [ ] Add pytest dependencies: `pytest`, `pytest-asyncio`, `pytest-cov`
- [ ] Create `tests/unit/` structure for alert logic, config parsing
- [ ] Mock external dependencies (psutil, aiohttp with `aioresponses`)
- [ ] Target: 70%+ code coverage for core logic
- [ ] GitHub Actions: `.github/workflows/tests.yml` runs on push/PR
- [ ] GitHub Actions: `.github/workflows/docker-build.yml` builds multi-arch on tag

#### Multi-Webhook Support
- [ ] Change `DISCORD_WEBHOOK_URL` to `DISCORD_WEBHOOKS` dict in config
  - Keys: `critical`, `warning`, `info`
  - Env vars: `DISCORD_WEBHOOK_CRITICAL`, `DISCORD_WEBHOOK_WARNING`, `DISCORD_WEBHOOK_INFO`
- [ ] Modify `send_notification()` to route by severity
- [ ] Add fallback: if webhook missing for severity, use critical webhook
- [ ] Document multi-webhook setup in README (optional feature)

#### Discord Rate Limiting
- [ ] Implement exponential backoff in `discord_client.py` when response = 429
- [ ] Queue messages and retry after `retry_after` seconds from response headers
- [ ] Add config option: `DISCORD_RATE_LIMIT_RETRY: true` (default)

#### Community Growth
- [ ] Create video tutorial: "Setting up Unraid Monitor in 5 minutes" (YouTube)
- [ ] Write blog post: "Building a Discord monitoring bot for Unraid" (dev.to)
- [ ] Add example configs: `examples/basic-setup/`, `examples/advanced-arr-stack/`
- [ ] Monthly Discord event: "Show & Tell" — users showcase custom setups
- [ ] Enable GitHub Discussions with FAQ and Tips & Tricks categories

---

### Phase 3: Expansion (6-12 months)
**Goal**: Multi-platform notifications, plugin system, advanced features for power users

**Status**: 🔴 Not Started  
**Target Completion**: Q3-Q4 2026

#### Additional Notification Providers
- [ ] **Telegram** — `src/notifications/telegram.py` with Bot API integration
  - Config: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  - Markdown formatting (no embeds in Telegram)
- [ ] **Slack** — `src/notifications/slack.py` with Block Kit formatting
  - Config: `SLACK_WEBHOOK_URL` or `SLACK_BOT_TOKEN + SLACK_CHANNEL`
  - Handle Slack rate limits (1 msg/sec)
- [ ] **Email** — `src/notifications/email.py` with `aiosmtplib`
  - Config: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO`
  - HTML email templates with alert tables
  - Use case: backup channel when Discord/Telegram offline

#### Plugin System
- [ ] Create `src/monitors/plugins/` with auto-discovery loader
- [ ] Dynamic import in `main.py`: scan for `*.py` files, check `BaseMonitor` subclass
- [ ] Config: `plugins.enabled: [plugin_name]` whitelist
- [ ] Plugin template: `examples/plugin-template/` with boilerplate code
- [ ] Plugin registry: GitHub Wiki or dedicated page with community submissions
- [ ] Example plugins:
  - UPS monitoring (Network UPS Tools)
  - Network speed test (speedtest-cli)
  - GPU temperature monitoring (nvidia-smi)
  - ZFS pool status

#### Prometheus Metrics Endpoint
- [ ] Add `prometheus-client>=0.19.0` to optional dependencies
- [ ] Endpoint: `GET /metrics` returning Prometheus text format
- [ ] Expose metrics: `unraid_cpu_percent`, `unraid_memory_percent`, `unraid_disk_used_bytes`, `unraid_container_status`
- [ ] Config: `ENABLE_PROMETHEUS_METRICS: false` (default off)
- [ ] Document Grafana integration in README

#### Advanced Alerting Features
- [ ] **Alert Grouping** — If 5+ alerts in 1 minute, send one summary embed
- [ ] **Silence Rules** — `alerts.silence` in config to ignore specific containers/metrics for X hours
- [ ] **Custom Thresholds** — Per-metric config instead of global: `metrics.cpu.warning: 70, critical: 90`
- [ ] **Alert Dependencies** — Suppress child alerts when host is down

#### Progressive Web App (PWA)
- [ ] Add `manifest.json` for install-to-homescreen capability
- [ ] Implement service worker for offline fallback page
- [ ] Web Push API integration for push notifications (optional)
- [ ] Generate PWA icons (various sizes) and add to static assets
- [ ] Test on mobile devices (iOS Safari, Android Chrome)

#### Internationalization (i18n)
**Decision**: Add in Phase 3 when community grows. Start with English, add translations based on user demand.

- [ ] Install `gettext` or similar i18n library
- [ ] Extract UI strings to translation files: `locales/en/LC_MESSAGES/messages.po`
- [ ] Add language selection in Web UI (dropdown)
- [ ] Priority languages based on community: Polish, German, French, Spanish
- [ ] Alert messages: keep in English for support searchability, translate UI only
- [ ] Config: `LANGUAGE: en` (default)

---

## Success Metrics (KPIs)

### Adoption
- **Docker Hub Pulls**: 1000+ within 3 months of v1.0
- **GitHub Stars**: 500+ within 6 months
- **Discord Members**: 100+ active within 6 months

### Quality
- **Issue Response Time**: <48h for bugs
- **Test Coverage**: 70%+ by end of Phase 2
- **Security**: Zero critical vulnerabilities (automated scanning with Dependabot)

### Community
- **Plugin Submissions**: 3+ community plugins within 1 year
- **Contributors**: 10+ PR contributors within 1 year
- **Documentation**: 90%+ feature documentation completeness

---

## Decision Log

### Why htmx + Alpine.js instead of React/Vue?
**Date**: January 17, 2026  
**Rationale**: 
- Homelab use case doesn't need heavy SPA complexity
- Keeps deployment simple (no build step, single container)
- Sufficient reactivity for status dashboard
- Lightweight (htmx = 14KB, Alpine = 5KB vs React = 130KB+)
- Server-rendered = better for slow homelab hardware

### Why homelab-first, not enterprise?
**Date**: January 17, 2026  
**Rationale**:
- Niche is underserved (Unraid + Discord + media stack)
- Enterprise features (LDAP, HA, audit logs) increase complexity exponentially
- Competitive advantage is simplicity and domain specificity
- Team size = 1 developer, can't compete with enterprise products

### Unraid Version Support: 7.0+
**Date**: January 17, 2026  
**Rationale**:
- Latest stable: 7.2.3 (as of Jan 2026)
- Supporting 6.x would require backcompat testing on old kernel/Docker versions
- Focus on recent versions used by majority of active users
- Document minimum version in README; community can backport if needed

### Monetization: Donation-based (Ko-fi/Sponsors)
**Date**: January 17, 2026  
**Rationale**:
- First project for developer, keep it open/accessible
- Ko-fi/Sponsors = low pressure, optional support
- No freemium/SaaS paywall to avoid support burden
- MIT license encourages adoption and contributions

---

## Out of Scope (Explicitly NOT Planned)

❌ **Enterprise features**: LDAP/OAuth, high availability, commercial SLA  
❌ **Heavy analytics**: Full-featured metrics database (use Prometheus if needed)  
❌ **Native mobile apps**: iOS/Android native (PWA is sufficient)  
❌ **Blockchain/NFT integration**: Stay focused on practical monitoring  
❌ **Windows/macOS support**: Unraid is Linux-only, so is this project  
❌ **GUI configuration editor**: Config via YAML/env is standard for Docker apps  

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Reporting bugs and requesting features
- Code style (Black formatter, type hints, async best practices)
- Pull request process
- Community code of conduct

Join our [Discord server](#) for discussions and support!

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
