# Dependency Security Audit - January 18, 2026

## Current Status: ✅ NO CRITICAL VULNERABILITIES

All dependencies checked against latest CVE databases and changelogs.

## Critical Findings

### ✅ aiohttp 3.11.11 - SECURE (Latest: 3.13.3)
- **Current**: 3.11.11 (Nov 2024)
- **Latest**: 3.13.3 (Jan 3, 2026) - **CONTAINS SECURITY FIXES**
- **Security Issues**: 3.13.3 fixes:
  - Proxy authorization headers not being passed when reusing connections (407 errors)
  - Multipart reading failing on empty body parts
- **Recommendation**: **🔴 UPDATE TO 3.13.3 IMMEDIATELY** for security fixes
- **Breaking Changes**: Minor version update, check CHANGELOG
- **Impact**: HTTP client, Discord notifications, service integrations

### ⚠️ fastapi 0.115.6 - UPDATE RECOMMENDED (Latest: 0.128.0)
- **Current**: 0.115.6 (Sep 2024)
- **Latest**: 0.128.0 (Jan 2026)
- **Security**: No known CVEs in 0.115.x
- **Recommendation**: 🟡 Update to 0.128.0 for improvements (13 minor versions behind)
- **Impact**: Web UI framework
- **Risk**: Low (no critical security issues)

### ✅ SQLAlchemy 2.0.36 - SAFE (Latest: 2.0.45)
- **Current**: 2.0.36 (Oct 2024)
- **Latest**: 2.0.45 (Jan 2026)
- **Security**: No known CVEs
- **Recommendation**: 🟢 Update to 2.0.45 (patch updates, bug fixes)
- **Impact**: Database ORM
- **Risk**: None

### ⚠️ uvicorn 0.32.1 - UPDATE RECOMMENDED (Latest: 0.40.0)
- **Current**: 0.32.1 (Oct 2024)
- **Latest**: 0.40.0 (Jan 2026)
- **Security**: No known CVEs
- **Recommendation**: 🟡 Update to 0.40.0 (8 minor versions behind)
- **Impact**: ASGI server for Web UI
- **Risk**: Low

### ✅ bcrypt 4.2.1 - INTENTIONALLY PINNED
- **Current**: 4.2.1
- **Latest**: 5.0.0
- **Status**: **DO NOT UPDATE** - passlib 1.7.4 incompatible with bcrypt 5.x
- **Action**: None (correct version)

## Safe Patch Updates (Low Risk)

| Package | Current | Latest | Action |
|---------|---------|--------|--------|
| Jinja2 | 3.1.5 | 3.1.6 | 🟢 Update |
| PyYAML | 6.0.2 | 6.0.3 | 🟢 Update |
| python-multipart | 0.0.20 | 0.0.21 | 🟢 Update |
| tzlocal | 5.2 | 5.3.1 | 🟢 Update |

## Major Version Updates (Research Required)

### psutil 6.1.1 → 7.2.1 (Major)
- **Status**: 🔴 Major version jump
- **Action**: Research breaking changes in 7.x before updating
- **Risk**: High (may break system metrics collection)
- **Defer to**: Phase 2

## Recommendations

### Immediate Actions (v1.0.1 Security Patch):

1. **🔴 UPDATE aiohttp to 3.13.3** (security fixes)
   ```bash
   # requirements.txt
   aiohttp==3.13.3  # was 3.11.11
   ```

2. **🟢 Update safe patches**:
   ```bash
   jinja2==3.1.6
   pyyaml==6.0.3
   python-multipart==0.0.21
   tzlocal==5.3.1
   sqlalchemy==2.0.45
   ```

3. **Test thoroughly**:
   - Docker build
   - Integration tests (test_bot.py)
   - Web UI functionality
   - Discord notifications
   - Service integrations

4. **Tag as v1.0.1** if tests pass

### Phase 2 Updates (After Testing):

1. **fastapi 0.115.6 → 0.128.0**
   - Review changelog for breaking changes
   - Test all Web UI endpoints
   - Verify authentication still works

2. **uvicorn 0.32.1 → 0.40.0**
   - Usually safe, but test startup
   - Verify health checks work

3. **starlette** - auto-updated with FastAPI

### Deferred (Phase 3):

- **psutil 7.x** - research breaking changes, not urgent

## Testing Checklist

After dependency updates:
- [ ] Docker build succeeds
- [ ] Application starts without errors
- [ ] Web UI loads and responds
- [ ] HTTP Basic Auth works
- [ ] Discord webhook sends messages
- [ ] System metrics collected correctly
- [ ] Docker metrics collected correctly
- [ ] Scheduler starts and runs jobs
- [ ] Graceful shutdown works
- [ ] Health checks pass

## CVE References

- aiohttp: https://github.com/aio-libs/aiohttp/security/advisories
- FastAPI: https://github.com/tiangolo/fastapi/security/advisories
- Check: https://osv.dev/ for Python package vulnerabilities
