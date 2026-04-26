# Contributing to CloudctlSkill

Thank you for your interest in contributing to CloudctlSkill! We welcome contributions from the community.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## Getting Started

### Prerequisites

- Python 3.12+
- Poetry
- cloudctl CLI (for integration tests)

### Development Setup

```bash
# Clone repository
git clone https://github.com/rhyscraig/cloudctl-skill
cd cloudctl-skill

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Verify setup
pytest tests/ -v
mypy src/cloudctl_skill/
```

### Project Structure

```
cloudctl-skill/
├── src/cloudctl_skill/    # Source code
│   ├── __init__.py
│   ├── models.py          # Pydantic data models
│   ├── skill.py           # Main CloudctlSkill class
│   ├── config.py          # Configuration management
│   └── utils.py           # Utilities
├── tests/                 # Test suite
│   ├── test_models.py
│   ├── test_skill.py
│   ├── test_config.py
│   └── test_integration.py
├── docs/                  # Documentation
├── examples/              # Usage examples
├── pyproject.toml         # Project metadata
└── README.md              # Main documentation
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming:
- `feature/*` — New features
- `fix/*` — Bug fixes
- `docs/*` — Documentation updates
- `test/*` — Test improvements
- `refactor/*` — Code refactoring

### 2. Write Code

Follow these standards:

**Code Quality**:
- Black formatting (automatic with `black src/`)
- Ruff linting (check with `ruff check src/`)
- Strict mypy (check with `mypy src/`)
- Descriptive variable/function names

**Type Hints**:
- Required on all public methods
- Use Pydantic models for data structures
- Proper generic types: `dict[str, str]`, `list[int]`, etc.

**Docstrings**:
- Required on all public classes and methods
- Use Google-style format:

```python
def switch_context(self, organization: str) -> CommandResult:
    """Switch cloud context to specified organization.
    
    Validates context switch and updates state. Automatically
    refreshes token if expired.
    
    Args:
        organization: Organization name
        
    Returns:
        CommandResult with switch operation status
        
    Raises:
        ValueError: If organization name is empty
        RuntimeError: If context switch fails
    """
```

### 3. Write Tests

Every change should have tests:

```python
@pytest.mark.unit
async def test_switch_context_success():
    """Test successful context switch."""
    skill = CloudctlSkill()
    # ... test implementation
    
@pytest.mark.integration
async def test_switch_context_integration():
    """Test context switch with real cloudctl."""
    if not cloudctl_installed():
        pytest.skip("cloudctl not installed")
    # ... integration test
```

Test categories:
- `@pytest.mark.unit` — Unit tests (mocked)
- `@pytest.mark.integration` — Integration tests (requires cloudctl)
- `@pytest.mark.security` — Security tests

Run tests:

```bash
# All tests
pytest tests/ -v

# By category
pytest tests/ -m unit
pytest tests/ -m integration

# With coverage
pytest tests/ --cov=cloudctl_skill --cov-report=html
```

### 4. Code Quality Checks

Before committing:

```bash
# Format code
black src/

# Lint code
ruff check src/ --fix

# Type check
mypy src/cloudctl_skill/

# Security check
bandit -r src/cloudctl_skill/

# Run tests
pytest tests/ -v

# Check dependencies
pip-audit
```

Or run all checks:

```bash
make check  # if Makefile exists
# or manually run all above commands
```

### 5. Commit Messages

Use clear, descriptive commit messages:

```
Add token auto-refresh on expiry

- Check token validity before operations
- Auto-refresh if expires within 5 minutes
- Retry failed operation after refresh
- Add TokenStatus model for tracking

Fixes #123
```

Guidelines:
- First line: 50 characters, summary
- Blank line
- Detailed explanation (wrapped at 72 characters)
- Reference issues: `Fixes #123`, `Closes #456`

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request with:

**Title**: Clear, concise summary (50 chars)

**Description**:
```markdown
## Summary
Brief description of changes.

## Changes
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests added
- [ ] Integration tests pass
- [ ] Existing tests still pass
- [ ] Type checking passes
- [ ] Code formatted with black

## Related Issues
Fixes #123
```

## Pull Request Review

PRs must pass:

- ✅ All tests (unit + integration)
- ✅ Type checking (mypy strict)
- ✅ Code formatting (black)
- ✅ Linting (ruff)
- ✅ Security scan (bandit)
- ✅ Dependency audit (pip-audit)
- ✅ Maintainer review

Reviewers may request:
- Tests for edge cases
- Better documentation
- Performance improvements
- Security considerations

## Areas for Contribution

### High Priority

- [ ] Performance optimizations
- [ ] Additional cloud provider support
- [ ] Enhanced error recovery
- [ ] Documentation improvements
- [ ] Example recipes

### Medium Priority

- [ ] Additional configuration options
- [ ] Better logging/observability
- [ ] Integration tests
- [ ] CI/CD improvements
- [ ] Dependency updates

### Low Priority

- [ ] Code refactoring
- [ ] Code style improvements
- [ ] Comment updates
- [ ] Badge/metadata updates

## Documentation Contributions

Documentation improvements welcome!

**Update docs when**:
- Adding new features
- Changing API
- Fixing unclear explanations
- Adding examples
- Reporting bugs

**Documentation files**:
- `README.md` — Main documentation
- `docs/API.md` — API reference
- `docs/ARCHITECTURE.md` — Design documentation
- `docs/TROUBLESHOOTING.md` — Common issues
- `docs/CONFIGURATION.md` — Setup guide
- `examples/` — Usage examples

## Reporting Bugs

Use GitHub Issues with:

**Title**: Clear, concise bug description

**Description**:
```markdown
## Description
What's the issue?

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen?

## Actual Behavior
What actually happens?

## Environment
- OS: macOS/Linux/Windows
- Python: 3.12/3.13
- cloudctl version: (output of `cloudctl --version`)

## Logs/Errors
```
paste error logs here
```

## Possible Solution
(optional) Ideas for fixing the issue
```

## Requesting Features

Use GitHub Discussions or Issues with:

**Title**: Clear feature description

**Description**:
```markdown
## Problem
What problem does this solve?

## Proposed Solution
How should it work?

## Example Usage
```python
# Example code showing desired behavior
```

## Alternatives
Other approaches considered?
```

## Code Review Standards

When reviewing code:

1. **Functionality** — Does it work correctly?
2. **Tests** — Are tests sufficient and passing?
3. **Documentation** — Is it clear and complete?
4. **Performance** — Any performance concerns?
5. **Security** — Any security issues?
6. **Style** — Consistent with project standards?

Be constructive and encouraging in feedback.

## Questions?

- 📖 Check [README.md](README.md)
- 🔍 Search existing [issues](https://github.com/rhyscraig/cloudctl-skill/issues)
- 💬 Ask in [discussions](https://github.com/rhyscraig/cloudctl-skill/discussions)
- ✉️ Email: craig@craighoad.com

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

Thank you for contributing to CloudctlSkill! 🎉
