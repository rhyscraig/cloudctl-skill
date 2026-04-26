# CloudctlSkill Project Configuration

## Repository Overview

This repository contains **CloudctlSkill v1.2.0** — an enterprise-grade Python library for cloud context management with Model Context Protocol (MCP) integration for Claude.

**Key Facts:**
- **Purpose**: Multi-cloud context management (AWS, GCP, Azure)
- **Model**: Zero-credential architecture (credentials handled externally)
- **Integration**: MCP server for Claude (`/cloudctl` command)
- **Status**: Production-ready, 48 tests passing

## When to Use CloudctlSkill

Use CloudctlSkill when:
1. **Switching cloud contexts** in Claude workflows
2. **Managing multi-cloud operations** (AWS, GCP, Azure)
3. **Verifying cloud credentials and access**
4. **Checking current cloud context** (provider, account, region)
5. **Automating cloud operations** without credential management

## Architecture

```
User Request (/cloudctl command in Claude)
    ↓
Claude MCP Server (mcp.py)
    ↓
CloudctlSkill Library (skill.py)
    ↓
cloudctl Binary (handles SSO/authentication)
    ↓
Cloud Provider (AWS/GCP/Azure)
```

**Key Design Principle**: cloudctl binary manages all authentication. CloudctlSkill is a stateless wrapper.

## Configuration

### Master Configuration: ~/.cloudctl.yaml

Defines your organizations and preferences:

```yaml
cloudctl:
  timeout_seconds: 30
  max_retries: 3
  verify_context_after_switch: true
  enable_audit_logging: true
  enable_caching: true
  cache_ttl_seconds: 300

environment_overrides:
  AWS_REGION: us-west-2
  GCLOUD_PROJECT: my-dev-project
```

### MCP Server Registration: ~/.claude/settings.json

CloudctlSkill is registered as an MCP server:

```json
{
  "mcpServers": {
    "cloudctl": {
      "command": "python3",
      "args": ["-m", "cloudctl_skill.mcp"],
      "cwd": "/path/to/cloudctl-skill",
      "description": "Cloud context management"
    }
  }
}
```

### Skill Manifest: ~/.claude/skills/cloudctl.json

Describes available commands and capabilities.

## Development Workflow

### Setup

```bash
# 1. Clone and install
git clone https://github.com/rhyscraig/cloudctl-skill
cd cloudctl-skill
make install-dev

# 2. Set up configuration
cp .cloudctl.example.yaml ~/.cloudctl.yaml
nano ~/.cloudctl.yaml

# 3. Verify cloudctl is installed
cloudctl status
```

### Development

```bash
# Run tests
make test

# Run with coverage
make test-cov

# Format code
make format

# Type check
make type-check

# Lint
make lint
```

### Testing

```bash
# All tests
make test

# Unit tests only
make test-unit

# Security tests only
make test-security

# Integration tests
make test-integration

# With coverage
make test-cov
```

## File Organization

```
cloudctl-skill/
├── src/cloudctl_skill/
│   ├── __init__.py          # Package initialization
│   ├── mcp.py               # MCP server for Claude
│   ├── skill.py             # Core CloudctlSkill class
│   ├── models.py            # Pydantic data models
│   ├── config.py            # Configuration loading
│   └── ...                  # Other modules
├── tests/
│   ├── test_cloudctl_skill.py       # Unit tests
│   ├── test_security.py             # Security tests
│   └── ...
├── docs/
│   ├── ARCHITECTURE.md      # Architecture details
│   ├── API.md               # API reference
│   ├── CONFIGURATION.md     # Configuration guide
│   └── ...
├── .claude/
│   ├── SKILL.md             # Integration guide
│   ├── CLAUDE.md            # This file
│   ├── cloudctl.md          # User guide
│   └── skills/cloudctl.json # Skill manifest
├── skill.md                 # Skill definition
├── pyproject.toml           # Python package config
├── requirements.txt         # Dependencies
├── Makefile                 # Development commands
└── pytest.ini               # Test configuration
```

## Key Files

