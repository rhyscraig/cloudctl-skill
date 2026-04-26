# CloudctlSkill Configuration Guide

Complete guide to configuring CloudctlSkill for your environment.

## Configuration Overview

CloudctlSkill uses a layered configuration system:

1. **Environment variables** (highest priority)
2. `./.cloudctl.yaml` (current directory)
3. `~/.cloudctl.yaml` (home directory)
4. **Default values** (lowest priority)

Later layers override earlier ones.

## Configuration Files

### Location

| Config File | Location | Purpose |
|------------|----------|---------|
| Local config | `./.cloudctl.yaml` (current directory) | Project-specific settings |
| Home config | `~/.cloudctl.yaml` (home directory) | Global settings |
| Default | Hardcoded in code | Fallback values |

### File Format

Configuration files are YAML. Start by copying the example:

```bash
cp .cloudctl.example.yaml ~/.cloudctl.yaml
nano ~/.cloudctl.yaml
```

---

## Configuration Sections

### 1. CloudctlSkill Settings

```yaml
cloudctl:
  # Path to cloudctl binary
  # Default: "cloudctl" (must be in PATH)
  cloudctl_path: cloudctl

  # Command timeout in seconds (1-300)
  # Default: 30
  # Increase for slow networks or large organizations
  timeout_seconds: 30

  # Maximum retry attempts (0-50)
  # Default: 3
  # Uses exponential backoff: 1s, 2s, 4s...
  max_retries: 3

  # Verify context after switching (adds ~50ms per switch)
  # Default: true
  verify_context_after_switch: true

  # Enable operation audit logging
  # Default: true
  # Logs to: ~/.config/cloudctl/audit/operations_YYYYMMDD.jsonl
  enable_audit_logging: true

  # Dry-run mode (don't execute commands)
  # Default: false
  # Useful for testing configuration
  dry_run: false

  # Enable context caching for performance
  # Default: true
  # Improves performance by caching context for cache_ttl_seconds
  enable_caching: true

  # Cache time-to-live in seconds (0-3600)
  # Default: 300 (5 minutes)
  # Set to 0 to effectively disable caching
  cache_ttl_seconds: 300
```

---

### 2. Environment Variable Overrides

```yaml
environment_overrides:
  # AWS Configuration
  AWS_REGION: us-west-2
  AWS_PROFILE: default
  AWS_ACCOUNT_ID: "123456789012"

  # GCP Configuration
  GCLOUD_PROJECT: my-dev-project
  CLOUDSDK_CORE_PROJECT: my-dev-project

  # Azure Configuration
  AZURE_SUBSCRIPTION_ID: "00000000-0000-0000-0000-000000000000"
```

These variables are set in the CloudctlSkill session, allowing region/project switching without environment variable exports.

---

### 3. Logging Configuration (Optional)

```yaml
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: INFO

  # Log format string
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

  # Log file path (supports ~ for home directory)
  file: ~/.config/cloudctl/audit/operations.jsonl
```

---

### 4. Validation Rules (Optional)

```yaml
validation:
  # Require valid context after switching
  require_context_after_switch: true

  # Validate credentials exist before switching
  validate_credentials: true

  # Check organization exists in configuration
  check_organization_exists: true
```

---

## Example Configurations

### Development Setup

```yaml
cloudctl:
  cloudctl_path: cloudctl
  timeout_seconds: 60
  max_retries: 5
  verify_context_after_switch: true
  enable_audit_logging: true
  dry_run: false
  cache_ttl_seconds: 60

environment_overrides:
  AWS_REGION: us-east-1
  GCLOUD_PROJECT: dev-project
```

### Production Setup

```yaml
cloudctl:
  cloudctl_path: /usr/local/bin/cloudctl
  timeout_seconds: 30
  max_retries: 3
  verify_context_after_switch: true
  enable_audit_logging: true
  dry_run: false
  cache_ttl_seconds: 600

environment_overrides:
  AWS_REGION: eu-west-1
  GCLOUD_PROJECT: prod-project
```

### CI/CD Setup

```yaml
cloudctl:
  cloudctl_path: cloudctl
  timeout_seconds: 300
  max_retries: 5
  verify_context_after_switch: true
  enable_audit_logging: false
  dry_run: false
  enable_caching: false

environment_overrides:
  AWS_REGION: us-west-2
  GCLOUD_PROJECT: ci-project
```

---

## Environment Variables

You can override configuration with environment variables:

```bash
# Override timeout
export CLOUDCTL_TIMEOUT=60

# Override retries
export CLOUDCTL_RETRIES=5

# Override cloudctl path
export CLOUDCTL_PATH=/usr/local/bin/cloudctl

# Enable dry-run mode
export CLOUDCTL_DRY_RUN=true

# Disable audit logging
export CLOUDCTL_AUDIT=false

# Disable verification
export CLOUDCTL_VERIFY=false
```

---

