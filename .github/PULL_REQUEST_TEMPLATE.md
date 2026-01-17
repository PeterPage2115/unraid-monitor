## Pull Request Checklist

**Before submitting this PR, please ensure:**

- [ ] I have read the [Contributing Guidelines](../CONTRIBUTING.md)
- [ ] My code follows the project's code style (Black formatter, type hints)
- [ ] I have tested my changes locally
- [ ] I have added/updated documentation where necessary
- [ ] I have added an entry to [CHANGELOG.md](../CHANGELOG.md) under `[Unreleased]`
- [ ] No sensitive data (API keys, passwords, personal info) is included

---

## Description

**What does this PR do?**

<!-- Provide a clear description of the changes -->

**Related Issue:**

<!-- Link to the issue this PR addresses -->
Fixes #(issue number) or N/A

---

## Type of Change

<!-- Mark the relevant option with an 'x' -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🧪 Test improvement
- [ ] ♻️ Code refactoring (no functional changes)
- [ ] 🎨 UI/UX improvement
- [ ] ⚡ Performance improvement

---

## Changes Made

<!-- List the specific changes made in this PR -->

-
-
-

---

## Testing

**How has this been tested?**

<!-- Describe the tests you ran to verify your changes -->

- [ ] Ran `python src/test_bot.py` integration tests
- [ ] Tested manually with Docker container
- [ ] Added/updated unit tests (if applicable)
- [ ] Tested on multiple platforms (amd64, arm64)

**Test Configuration:**
- Unraid Version:
- Docker Version:
- Platform:

**Test Results:**

<!-- Paste test output or describe what you verified -->

```
# Example:
$ python src/test_bot.py webhook
✅ Webhook test passed

$ docker logs unraid-monitor
INFO: Monitor started successfully
```

---

## Screenshots

<!-- If applicable, add screenshots to help explain your changes -->
<!-- Delete this section if not applicable -->

**Before:**


**After:**


---

## Documentation

**Documentation updated:**

<!-- Mark the relevant options -->

- [ ] README.md
- [ ] ROADMAP.md
- [ ] Code comments / docstrings
- [ ] Example configurations
- [ ] No documentation changes needed

**If documentation was not updated, explain why:**


---

## Breaking Changes

**Does this PR introduce breaking changes?**

- [ ] Yes
- [ ] No

**If yes, describe what breaks and how to migrate:**


---

## Additional Context

<!-- Add any other context, considerations, or notes for reviewers -->


---

## Reviewer Notes

<!-- Notes for maintainers during review -->

**Areas to focus on:**


**Questions for reviewers:**


---

## Post-Merge Tasks

<!-- Tasks to complete after this PR is merged (if applicable) -->

- [ ] Update Docker Hub image
- [ ] Announce in Discord #announcements
- [ ] Update GitHub Discussions FAQ
- [ ] Create follow-up issues for future work

---

**By submitting this pull request, I confirm that my contribution is made under the terms of the MIT License.**
