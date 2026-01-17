# Unraid Monitor — Implementation Tracking

**Last Updated**: January 17, 2026  
**Current Phase**: Phase 1 — Stabilization & v1.0

---

## Phase 1: Stabilization & v1.0 Release

### 🔴 Critical Fixes (Blocking v1.0)

- [x] **APScheduler Dependency Issue**
  - Files: `requirements.txt`, `src/main.py`
  - Action: Changed `apscheduler>=4.0.0a5` to `apscheduler==3.11.2` (stable)
  - Refactored: Migrated from AsyncScheduler (4.x) to AsyncIOScheduler (3.x API)
  - Test: Run `python src/test_bot.py` and verify scheduled tasks work
  - **Status**: ✅ COMPLETED (Jan 17, 2026)

- [x] **Web UI Password Security**
  - Files: `requirements.txt`, `src/web/app.py`, `README.md`, `generate_password.py` (new)
  - Actions:
    1. Added `passlib[bcrypt]==1.7.4` to requirements
    2. Implemented HTTP Basic Auth with bcrypt password verification
    3. Created `generate_password.py` script for generating password hashes
    4. Updated README with password setup instructions
    5. Protected all Web UI and API endpoints with authentication
  - **Status**: ✅ COMPLETED (Jan 17, 2026)

- [x] **Pin All Dependencies**
  - Files: `requirements.txt`, `requirements-dev.txt` (new)
  - Actions:
    1. Replaced all `>=` with `==` for production dependencies
    2. Created `requirements-dev.txt` with: `pytest==8.3.0`, `pytest-asyncio==0.24.0`, `pytest-cov==6.0.0`, `black==24.10.0`, `mypy==1.13.0`
    3. Documented tested versions in README
  - **Status**: ✅ COMPLETED (Jan 17, 2026)

- [x] **Docker Non-Root Execution**
  - Files: `Dockerfile`, `README.md`, `docker-compose.yml`
  - Actions:
    1. Added docker group (GID 999) to container
    2. Changed container to run as `appuser` (UID 1000) with docker group membership
    3. Updated Dockerfile to `USER appuser` instead of root
    4. Copied `generate_password.py` into container image
    5. Updated README with Docker socket permission notes
  - **Status**: ✅ COMPLETED (Jan 17, 2026)

### 📄 Community Infrastructure

- [x] **CONTRIBUTING.md**
  - Content:
    - How to report bugs (issue template)
    - Feature request process
    - Code style: Black formatter, type hints required, async-first
    - PR checklist: tests pass, docs updated, CHANGELOG entry
    - Community code of conduct
  - **Status**: 🔴 Not Started