## Configuration Precedence

When CloudctlSkill loads configuration, it uses this precedence:

1. **Environment variables** — `CLOUDCTL_*` variables (highest priority)
2. **Local config** — `./.cloudctl.yaml` (current directory)
3. **Home config** — `~/.cloudctl.yaml` (home directory)
4. **Default values** — Hardcoded in CloudctlSkill

Example: If `CLOUDCTL_TIMEOUT=60` is set in environment AND `timeout_seconds: 30` in config file, the environment variable wins (60 seconds).

---

## Security Guidelines

### ✅ DO

- Configure organizations in `.cloudctl.yaml`
- Use `environment_overrides` for non-sensitive settings
- Keep `.cloudctl.yaml` out of version control (add to `.gitignore`)
- Let cloudctl handle credential storage
- Use SSO for authentication

### ❌ DON'T

- Store credentials in `.cloudctl.yaml`
- Export AWS keys or credentials
- Hardcode API tokens in config
- Commit `.cloudctl.yaml` to git
- Store credentials in environment variables

---

## Validation

CloudctlSkill validates configuration on startup:

```yaml
cloudctl:
  # Timeout must be 1-300 seconds
  timeout_seconds: 60  # ✅ Valid

  # Retries must be 0-50
  max_retries: 5       # ✅ Valid

  # Cache TTL must be 0-3600 seconds
  cache_ttl_seconds: 300  # ✅ Valid
```

Invalid configuration will raise an error with details.

---

## Troubleshooting Configuration

### "Configuration not found"

CloudctlSkill looks for `.cloudctl.yaml` in this order:
1. Current directory (`./.cloudctl.yaml`)
2. Home directory (`~/.cloudctl.yaml`)
3. Uses defaults if neither found

**Solution**: Create one of these files:
```bash
cp .cloudctl.example.yaml ~/.cloudctl.yaml
nano ~/.cloudctl.yaml
```

### "Invalid configuration"

Configuration values don't match schema:

```yaml
# ❌ INVALID: timeout > 300
cloudctl:
  timeout_seconds: 600

# ✅ VALID
cloudctl:
  timeout_seconds: 120
```

**Solution**: Check value ranges in configuration guide above.

### "cloudctl_path not found"

CloudctlSkill can't find the cloudctl binary at the specified path.

**Solution**:
```bash
# Check if cloudctl is in PATH
which cloudctl

# Or specify full path
cloudctl:
  cloudctl_path: /usr/local/bin/cloudctl
```

### "Credentials invalid"

CloudctlSkill detected invalid credentials.

**Solution**:
```bash
# Test cloudctl directly
cloudctl status

# Re-authenticate if needed
cloudctl login
```

---

## Advanced Configuration

### Custom Timeout for Slow Networks

```yaml
cloudctl:
  timeout_seconds: 120  # 2 minutes instead of default 30 seconds
  max_retries: 5
```

### Disable Caching for Shared Environments

```yaml
cloudctl:
  enable_caching: false  # Always fetch fresh context
```

### Custom Log Location

```yaml
logging:
  file: /var/log/cloudctl/operations.jsonl
```

### Dry-Run Mode for Testing

```yaml
cloudctl:
  dry_run: true  # Commands don't execute, just simulate
```

---

## Configuration Files Reference

### Full Example ~/.cloudctl.yaml

```yaml
# CloudctlSkill Configuration
# Copy this to ~/.cloudctl.yaml or ./.cloudctl.yaml

cloudctl:
  # Path to cloudctl binary
  cloudctl_path: cloudctl

  # Timeout in seconds (1-300)
  timeout_seconds: 30

  # Retry attempts (0-50)
  max_retries: 3

  # Verify context after switching
  verify_context_after_switch: true

  # Enable audit logging
  enable_audit_logging: true

  # Dry-run mode
  dry_run: false

  # Enable caching
  enable_caching: true

  # Cache TTL in seconds (0-3600)
  cache_ttl_seconds: 300

environment_overrides:
  AWS_REGION: us-west-2
  GCLOUD_PROJECT: my-project

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: ~/.config/cloudctl/audit/operations.jsonl

validation:
  require_context_after_switch: true
  validate_credentials: true
  check_organization_exists: true
```

---

## Configuration Validation Schema

CloudctlSkill validates configuration against a JSON Schema. See `config/schema.json` for the complete specification.

---

## Best Practices

1. **Start with defaults**: Copy `.cloudctl.example.yaml` and customize
2. **Keep it DRY**: Don't repeat settings across config files
3. **Test changes**: Run `/cloudctl health` after config changes
4. **Use environment variables for CI/CD**: Easier than config files in pipelines
5. **Document your setup**: Add comments explaining custom settings
6. **Monitor logs**: Check `~/.config/cloudctl/audit/` for operation history

---

**Questions?** See `TROUBLESHOOTING.md` or `.claude/SKILL.md`
