# Contributing to Unraid Monitor

First off, thank you for considering contributing to Unraid Monitor! 🎉

It's people like you that make Unraid Monitor such a great tool for the homelab community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Features](#suggesting-features)
  - [Contributing Code](#contributing-code)
  - [Improving Documentation](#improving-documentation)
- [Development Setup](#development-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

---

## Code of Conduct

This project and everyone participating in it is governed by our commitment to fostering an open and welcoming environment. By participating, you are expected to uphold this code:

- **Be respectful**: Treat everyone with respect. Disagreements are fine, but keep discussions professional.
- **Be helpful**: We're all learning. Help others where you can.
- **Be patient**: Remember that contributors may be working on this in their spare time.
- **No harassment**: Harassment of any kind will not be tolerated.

If you experience or witness unacceptable behavior, please contact the project maintainers.

---

## How Can I Contribute?

### Reporting Bugs

Found a bug? Help us fix it!

**Before Submitting:**
1. **Check existing issues**: Your bug may already be reported
2. **Try the latest version**: Update to the latest Docker image
3. **Read the docs**: Check if it's a configuration issue

**When Submitting:**
Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml) and include:
- Unraid version (e.g., 7.2.3)
- Docker image version (e.g., 1.0.0)
- Full error message or logs
- Steps to reproduce the issue
- Expected vs. actual behavior
- Relevant parts of `settings.yaml` or environment variables (redact sensitive info!)

**Example of a good bug report:**
> **Title**: "Docker monitor crashes when container has no health check"
> 
> **Description**: When monitoring a container without a health check defined, the monitor crashes with KeyError.
> 
> **Environment**: Unraid 7.2.3, unraid-monitor:1.0.0
> 
> **Steps to Reproduce**:
> 1. Start a container without HEALTHCHECK in Dockerfile
> 2. Wait for docker monitor check cycle
> 3. Check logs: `docker logs unraid-monitor`
> 
> **Logs**:
> ```
> KeyError: 'Health' in docker_monitor.py line 123
> ```

### Suggesting Features

Have an idea to make Unraid Monitor better?

**Before Suggesting:**
1. **Check the roadmap**: See [ROADMAP.md](ROADMAP.md) — it might already be planned!
2. **Search existing issues**: Someone may have suggested it already
3. **Consider the scope**: Does this fit the homelab-first focus?

**When Suggesting:**
Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml) and include:
- **Problem Statement**: What problem does this solve?
- **Proposed Solution**: How should it work?
- **Use Case**: Who would benefit from this?
- **Alternatives**: Have you considered other approaches?

**Example of a good feature request:**
> **Title**: "Add support for NUT (Network UPS Tools) monitoring"
> 
> **Problem**: Homelab users with UPS units want to monitor battery status and power events.
> 
> **Solution**: Create a new monitor in `src/monitors/ups.py` that reads from NUT daemon.
> 
> **Use Case**: Alert when UPS switches to battery, low battery warning, etc.
> 
> **Alternatives**: Could use a plugin system (Phase 3 roadmap), but built-in support would be better UX.

### Contributing Code

Ready to write code? Awesome! 

**First-Time Contributors:**
Look for issues labeled `good first issue` — these are intentionally scoped for newcomers.

**Process:**
1. **Fork the repository**: https://github.com/peterpage2115/unraid-monitor
2. **Create a feature branch**: `git checkout -b feature/awesome-feature`
3. **Make your changes** (see [Code Style Guidelines](#code-style-guidelines))
4. **Test your changes** (see [Development Setup](#development-setup))
5. **Commit with clear messages**: `git commit -m "Add UPS monitoring support"`
6. **Push to your fork**: `git push origin feature/awesome-feature`
7. **Open a Pull Request** (see [Pull Request Process](#pull-request-process))

**Types of Contributions:**
- 🐛 **Bug fixes**: Fix existing issues
- ✨ **New features**: Add monitors, services, notification providers
- 🧪 **Tests**: Improve test coverage
- 📚 **Documentation**: Improve README, add examples
- 🎨 **UI improvements**: Enhance web dashboard
- 🔌 **Plugins**: Community-contributed monitors (Phase 3)

### Improving Documentation

Documentation is as important as code!

**Where to Contribute:**
- **README.md**: Installation, configuration, usage examples
- **ROADMAP.md**: Add context or clarify planned features
- **Code comments**: Docstrings, inline comments for complex logic
- **Examples**: Add `examples/` configs for specific use cases
- **Wiki/Discussions**: Answer common questions

**Documentation Standards:**
- Use clear, concise language
- Include code examples where helpful
- Keep formatting consistent (Markdown)
- Test commands/configs before documenting them

---

## Development Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git
- (Optional) VS Code with Python extensions

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/peterpage2115/unraid-monitor.git
   cd unraid-monitor
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development tools
   ```

4. **Set up configuration**:
   ```bash
   cp config/settings.yaml config/settings.local.yaml
   # Edit settings.local.yaml with your test values
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
   ```

5. **Run tests**:
   ```bash
   # Integration tests (requires Docker socket)
   python src/test_bot.py webhook
   python src/test_bot.py system
   
   # Unit tests (Phase 2+)
   pytest tests/
   ```

6. **Run locally**:
   ```bash
   # Windows
   set PYTHONPATH=src
   python src/main.py
   
   # Linux/Mac
   PYTHONPATH=src python src/main.py
   ```

### Docker Development

```bash
# Build image
docker build -t unraid-monitor:dev .

# Run with local changes mounted
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./src:/app/src \
  -e DISCORD_WEBHOOK_URL="https://..." \
  unraid-monitor:dev
```

---

## Code Style Guidelines

### Python Style

**Formatter**: [Black](https://github.com/psf/black) (line length: 100)
```bash
black src/
```

**Linter**: [Flake8](https://flake8.pycqa.org/) (E501 ignored due to Black)
```bash
flake8 src/ --max-line-length=100
```

**Type Checker**: [mypy](https://mypy-lang.org/)
```bash
mypy src/
```

### Code Conventions

1. **Type Hints**: Required for all function signatures
   ```python
   async def check_system(threshold: float) -> dict[str, float]:
       ...
   ```

2. **Async-First**: Use `async`/`await` for all I/O operations
   ```python
   # ✅ Good
   async def fetch_data(url: str) -> dict:
       async with aiohttp.ClientSession() as session:
           async with session.get(url) as response:
               return await response.json()
   
   # ❌ Bad (blocking)
   def fetch_data(url: str) -> dict:
       response = requests.get(url)
       return response.json()
   ```

3. **Docstrings**: Use Google-style docstrings
   ```python
   async def process_alert(alert: Alert, threshold: float) -> bool:
       """Process an alert and determine if notification should be sent.
       
       Args:
           alert: The alert object to process
           threshold: Threshold value for comparison
           
       Returns:
           True if notification sent, False otherwise
           
       Raises:
           ValueError: If threshold is negative
       """
       ...
   ```

4. **Error Handling**: Always handle exceptions gracefully
   ```python
   try:
       result = await risky_operation()
   except SpecificException as e:
       logger.error(f"Operation failed: {e}")
       return None
   ```

5. **Logging**: Use structured logging with appropriate levels
   ```python
   logger.debug("Checking system metrics...")  # Verbose details
   logger.info("System check completed")        # Normal operations
   logger.warning("CPU usage high: 85%")        # Warnings
   logger.error("Failed to read disk stats")    # Errors
   logger.critical("Alert manager crashed")     # Critical failures
   ```

6. **Resource Cleanup**: Always close sessions/connections
   ```python
   # ✅ Good
   async with aiohttp.ClientSession() as session:
       # Use session
   
   # ❌ Bad
   session = aiohttp.ClientSession()
   # ... forgot to close
   ```

### File Organization

```python
# Standard library imports
import asyncio
from typing import Optional

# Third-party imports
import aiohttp
from pydantic import BaseModel

# Local imports
from monitors.base import BaseMonitor
from alerts.models import Alert
```

---

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines (run `black src/`)
- [ ] Type hints are present (run `mypy src/`)
- [ ] Tests pass (run `python src/test_bot.py` or `pytest`)
- [ ] Documentation updated (README, docstrings, comments)
- [ ] CHANGELOG.md entry added under `[Unreleased]`
- [ ] No sensitive data committed (API keys, passwords, personal info)

### PR Template Checklist

When you open a PR, you'll see a template with checklist. Fill it out completely!

**Required Information:**
- **Description**: What does this PR do?
- **Issue Link**: Fixes #123 (or N/A)
- **Type**: Bug fix / Feature / Documentation / Refactor
- **Testing**: How did you test this?
- **Screenshots**: If UI changes, include before/after

### Review Process

1. **Automated Checks**: CI runs tests and linting (once set up in Phase 2)
2. **Maintainer Review**: A maintainer will review within 48 hours
3. **Discussion**: Address any feedback or questions
4. **Approval**: Once approved, maintainer will merge
5. **Release**: Changes will be included in next version

### After Merge

- Your contribution will be acknowledged in release notes
- You'll be added to CONTRIBUTORS.md (if not already)
- Consider joining our Discord to stay involved!

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions, ideas, show-and-tell
- **Discord Server**: Real-time chat, support, development discussion
  - `#support`: Get help using Unraid Monitor
  - `#development`: Discuss code, architecture, PRs
  - `#showcase`: Share your setup and dashboards
  - `#off-topic`: General homelab chat

### Recognition

We value all contributions! Contributors will be recognized through:
- Mention in release notes
- CONTRIBUTORS.md file
- GitHub "Contributors" section
- Optional: Ko-fi supporters list (if you donate)

---

## Questions?

**Don't see your question answered here?**
- Check the [FAQ in GitHub Discussions](https://github.com/peterpage2115/unraid-monitor/discussions)
- Ask in Discord `#support` channel (link TBD)
- Open a [Question issue](.github/ISSUE_TEMPLATE/question.yml)

**Need help getting started?**
Look for issues tagged `good first issue` or ask in Discord `#development`!

---

## License

By contributing to Unraid Monitor, you agree that your contributions will be licensed under the MIT License.

---

Thank you for making Unraid Monitor better! 🚀