| File | Purpose |
|------|---------|
| `src/cloudctl_skill/mcp.py` | MCP server - handles JSON-RPC requests from Claude |
| `src/cloudctl_skill/skill.py` | Core logic - context management, switching, validation |
| `src/cloudctl_skill/models.py` | Data models - CloudContext, CommandResult, HealthCheckResult |
| `tests/test_cloudctl_skill.py` | Unit tests - 30 core tests |
| `tests/test_security.py` | Security tests - credential safety validation |
| `.claude/SKILL.md` | Integration guide for Claude |
| `.claude/cloudctl.md` | Complete user guide |
| `skill.md` | Skill definition with examples |
| `COMPREHENSIVE_TEST_REPORT.md` | Test results and validation |
| `TROUBLESHOOTING.md` | Debugging guide |
| `docs/ARCHITECTURE.md` | System architecture |
| `docs/CONFIGURATION.md` | Configuration reference |

## Security Model

CloudctlSkill follows **defense-in-depth security**:

✅ **No credentials in code** — Never stored or handled  
✅ **No credentials in config** — Only organization definitions  
✅ **No credentials in environment** — Managed by cloudctl  
✅ **Pydantic validation** — All inputs/outputs validated  
✅ **Immutable models** — Frozen dataclasses  
✅ **Audit logging** — JSONL compliance format  
✅ **Pre-commit hooks** — Prevent credential commits  

**Golden Rule**: The `cloudctl` binary handles all authentication. CloudctlSkill never touches credentials.

## Testing Strategy

### Test Coverage

| Category | Tests | Status |
|----------|-------|--------|
| Models & Data | 9 | ✅ Pass |
| Configuration | 5 | ✅ Pass |
| Context Operations | 4 | ✅ Pass |
| Credentials | 2 | ✅ Pass |
| Health Checks | 1 | ✅ Pass |
| Multi-Cloud | 3 | ✅ Pass |
| Error Handling | 1 | ✅ Pass |
| Integration | 2 | ✅ Pass |
| Async Operations | 1 | ✅ Pass |
| Security | 14 | ✅ Pass |
| **Total** | **48** | **✅ 100%** |

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=cloudctl_skill --cov-report=html

# Specific test suite
pytest tests/test_cloudctl_skill.py -v
pytest tests/test_security.py -v

# Async tests only
pytest tests/ -v -m asyncio

# With markers
pytest tests/ -m "not slow"
```

## CI/CD & Deployment

### Pre-commit Hooks

The repository includes pre-commit hooks to prevent credential leakage:
- No AWS keys allowed in commits
- No private keys in source
- No credential assignments
- Configuration files validated

### GitHub Actions

Tests run on:
- Python 3.12+
- All major cloud providers supported
- 100% test pass requirement

## Documentation

### User Documentation
- **`.claude/SKILL.md`** — How Claude should use CloudctlSkill
- **`.claude/cloudctl.md`** — Complete user guide with examples
- **`skill.md`** — Skill definition and capabilities

### Developer Documentation
- **`docs/ARCHITECTURE.md`** — System design and components
- **`docs/API.md`** — Complete API reference
- **`docs/CONFIGURATION.md`** — Configuration options

### Reports & Guides
- **`COMPREHENSIVE_TEST_REPORT.md`** — Full test results
- **`TROUBLESHOOTING.md`** — Debugging guide

## Troubleshooting

### Common Issues

**"cloudctl-skill not found"**
```bash
pip install cloudctl-skill
```

**"/cloudctl command not visible"**
- Fully close and reopen Claude
- Check settings.json has MCP registration
- Verify cwd parameter points to correct directory

**"No active context found"**
```bash
cloudctl login
cloudctl switch <org>
```

**Tests failing**
```bash
# Run with verbose output
pytest tests/ -vvv

# Check pytest configuration
cat pytest.ini
```

## Related Resources

- **GitHub Repository**: https://github.com/rhyscraig/cloudctl-skill
- **Issue Tracker**: https://github.com/rhyscraig/cloudctl-skill/issues
- **Discussions**: https://github.com/rhyscraig/cloudctl-skill/discussions

## Contributing

Contributions welcome! When adding features:

1. Write tests first (TDD approach)
2. Ensure all 48 tests pass
3. Add security tests if handling credentials
4. Update documentation
5. Run: `make lint format type-check`
6. Create PR with test results

## License

MIT License — See LICENSE file

---

**Questions?** Check `.claude/SKILL.md` or `TROUBLESHOOTING.md`
