# CloudctlSkill Security Policy

**CRITICAL: This document establishes absolute guardrails to prevent secrets from ever entering the repository.**

## Table of Contents

- [Security Philosophy](#security-philosophy)
- [Secrets Management](#secrets-management)
- [Architecture Patterns](#architecture-patterns)
- [Code Review Security Checklist](#code-review-security-checklist)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Secrets Scanning](#secrets-scanning)
- [Configuration Safety](#configuration-safety)
- [Incident Response](#incident-response)
- [Security Guidelines](#security-guidelines)

## Security Philosophy

### Core Principles

1. **All Secrets Stay Local**
   - Credentials never in code, tests, or examples
   - Configuration stored locally only
   - Environment variables for CI/CD

2. **Defense in Depth**
   - Multiple layers of protection
   - Automated scanning + manual review
   - Pre-commit hooks + CI/CD checks

3. **Fail Secure**
   - Default deny when in doubt
   - Clear error messages without leaking info
   - Safe defaults in all configurations

4. **Audit Everything**
   - Track when/where configs are accessed
   - Log credential refresh operations
   - Monitor for suspicious patterns

## Secrets Management

### What Is a Secret?

❌ **NEVER COMMIT THESE:**
- API keys, tokens, credentials
- Passwords, SSH keys, certificates
- AWS access keys, GCP service accounts
- Azure subscription IDs with context
- Database connection strings
- Private encryption keys
- OAuth tokens, bearer tokens
- Any real account IDs or organization names

✅ **SAFE TO COMMIT:**
- Example/dummy values (12345678, my-org)
- Configuration structure (.cloudctl.example.yaml)
- Pattern documentation
- Public documentation and guides
- Error handling code
- Test fixtures with fake data

### Configuration-Only Model

**Architecture Decision: NO credential handling in code**

```python
# ❌ WRONG - Code touches credentials
class CloudctlSkill:
    def __init__(self, api_key: str):
        self.api_key = api_key  # NEVER!
        self.client = APIClient(self.api_key)

# ✅ RIGHT - Code uses environment
class CloudctlSkill:
    def __init__(self):
        # Never store credentials in instance
        # Subprocess execution isolates credential passing
        pass
    
    async def _execute_cloudctl(self, *args: str) -> CommandResult:
        # cloudctl binary handles credentials internally
        # CloudctlSkill never sees them
        process = await asyncio.create_subprocess_exec(
            self.config.cloudctl_path, *args
            # Credentials passed through subprocess environment
        )
```

**Why This Works:**
- CloudctlSkill never stores credentials
- External `cloudctl` binary handles auth
- Environment variables isolated to subprocess
- Code remains secret-free

### Configuration Files

**`.cloudctl.yaml` - LOCAL ONLY**

```yaml
# This file is NEVER committed
# Add to .gitignore: ✅ Done
# Use .cloudctl.example.yaml for templates

cloudctl:
  timeout_seconds: 30
  max_retries: 3

environment_overrides:
  # Only non-sensitive environment variables here
  AWS_REGION: "us-west-2"  # ✅ OK
  # NEVER: AWS_ACCESS_KEY_ID: "AKIA..."  ❌
```

**.cloudctl.example.yaml - TEMPLATE ONLY**

```yaml
# This file IS committed
# Shows structure and examples only
# NO real values, NO organization names

cloudctl:
  timeout_seconds: 30
  max_retries: 3

environment_overrides:
  # Example values only
  AWS_REGION: us-west-2
  # GCLOUD_PROJECT: my-project  # Commented example
```

**Environment Variables - For Secrets**

```bash
# Credentials go here, never in files
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export GCLOUD_SERVICE_ACCOUNT_JSON="..."

# CloudctlSkill reads these via subprocess
result = await skill.ensure_cloud_access("myorg")
```

## Architecture Patterns

### Pattern 1: Subprocess Isolation

Credentials stay in subprocess environment, never in Python code:

```python
# ✅ GOOD: Subprocess handles credentials
process = await asyncio.create_subprocess_exec(
    "cloudctl", "context", "switch", organization,
    # cloudctl binary handles credentials internally
    # They never enter CloudctlSkill process
)

# ❌ WRONG: Passing credentials through code
result = cloudctl_command(
    organization=organization,
    api_key=os.environ["API_KEY"],  # NEVER
)
```

### Pattern 2: Configuration-Only Storage

Store only configuration, never credentials:

```python
class SkillConfig(BaseModel):
    """Configuration - NEVER credentials"""
    cloudctl_path: str  # ✅ OK
    cloudctl_timeout: int  # ✅ OK
    # api_key: str  # ❌ NEVER
    # password: str  # ❌ NEVER
    # token: str  # ❌ NEVER
```

### Pattern 3: Error Safety

Error messages never leak secrets:

```python
# ❌ WRONG: Leaks credentials
except Exception as e:
    print(f"Error: {e}")  # Could contain credentials

# ✅ RIGHT: Safe error message
except Exception as e:
    logger.error("Authentication failed")  # Generic
    logger.debug(f"Subprocess returned: {e}")  # Logged, not displayed
    return CommandResult(
        success=False,
        error="Authentication failed",
        fix="Check CLOUDCTL_PATH and credentials"
    )
```

### Pattern 4: No Credential Parameters

Methods never take credentials as parameters:

```python
# ❌ WRONG: Takes credentials
async def login(self, org: str, api_key: str) -> CommandResult:
    pass

# ✅ RIGHT: Uses environment
async def login(self, org: str) -> CommandResult:
    # Credentials from environment, never as parameter
    result = await self._execute_cloudctl("auth", "login", org)
```

### Pattern 5: Configuration Precedence Chain

```python
# Loading order (highest to lowest precedence)
# 1. Environment variables (CLOUDCTL_*)
# 2. Local config (./.cloudctl.yaml)
# 3. Home config (~/.cloudctl.yaml)
# 4. Defaults (SkillConfig)

# This ensures:
# - Environment overrides everything (CI/CD friendly)
# - Local config for user customization
# - Home config for system defaults
# - Defaults are safe and sensible
# - No secrets needed at any level
```

## Code Review Security Checklist

**Every PR must pass this checklist:**

### Before Approval

- [ ] No hardcoded credentials (grep: password, secret, key, token, api_key)
- [ ] No real AWS/GCP/Azure IDs in code
- [ ] No real organization names in code
- [ ] No credentials in test fixtures
- [ ] No credentials in example code
- [ ] No credentials in documentation
- [ ] Error messages don't leak secrets
- [ ] No new model fields for credentials
- [ ] Config files point to .gitignore
- [ ] All file paths documented in .gitignore

### Configuration Files

- [ ] `.cloudctl.example.yaml` has no real values
- [ ] `.cloudctl.yaml` is in `.gitignore`
- [ ] No environment variable defaults with secrets
- [ ] Configuration docs show safe examples only

### Testing

- [ ] Tests use fake credentials only
- [ ] Mock objects don't contain real values
- [ ] Test fixtures use dummy data
- [ ] Integration tests use dry-run mode
- [ ] No test secrets in CI/CD config

### Documentation

- [ ] Docs show template examples only
- [ ] README has no real account IDs
- [ ] Contributing guide warns about secrets
- [ ] Architecture docs explain secret safety
- [ ] Troubleshooting shows generic examples

## Pre-commit Hooks

**Prevent commits with secrets automatically:**

### Installation

```bash
# Copy hook to .git/hooks/
cp scripts/pre-commit-secrets .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Or use pre-commit framework
pip install pre-commit
pre-commit install
```

### What It Checks

```bash
# Detects common secret patterns
- AWS Access Keys (AKIA...)
- Private keys (BEGIN PRIVATE KEY)
- Passwords (password: [value])
- API keys (api_key: [value])
- Tokens (token: [value])
- Service account JSON
- Connection strings
```

### Example Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

set -e

# Files to check
files=$(git diff --cached --name-only | grep -E '\.(py|yaml|yml|json|md|toml)$')

# Secret patterns
patterns=(
    'AKIA[0-9A-Z]\{16\}'           # AWS key
    'password\s*[:=]'                # Password assignment
    'api_key\s*[:=]'                 # API key assignment
    'secret\s*[:=]'                  # Secret assignment
    'BEGIN PRIVATE KEY'               # Private key
    'BEGIN RSA PRIVATE KEY'           # RSA key
    'authorization\s*[:=]\s*Bearer'  # Bearer token
)

failed=0
for file in $files; do
    for pattern in "${patterns[@]}"; do
        if grep -E "$pattern" "$file"; then
            echo "❌ Potential secret in $file"
            failed=1
        fi
    done
done

if [ $failed -eq 1 ]; then
    echo "Pre-commit hook failed: potential secrets detected"
    echo "Review the matches above and remove any credentials"
    exit 1
fi
```

## Secrets Scanning

### Local Scanning

```bash
# Find potential secrets in working directory
grep -r "password\|api_key\|secret\|token" \
    --include="*.py" \
    --include="*.yaml" \
    --include="*.json" \
    src/ examples/ docs/ \
    | grep -v "tokenStatus\|token_status\|get_token\|Token\|SECRET\|KEY\|PASSWORD"

# Scan for AWS keys
grep -r "AKIA[A-Z0-9]\{16\}" src/ examples/

# Scan for private keys
grep -r "BEGIN.*PRIVATE KEY" .
```

### GitHub Actions Scanning

**In `.github/workflows/security.yml`:**

```yaml
- name: Secret scanning with truffleHog
  run: |
    pip install truffleHog
    trufflehog filesystem . --json --max-depth 3
    
- name: Detect secrets with detect-secrets
  run: |
    pip install detect-secrets
    detect-secrets scan --all-files
```

### Tools to Use

1. **TruffleHog** - Entropy-based detection
   ```bash
   pip install truffleHog
   trufflehog filesystem .
   ```

2. **detect-secrets** - Pattern-based detection
   ```bash
   pip install detect-secrets
   detect-secrets scan
   ```

3. **git-secrets** - Git hook integration
   ```bash
   brew install git-secrets
   git secrets --install
   git secrets --register-aws
   ```

## Configuration Safety

### Safe Configuration Pattern

```python
from pathlib import Path
import os
import yaml

def load_config() -> SkillConfig:
    """Load configuration from safe sources only.
    
    Configuration precedence (NEVER includes secrets):
    1. Environment variables (CLOUDCTL_*)
    2. Local .cloudctl.yaml (NOT in git)
    3. Home ~/.cloudctl.yaml (NOT in git)
    4. Defaults (SkillConfig)
    
    Returns:
        SkillConfig with only safe configuration
        
    Raises:
        ValueError: If configuration contains secrets
    """
    config_dict = {}
    
    # Load from home directory
    home_config = Path.home() / ".cloudctl.yaml"
    if home_config.exists():
        with open(home_config) as f:
            loaded = yaml.safe_load(f) or {}
            _validate_no_secrets(loaded, home_config)
            config_dict.update(loaded)
    
    # Load from current directory
    local_config = Path(".cloudctl.yaml")
    if local_config.exists():
        with open(local_config) as f:
            loaded = yaml.safe_load(f) or {}
            _validate_no_secrets(loaded, local_config)
            config_dict.update(loaded)
    
    # Load from environment (highest priority)
    env_config = _load_env_config()
    _validate_no_secrets(env_config, "environment")
    config_dict.update(env_config)
    
    return SkillConfig(**config_dict)


def _validate_no_secrets(config: dict, source: str) -> None:
    """Validate configuration contains no secrets.
    
    Args:
        config: Configuration dictionary
        source: Source name for error messages
        
    Raises:
        ValueError: If secrets detected
    """
    forbidden_keys = {
        "password", "secret", "api_key", "token",
        "credential", "key", "access_key", "private_key",
        "auth", "oauth", "bearer"
    }
    
    def check_dict(d: dict, path: str = "") -> None:
        for key, value in d.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check key names
            if key.lower() in forbidden_keys:
                raise ValueError(
                    f"Configuration from {source} contains forbidden key: {current_path}\n"
                    f"Credentials must be in environment variables only, never in configuration files."
                )
            
            # Check values for obvious credentials
            if isinstance(value, str):
                if any(pattern in value for pattern in ["AKIA", "GCLOUDSDKAUTH"]):
                    raise ValueError(
                        f"Potential credentials detected in {source}: {current_path}\n"
                        f"Use environment variables instead."
                    )
            
            # Recurse into nested dicts
            if isinstance(value, dict):
                check_dict(value, current_path)
    
    check_dict(config)
```

## Incident Response

### If Secrets Are Accidentally Committed

1. **Immediately:**
   ```bash
   # Revert the commit
   git revert <commit-hash>
   
   # Or force-push if not yet public
   git reset --hard HEAD~1
   git push --force-with-lease
   ```

2. **Audit:**
   - Check when secret was committed
   - Check who accessed it
   - Check if deployed anywhere

3. **Rotate:**
   - Rotate all compromised credentials
   - Update all places using them
   - Verify rotation worked

4. **Review:**
   - Add detection to hooks
   - Update CI/CD scanning
   - Add to team guidelines

5. **Document:**
   - Document what happened
   - Document how it was prevented
   - Update SECURITY.md

## Security Guidelines

### Development

1. **Never use real credentials in development**
   ```bash
   # ✅ USE: Environment variables
   export CLOUDCTL_ORG="test-org"
   export AWS_REGION="us-west-2"
   
   # ❌ NEVER: Hardcode credentials
   CLOUDCTL_API_KEY="sk-..."
   ```

2. **Use dummy data for testing**
   ```python
   # ✅ USE: Fake data
   @pytest.fixture
   def aws_context():
       return CloudContext(
           organization="test-org",  # Dummy
           account_id="123456789",   # Dummy
       )
   
   # ❌ NEVER: Real credentials
   account_id="987654321012"  # Real AWS account
   ```

3. **Keep local config private**
   ```bash
   # ✅ GOOD: In .gitignore
   .cloudctl.yaml
   .env
   *.key
   
   # ✅ GOOD: Local only
   ~/.cloudctl.yaml  # User's home directory
   ```

### Code Review

1. **Ask these questions for every PR:**
   - Does this code handle credentials?
   - Could any environment variables leak?
   - Are there any hardcoded values?
   - Are error messages safe?
   - Are tests using real data?

2. **Red flags:**
   - Credentials passed as parameters
   - Config files with real values
   - Environment variable defaults with secrets
   - Example code with actual accounts
   - Error logging without sanitization

### Documentation

1. **Never document real values**
   ```markdown
   # ✅ GOOD: Generic examples
   ```bash
   export AWS_REGION="us-west-2"
   export GCLOUD_PROJECT="my-project"
   ```
   
   # ❌ WRONG: Real values
   ```bash
   export AWS_REGION="eu-west-1"
   export AWS_ACCESS_KEY_ID="AKIA1234..."
   ```

2. **Always show the template**
   ```markdown
   See `.cloudctl.example.yaml` for configuration template.
   Copy to `.cloudctl.yaml` and customize for your environment.
   ```

### Testing

1. **Use mocking extensively**
   ```python
   @patch('cloudctl_skill.skill.asyncio.create_subprocess_exec')
   async def test_switch_context(mock_exec):
       # Use mock, never real credentials
       mock_exec.return_value.communicate.return_value = (b"aws:prod", b"")
   ```

2. **Never use real credentials in tests**
   ```python
   # ✅ GOOD: Fake data
   mock_result = CommandResult(success=True, output="mock output")
   
   # ❌ WRONG: Real credentials
   os.environ["AWS_ACCESS_KEY_ID"] = "AKIA..."
   ```

3. **Use dry-run for integration tests**
   ```python
   async def test_integration():
       config = SkillConfig(dry_run=True)
       skill = CloudctlSkill(config)
       # Won't actually execute commands
   ```

## Reporting Security Issues

**Do NOT open public issues for security vulnerabilities.**

1. **Email:** security@craighoad.com
2. **Include:**
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

3. **Expect:**
   - Acknowledgment within 48 hours
   - Fix within 7 days (if confirmed)
   - Public notification after patch
   - Credit if desired

## Compliance

This repository maintains:

- ✅ **No hardcoded secrets** - Verified by pre-commit hooks
- ✅ **No credential parameters** - Architecture prevents it
- ✅ **Safe error messages** - Code review checklist
- ✅ **Configuration-only model** - Enforced by design
- ✅ **Environment isolation** - Subprocess patterns
- ✅ **Audit logging** - JSONL for operations
- ✅ **Secret scanning** - CI/CD and local tools
- ✅ **Security documentation** - This file

## Summary

**CloudctlSkill maintains absolute security through:**

1. **Architecture Design** - Impossible to store credentials
2. **Configuration Pattern** - Secrets never in code
3. **Code Review** - Human verification at every step
4. **Automated Scanning** - Machine detection of leaks
5. **Pre-commit Hooks** - Prevention before commit
6. **CI/CD Checks** - Verification before merge
7. **Documentation** - Clear guidelines for all
8. **Incident Response** - Plan if something slips

**Result: Secrets cannot leak to this public repository.**