- [ ] **CHANGELOG.md**
  - Format: Keep a Changelog (https://keepachangelog.com/)
  - Sections: `[Unreleased]`, `[1.0.0] - 2026-02-XX`
  - Categories: Added, Changed, Deprecated, Removed, Fixed, Security
  - **Status**: 🔴 Not Started

- [ ] **SECURITY.md**
  - Content:
    - Supported versions (1.x.x)
    - How to report vulnerabilities (email or private GitHub issue)
    - Response timeline (48h acknowledgment, 7d fix target)
  - **Status**: 🔴 Not Started

- [ ] **GitHub Issue Templates**
  - Files: `.github/ISSUE_TEMPLATE/bug_report.yml`, `feature_request.yml`, `question.yml`
  - Content: Structured forms with required fields (environment, steps to reproduce, logs)
  - **Status**: 🔴 Not Started

- [ ] **GitHub Pull Request Template**
  - File: `.github/PULL_REQUEST_TEMPLATE.md`
  - Content: Checklist (tests added, docs updated, CHANGELOG entry, code formatted)
  - **Status**: 🔴 Not Started

- [ ] **Discord Server Setup**
  - Channels: #announcements, #support, #development, #showcase, #off-topic
  - Roles: Admin, Contributor, Helper, Member
  - Welcome message with links to README and CONTRIBUTING
  - Integration: GitHub webhook for new releases
  - **Status**: 🔴 Not Started

- [ ] **Ko-fi / GitHub Sponsors**
  - Create Ko-fi account OR enable GitHub Sponsors
  - Add badge to README: `[![Support on Ko-fi](https://img.shields.io/badge/Support%20on-Ko--fi-FF5E5B?logo=ko-fi)](https://ko-fi.com/yourusername)`
  - Add `.github/FUNDING.yml` for GitHub Sponsors button
  - **Status**: 🔴 Not Started

### 🚀 Release v1.0.0

- [ ] **Version Tagging**
  - Action: `git tag -a v1.0.0 -m "First stable release"`
  - Update version constant in `src/main.py` or `src/__init__.py`
  - **Status**: 🔴 Not Started

- [ ] **Multi-Arch Docker Build**
  - Command: `docker buildx build --platform linux/amd64,linux/arm64 -t yourusername/unraid-monitor:1.0.0 -t yourusername/unraid-monitor:latest --push .`
  - Test on: Raspberry Pi (arm64), Intel NUC (amd64)
  - **Status**: 🔴 Not Started

- [ ] **Docker Hub Publishing**
  - Tags: `1.0.0`, `1.0`, `1`, `latest`
  - Update Docker Hub description with README content
  - Add links to GitHub, Discord, Ko-fi
  - **Status**: 🔴 Not Started

- [ ] **Announcement Posts**
  - Platforms:
    - r/unraid (title: "Unraid Monitor v1.0 — Discord-native monitoring for your homelab")
    - r/homelab (focus on lightweight monitoring)
    - r/selfhosted (emphasize open-source, MIT license)
    - Discord server announcement
  - Content: Screenshot of dashboard, key features, installation one-liner
  - **Status**: 🔴 Not Started

- [ ] **README Badge Updates**
  - Add: Version badge, Docker Pulls, Discord invite, Ko-fi
  - Example: `[![Docker Pulls](https://img.shields.io/docker/pulls/yourusername/unraid-monitor)](https://hub.docker.com/r/yourusername/unraid-monitor)`
  - **Status**: 🔴 Not Started

---

## Phase 2: Enhancement (Future)

### 🎨 Web UI Modernization
- [ ] Add htmx, Alpine.js, Chart.js to templates
- [ ] Rewrite dashboard.html with auto-refresh
- [ ] Add dark mode toggle
- [ ] Implement mobile-responsive design
- [ ] Add minimalist CSS framework

### 📊 Historical Data
- [ ] Add `MetricHistory` database model
- [ ] Save metrics after monitor checks
- [ ] Implement 30-day retention cleanup job
- [ ] Add `/api/metrics/history` endpoint
- [ ] Display Chart.js graphs in dashboard

### 🧪 Testing Suite
- [ ] Set up pytest infrastructure
- [ ] Write unit tests for alerts manager
- [ ] Mock external dependencies (psutil, aiohttp)
- [ ] Add GitHub Actions CI workflow
- [ ] Achieve 70%+ code coverage

### 🔔 Multi-Webhook Support
- [ ] Refactor config to support multiple webhooks
- [ ] Route alerts by severity level
- [ ] Add fallback webhook logic
- [ ] Document multi-webhook setup

### 🌐 Community Growth
- [ ] Create YouTube tutorial video
- [ ] Write dev.to blog post
- [ ] Add example configurations
- [ ] Host monthly "Show & Tell" events
- [ ] Enable GitHub Discussions

---

## Phase 3: Expansion (Future)

### 📱 Additional Notification Providers
- [ ] Telegram integration
- [ ] Slack integration
- [ ] Email notification provider

### 🔌 Plugin System
- [ ] Implement plugin auto-discovery
- [ ] Create plugin template
- [ ] Build plugin registry
- [ ] Example plugins (UPS, GPU, network)

### 📈 Prometheus Metrics
- [ ] Add `/metrics` endpoint
- [ ] Expose standard metrics
- [ ] Document Grafana integration

### 🌍 Internationalization
- [ ] Install i18n library
- [ ] Extract translatable strings
- [ ] Add language selection in UI
- [ ] Community translations (Polish, German, French, Spanish)

### 🚀 Progressive Web App
- [ ] Add manifest.json
- [ ] Implement service worker
- [ ] Web Push notifications
- [ ] Mobile testing

---

## Notes & Decisions

### APScheduler Alpha Version
**Issue**: Currently using `apscheduler>=4.0.0a5` which is unstable  
**Options**:
1. Downgrade to `3.10.4` stable (recommended for v1.0)
2. Keep alpha but document risks + lock to specific alpha version
**Decision Needed**: Choose option #1 for production readiness

### Password Hashing Strategy
**Current**: Plain-text comparison in `src/web/app.py`  
**Fix**: Use `passlib[bcrypt]` with salted hashes  
**Migration Path**: First boot generates hash from plain password, saves to file, removes plain env var  
**Alternative**: Require users to pre-generate hash (more secure, less user-friendly)  
**Decision**: Use pre-generated hash (better security practice)

### Unraid Version Support
**Minimum Version**: 7.0  
**Latest Tested**: 7.2.3  
**Rationale**: Focus on recent versions, avoid backcompat complexity for 6.x  
**Documented In**: README "Requirements" section

### i18n Priority Languages
**Primary**: English (default)  
**Secondary** (based on community demand):
1. Polish (developer native language)
2. German (large Unraid community)
3. French
4. Spanish
**Strategy**: Wait for community requests before investing in translation infrastructure

---

## Quick Reference

### Files to Create
- [ ] `CHANGELOG.md`
- [ ] `CONTRIBUTING.md`
- [ ] `SECURITY.md`
- [ ] `.github/ISSUE_TEMPLATE/bug_report.yml`
- [ ] `.github/ISSUE_TEMPLATE/feature_request.yml`
- [ ] `.github/ISSUE_TEMPLATE/question.yml`
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] `.github/FUNDING.yml`
- [ ] `requirements-dev.txt`
- [ ] `examples/basic-setup/docker-compose.yml`
- [ ] `examples/advanced-arr-stack/docker-compose.yml`

### Files to Modify (Phase 1)
- [ ] `requirements.txt` (pin versions, add passlib)
- [ ] `Dockerfile` (non-root user)
- [ ] `src/web/app.py` (password hashing)
- [ ] `README.md` (badges, Discord link, password setup, version support)
- [ ] `docker-compose.yml` (update examples for v1.0)

---

**Next Action**: Start with APScheduler fix — read `requirements.txt` and current usage, decide on stable version downgrade.
