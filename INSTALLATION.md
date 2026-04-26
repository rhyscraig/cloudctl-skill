# CloudctlSkill Installation & Setup

Complete guide to installing CloudctlSkill and registering it with Claude.

## Quick Start (5 minutes)

### 1. Install the Package

```bash
# Option A: From PyPI (when published)
pip install cloudctl-skill

# Option B: From GitHub (development)
git clone https://github.com/rhyscraig/cloudctl-skill
cd cloudctl-skill
pip install -e .

# Option C: From current directory
cd /tmp/cloudctl-skill
pip install -e .
```

### 2. Verify Installation

```bash
# Test the installation
python -c "from cloudctl_skill import CloudctlSkill; print('✅ CloudctlSkill installed')"

# Check version
python -c "from cloudctl_skill import __version__; print(f'Version: {__version__}')"
```

### 3. Configure Locally

```bash
# Copy example configuration
cp .cloudctl.example.yaml ~/.cloudctl.yaml

# Edit with your settings (no secrets here!)
nano ~/.cloudctl.yaml
```

### 4. Set Environment Variables

```bash
# AWS
export AWS_ACCESS_KEY_ID="your-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-west-2"

# Or GCP
export GCLOUD_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GCLOUD_PROJECT="my-project"

# Or Azure
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_TENANT_ID="your-tenant-id"
```

### 5. Install Pre-commit Hooks (Recommended)

```bash
# Navigate to the skill repository
cd /path/to/cloudctl-skill

# Install the pre-commit hook
chmod +x scripts/pre-commit-secrets
cp scripts/pre-commit-secrets .git/hooks/pre-commit

# Test it works
echo "password: test123" > test.txt
git add test.txt
git commit -m "test"  # Should fail
```

### 6. Register with Claude

To enable the `/cloudctl` command in Claude:

**Option A: Via Claude Settings (When Available)**
1. Open Claude settings
2. Go to Skills section
3. Click "Add Skill"
4. Enter repository: `https://github.com/rhyscraig/cloudctl-skill`
5. Or upload `SKILL_MANIFEST.json` from the repository

**Option B: Manual Registration (Development)**
If your Claude instance has a skills API, register via:

```bash
# Register the skill
curl -X POST http://your-claude-instance/skills \
  -H "Content-Type: application/json" \
  -d @SKILL_MANIFEST.json
```

**Option C: Direct Installation**
Copy the skill manifest to your Claude skills directory:

```bash
# Find your Claude skills directory
# (varies by installation - typically ~/.claude/skills/)
mkdir -p ~/.claude/skills/
cp SKILL_MANIFEST.json ~/.claude/skills/cloudctl.json
```

---

## Verification

### Test Basic Installation

```python
import asyncio
from cloudctl_skill import CloudctlSkill

async def test():
    skill = CloudctlSkill()
    
    # Get current context
    context = await skill.get_context()
    print(f"✅ Current context: {context}")
    
    # List organizations
    orgs = await skill.list_organizations()
    print(f"✅ Organizations: {orgs}")

asyncio.run(test())
```

### Test /cloudctl Command

Once registered with Claude, try:

```
/cloudctl context
/cloudctl list orgs
/cloudctl check credentials
/cloudctl health
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'cloudctl_skill'"

**Solution:**
```bash
# Reinstall the package
pip install -e /path/to/cloudctl-skill

# Or add to PYTHONPATH
export PYTHONPATH="/path/to/cloudctl-skill/src:$PYTHONPATH"
```

### "cloudctl: command not found"

**Solution:**
```bash
# Install cloudctl binary from your cloud provider
# AWS
aws --version  # Should be installed

# GCP
gcloud --version  # Should be installed

# Or set CLOUDCTL_PATH environment variable
export CLOUDCTL_PATH="/path/to/cloudctl"
```

### Pre-commit hook not running

**Solution:**
```bash
# Make sure it's executable
chmod +x .git/hooks/pre-commit

# Test it manually
.git/hooks/pre-commit

# Reinstall if needed
cp scripts/pre-commit-secrets .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### "/cloudctl command not found" in Claude

**Solution:**
1. Verify skill is registered (check Claude settings)
2. Restart Claude or refresh the page
3. Check that SKILL_MANIFEST.json exists in the repository
4. Verify the skill path in Claude configuration points to the correct repository

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLOUDCTL_PATH` | `cloudctl` | Path to cloudctl binary |
| `CLOUDCTL_TIMEOUT` | `30` | Command timeout in seconds |
| `CLOUDCTL_RETRIES` | `3` | Number of retry attempts |
| `CLOUDCTL_VERIFY` | `true` | Verify context after switch |
| `CLOUDCTL_AUDIT` | `true` | Enable audit logging |

### Local Configuration

Create `~/.cloudctl.yaml`:

```yaml
cloudctl:
  timeout_seconds: 30
  max_retries: 3
  verify_context_after_switch: true
  enable_audit_logging: true
  dry_run: false

environment_overrides:
  AWS_REGION: "us-west-2"
  GCLOUD_PROJECT: "my-project"
  # Credentials come from environment, NOT here!
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/test_cloudctl_skill.py -v

# Security tests only
pytest tests/test_security.py -v

# With coverage
pytest tests/ --cov=cloudctl_skill --cov-report=html
```

---

## Development Setup

```bash
# Clone repository
git clone https://github.com/rhyscraig/cloudctl-skill
cd cloudctl-skill

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
chmod +x scripts/pre-commit-secrets
cp scripts/pre-commit-secrets .git/hooks/pre-commit

# Run tests
pytest tests/ -v

# Type checking
mypy src/cloudctl_skill/

# Linting
ruff check src/
black --check src/
```

---

## Next Steps

1. **Read the Documentation**
   - [API Reference](docs/API.md) — Complete API documentation
   - [Architecture](docs/ARCHITECTURE.md) — Design principles
   - [Security](SECURITY.md) — Security policy

2. **Explore Examples**
   - [Basic Usage](examples/basic_usage.py)
   - [Multi-cloud](examples/multi_cloud_switching.py)
   - [Error Handling](examples/error_handling.py)

3. **Join the Community**
   - GitHub: [rhyscraig/cloudctl-skill](https://github.com/rhyscraig/cloudctl-skill)
   - Issues: Report bugs and request features
   - Discussions: Share ideas and ask questions

---

## Support

- 📖 [Documentation](https://github.com/rhyscraig/cloudctl-skill)
- 🐛 [Report Issues](https://github.com/rhyscraig/cloudctl-skill/issues)
- 💬 [Discussions](https://github.com/rhyscraig/cloudctl-skill/discussions)
- 🔒 [Security Policy](SECURITY.md)

---

## License

MIT — See LICENSE for details.
