# CloudctlSkill Security Setup Guide

Complete guide to setting up security checks that prevent secrets from ever entering the repository.

## Table of Contents

- [Quick Start](#quick-start)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Local Scanning](#local-scanning)
- [CI/CD Integration](#cicd-integration)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)

## Quick Start

**Get started in 2 minutes:**

```bash
# 1. Clone the repository
git clone https://github.com/rhyscraig/cloudctl-skill.git
cd cloudctl-skill

# 2. Install pre-commit hooks
chmod +x scripts/pre-commit-secrets
cp scripts/pre-commit-secrets .git/hooks/pre-commit

# 3. Test the hook
echo "password: secret123" > test.yaml
git add test.yaml
git commit -m "test"  # Should fail with security warning

# 4. Clean up
rm test.yaml
git reset HEAD test.yaml
```

**Result:** Pre-commit hook is now active and will prevent secrets from being committed.

## Pre-commit Hooks

### Installation Methods

#### Method 1: Manual Installation (Recommended)

```bash
# Make script executable
chmod +x scripts/pre-commit-secrets

# Copy to git hooks
cp scripts/pre-commit-secrets .git/hooks/pre-commit

# Verify installation
ls -la .git/hooks/pre-commit
# Should show: -rwxr-xr-x (executable)
```

#### Method 2: Using Pre-commit Framework

Install `pre-commit` framework (more robust):

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: local
    hooks:
      - id: secrets-check
        name: Check for secrets
        entry: scripts/pre-commit-secrets
        language: script
        stages: [commit]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
EOF

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### What the Hook Checks

The pre-commit hook scans for:

**AWS Credentials:**
```
AKIA[0-9A-Z]{16}  # AWS Access Key
AWS_SECRET_ACCESS_KEY
AWS_ACCESS_KEY_ID=AKIA...
```

**Private Keys:**
```
BEGIN PRIVATE KEY
BEGIN RSA PRIVATE KEY
BEGIN OPENSSH PRIVATE KEY
-----END.*PRIVATE KEY-----
```

**Credentials in Code:**
```
password = "..."
api_key = "..."
secret = "..."
token = "..."
credential = "..."
```

**Sensitive Files:**
```
.cloudctl.yaml        # User configuration
.env                  # Environment files
*.key, *.pem          # Key files
credentials.json      # Credential files
secrets.yaml          # Secret files
id_rsa                # SSH keys
```

### Testing the Hook

```bash
# 1. Create a test file with a fake secret
echo "password: secret123" > test.txt
git add test.txt

# 2. Try to commit (should fail)
git commit -m "test"
# Output: Pre-commit hook FAILED: Potential secrets detected

# 3. Remove the file
rm test.txt
git reset HEAD test.txt

# 4. Now commit works
git commit -m "normal commit"
# Output: ✅ No secrets detected - safe to commit
```

### Skipping the Hook (Not Recommended)

If you absolutely must skip the check (not recommended):

```bash
# Skip pre-commit hook
git commit --no-verify -m "Commit message"
```

**⚠️ WARNING:** Only do this if you're 100% certain there are no secrets.

## Local Scanning

### Manual Scanning

**Find potential secrets in working directory:**

```bash
# Quick grep scan
grep -r "password\|api_key\|secret\|token" \
    src/ examples/ docs/ \
    --include="*.py" \
    --include="*.yaml" \
    | grep -v "test\|mock\|example\|Token\|token_"

# Scan for AWS keys
grep -r "AKIA[A-Z0-9]\{16\}" .

# Scan for private keys
grep -r "BEGIN.*PRIVATE KEY" .

# Scan for .cloudctl.yaml
find . -name ".cloudctl.yaml" -not -path "./.git/*"
```

### Using detect-secrets

Install and use the `detect-secrets` tool:

```bash
# Install
pip install detect-secrets

# Scan current directory
detect-secrets scan

# Scan specific directory
detect-secrets scan src/

# Scan and output JSON
detect-secrets scan --json > secrets.json

# Scan with custom baseline
detect-secrets scan --baseline .secrets.baseline

# Audit results
detect-secrets audit .secrets.baseline
```

### Using TruffleHog

Entropy-based secret detection:

```bash
# Install
pip install truffleHog

# Scan filesystem
trufflehog filesystem . --json

# Scan for high entropy (faster)
trufflehog filesystem . --json --max-depth 2

# Scan specific directory
trufflehog filesystem src/ --json
```

### Using git-secrets

Git-integrated secret scanning:

```bash
# Install (macOS)
brew install git-secrets

# Or from source
git clone https://github.com/awslabs/git-secrets.git
cd git-secrets
make install

# Install patterns
git secrets --install
git secrets --register-aws

# Scan repository
git secrets --scan

# Scan all commits
git secrets --scan-history
```

## CI/CD Integration

### GitHub Actions Integration

Add to `.github/workflows/security.yml`:

```yaml
name: Security Scanning

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for scanning

      - name: Install dependencies
        run: |
          pip install detect-secrets truffleHog

      - name: Scan with detect-secrets
        run: |
          detect-secrets scan --json > .secrets.json
          detect-secrets audit .secrets.json

      - name: Scan with TruffleHog
        run: |
          trufflehog filesystem . --json --max-depth 3

      - name: Check git-secrets patterns
        run: |
          git clone https://github.com/awslabs/git-secrets.git /tmp/git-secrets
          /tmp/git-secrets/git-secrets --install
          /tmp/git-secrets/git-secrets --register-aws
          /tmp/git-secrets/git-secrets --scan-history
```

### GitLab CI Integration

Add to `.gitlab-ci.yml`:

```yaml
security:scan:
  image: python:3.12
  script:
    - pip install detect-secrets truffleHog
    - detect-secrets scan --json
    - trufflehog filesystem . --json --max-depth 2
  allow_failure: true
```

## Development Workflow

### Safe Development Practices

**1. Configuration Setup**

```bash
# Copy example config
cp .cloudctl.example.yaml ~/.cloudctl.yaml

# Edit with your settings (no secrets here!)
nano ~/.cloudctl.yaml
```

**Example `.cloudctl.yaml` (local, not in git):**
```yaml
cloudctl:
  timeout_seconds: 30
  max_retries: 3
  verify_context_after_switch: true

environment_overrides:
  AWS_REGION: "us-west-2"
  GCLOUD_PROJECT: "my-project"
  # Secrets come from environment, not here!
```

**2. Credentials Setup**

```bash
# Set credentials in environment
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export GCLOUD_APPLICATION_CREDENTIALS="$HOME/.config/gcp/service-account.json"

# Verify (do NOT echo credentials!)
echo "AWS credentials set: $(printenv AWS_ACCESS_KEY_ID | cut -c1-4)***"
```

**3. Working with Code**

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes (no credentials!)
# Edit code, tests, docs - everything is safe

# Test locally
pytest tests/

# Commit (pre-commit hook checks for secrets)
git add src/ tests/
git commit -m "Add feature X"
# Pre-commit hook runs automatically

# Push to GitHub
git push origin feature/my-feature

# Create pull request
gh pr create
```

**4. Testing**

For testing, use mock credentials:

```python
# ✅ GOOD: Use fake credentials for tests
@pytest.fixture
def aws_context():
    return CloudContext(
        provider=CloudProvider.AWS,
        organization="test-org",
        account_id="123456789",  # Fake
        region="us-west-2",
    )

# ❌ BAD: Real credentials in tests
@pytest.fixture
def aws_context():
    return CloudContext(
        organization="production-org",  # Real!
        account_id="987654321012",  # Real AWS account!
    )
```

## Troubleshooting

### Hook is not running

**Problem:** Pre-commit hook doesn't run when committing

**Solution:**

```bash
# 1. Check hook exists and is executable
ls -la .git/hooks/pre-commit
# Should show: -rwxr-xr-x (executable)

# 2. Make it executable
chmod +x .git/hooks/pre-commit

# 3. Test manually
.git/hooks/pre-commit

# 4. Check git config
git config core.hooksPath

# 5. Reinstall hook
cp scripts/pre-commit-secrets .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### False positives

**Problem:** Hook blocks legitimate code with false positives

**Solution:**

```bash
# 1. Review the match
# Example: "password" in a variable name like "password_length"

# 2. Suppress in hook
# Add to .git/hooks/pre-commit near the pattern:
# Add exclusion for false positives
forbidden_patterns=(
    # ... existing patterns ...
)

# Or mark line as safe
# Add comment to line: # pragma: secret-ok
def check_password_length(password_param):  # pragma: secret-ok
    return len(password_param)

# 3. Update hook script to skip pragma lines
```

### Hook is too strict

**Problem:** Hook rejects safe changes

**Solution:**

```bash
# Review what triggered the hook
# Check if it's actually a false positive

# If you're sure it's safe:
git commit --no-verify -m "Commit message"

# Then update the hook to handle this case
# Edit .git/hooks/pre-commit
# Add better filtering for false positives

# Document the exception
# Add to SECURITY.md why this pattern is safe
```

### Recovering from secret commit

**If a secret was accidentally committed:**

1. **Stop immediately** - Don't push!

2. **Rotate the credential** - Immediately invalidate it

3. **Revert the commit:**
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

4. **Or force push** (if not yet shared):
   ```bash
   git reset --hard HEAD~1
   git push --force-with-lease origin main
   ```

5. **Verify removal:**
   ```bash
   git log --all -p | grep -i "password\|api_key\|token"
   # Should find nothing
   ```

6. **Update security:**
   - Add pattern to hook
   - Document in SECURITY.md
   - Brief team on what happened

## Verification Checklist

**Before considering security setup complete:**

- [ ] Pre-commit hook is installed and executable
- [ ] Hook blocks test with fake credentials
- [ ] `.cloudctl.yaml` is in `.gitignore`
- [ ] `.cloudctl.example.yaml` has no real values
- [ ] Environment variables set for real credentials
- [ ] SECURITY.md is comprehensive
- [ ] Security tests pass (`pytest tests/test_security.py`)
- [ ] No hardcoded secrets in codebase
- [ ] All team members have hooks installed
- [ ] CI/CD has security scanning configured

## Best Practices

1. **Always commit with hooks enabled**
   - Never `--no-verify` without reviewing

2. **Keep credentials in environment only**
   - Never in files, code, or configs

3. **Rotate credentials regularly**
   - Especially after access by others

4. **Use `.cloudctl.example.yaml` as template**
   - Show structure, not real values

5. **Document security decisions**
   - Keep SECURITY.md updated

6. **Test security regularly**
   - Run security tests in CI/CD

7. **Review suspicious commits**
   - Check `git log` for secrets patterns

8. **Keep scanning tools updated**
   - Update detect-secrets, TruffleHog, etc.

## Summary

CloudctlSkill uses **multiple layers of security** to prevent secrets:

1. **Architecture** - Code doesn't handle credentials
2. **Configuration** - Secrets via environment only
3. **Pre-commit Hooks** - Local detection before commit
4. **Code Review** - Manual verification
5. **CI/CD Scanning** - Automated detection
6. **Testing** - Security test suite
7. **Documentation** - Clear guidelines
8. **Incident Response** - Plan if something slips

**Result: Secrets cannot leak to this public repository.**
