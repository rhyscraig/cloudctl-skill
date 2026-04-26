# CloudctlSkill Configuration Guide

Complete configuration reference for CloudctlSkill.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration Precedence](#configuration-precedence)
- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Settings Reference](#settings-reference)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Minimal Setup

```bash
# cloudctl is in PATH
cloudctl --version
```

That's it! CloudctlSkill will auto-discover cloudctl.

### With Custom cloudctl Path

```bash
export CLOUDCTL_PATH=/usr/local/bin/cloudctl
```

### With Configuration File

Create `.cloudctl.yaml` in your home directory:

```yaml
cloudctl:
  timeout_seconds: 30
  max_retries: 3
```

## Configuration Precedence

Settings are loaded in this order (highest to lowest priority):

1. **Environment Variables** (`CLOUDCTL_*`)
2. **Local Config** (`./.cloudctl.yaml` in current directory)
3. **Home Config** (`~/.cloudctl.yaml` in home directory)
4. **Default Values** (SkillConfig defaults)

**Example:** If you set `CLOUDCTL_TIMEOUT=60` and also have `timeout_seconds: 30` in `~/.cloudctl.yaml`, the environment variable wins (60 seconds).

## Environment Variables

### CLOUDCTL_PATH

Path to cloudctl binary.

```bash
export CLOUDCTL_PATH="/usr/local/bin/cloudctl"
export CLOUDCTL_PATH="$HOME/bin/cloudctl"
```

**Default:** `cloudctl` (must be in PATH)

### CLOUDCTL_TIMEOUT

Command timeout in seconds.

```bash
export CLOUDCTL_TIMEOUT=30
export CLOUDCTL_TIMEOUT=60
```

**Valid range:** 1-300 seconds  
**Default:** 30 seconds

### CLOUDCTL_RETRIES

Maximum number of retry attempts for transient errors.

```bash
export CLOUDCTL_RETRIES=3
export CLOUDCTL_RETRIES=5
```

**Valid range:** 0-10  
**Default:** 3 attempts

### CLOUDCTL_VERIFY

Verify context after context switch.

```bash
export CLOUDCTL_VERIFY=true
export CLOUDCTL_VERIFY=false
```

**Valid values:** `true`, `false`, `1`, `0`, `yes`, `no`  
**Default:** `true`

### CLOUDCTL_AUDIT

Enable audit logging to `~/.config/cloudctl/audit/`.

```bash
export CLOUDCTL_AUDIT=true
export CLOUDCTL_AUDIT=false
```

**Valid values:** `true`, `false`, `1`, `0`, `yes`, `no`  
**Default:** `true`

### CLOUDCTL_DRY_RUN

Enable dry-run mode (don't execute commands).

```bash
export CLOUDCTL_DRY_RUN=true
export CLOUDCTL_DRY_RUN=false
```

**Valid values:** `true`, `false`, `1`, `0`, `yes`, `no`  
**Default:** `false`

**Use case:** Test configuration without making changes

### CLOUDCTL_CACHE

Enable context caching.

```bash
export CLOUDCTL_CACHE=true
export CLOUDCTL_CACHE=false
```

**Valid values:** `true`, `false`, `1`, `0`, `yes`, `no`  
**Default:** `true`

### CLOUDCTL_CACHE_TTL

Cache time-to-live in seconds.

```bash
export CLOUDCTL_CACHE_TTL=300
export CLOUDCTL_CACHE_TTL=600
```

**Valid range:** 0-3600 seconds  
**Default:** 300 seconds (5 minutes)

## Configuration Files

### File Locations

CloudctlSkill looks for configuration in:

1. **Current directory** (highest priority)
   ```
   ./.cloudctl.yaml
   ```

2. **Home directory**
   ```
   ~/.cloudctl.yaml
   ```

### File Format

YAML format with two main sections:

```yaml
# cloudctl settings
cloudctl:
  timeout_seconds: 30
  max_retries: 3
  verify_context_after_switch: true
  enable_audit_logging: true
  dry_run: false
  enable_caching: true
  cache_ttl_seconds: 300

# environment variable overrides
environment_overrides:
  AWS_REGION: "us-west-2"
  AWS_PROFILE: "default"
  GCLOUD_PROJECT: "my-project"
  AZURE_SUBSCRIPTION_ID: "..."
```

### Example: .cloudctl.yaml

```yaml
# Basic configuration
cloudctl:
  timeout_seconds: 30
  max_retries: 3

# Set environment variables for cloud CLIs
environment_overrides:
  AWS_REGION: "eu-west-1"
  GCLOUD_PROJECT: "production"
```

### Example: Development Setup

```yaml
# Development configuration
cloudctl:
  timeout_seconds: 60
  max_retries: 5
  verify_context_after_switch: true
  enable_audit_logging: true
  dry_run: false
  cache_ttl_seconds: 60  # Shorter cache for active development

environment_overrides:
  AWS_REGION: "us-east-1"
  GCLOUD_PROJECT: "dev-project"
```

### Example: CI/CD Setup

```yaml
# CI/CD configuration
cloudctl:
  timeout_seconds: 300
  max_retries: 5
  verify_context_after_switch: true
  enable_audit_logging: true
  dry_run: false
  enable_caching: false  # Disable caching in CI/CD

environment_overrides:
  AWS_REGION: "us-west-2"
```

## Settings Reference

### cloudctl.timeout_seconds

Command execution timeout.

| Setting | Type | Range | Default |
|---------|------|-------|---------|
| `timeout_seconds` | integer | 1-300 | 30 |

**Behavior:**
- Commands exceeding timeout are killed
- Returns helpful timeout error
- Consider network latency and cloud API response times

**When to increase:**
- Slow network connections
- Large organizational lists
- Complex context switches

### cloudctl.max_retries

Retry attempts for transient errors.

| Setting | Type | Range | Default |
|---------|------|-------|---------|
| `max_retries` | integer | 0-10 | 3 |

**Retry strategy:**
- Exponential backoff: 1s, 2s, 4s, 8s...
- Only for transient errors (timeout, temporary unavailable)
- Permanent errors fail immediately

### cloudctl.verify_context_after_switch

Verify context after switching.

| Setting | Type | Default |
|---------|------|---------|
| `verify_context_after_switch` | boolean | true |

**Behavior:**
- If enabled: Queries cloudctl to verify switch succeeded
- If disabled: Trusts cloudctl output
- Adds ~50ms to context switches

### cloudctl.enable_audit_logging

Enable operation audit logging.

| Setting | Type | Default |
|---------|------|---------|
| `enable_audit_logging` | boolean | true |

**Output:** `~/.config/cloudctl/audit/operations_YYYYMMDD.jsonl`

### cloudctl.dry_run

Enable dry-run mode.

| Setting | Type | Default |
|---------|------|---------|
| `dry_run` | boolean | false |

**Behavior:**
- No actual commands are executed
- Commands return success with dry-run notice
- Useful for testing configuration

### cloudctl.enable_caching

Enable context caching.

| Setting | Type | Default |
|---------|------|---------|
| `enable_caching` | boolean | true |

**Behavior:**
- Caches context for `cache_ttl_seconds`
- Subsequent `get_context()` calls return cached value
- Cache invalidated on context switch

### cloudctl.cache_ttl_seconds

Cache time-to-live.

| Setting | Type | Range | Default |
|---------|------|-------|---------|
| `cache_ttl_seconds` | integer | 0-3600 | 300 |

**When to adjust:**
- **Decrease:** For active multi-cloud work (short cache)
- **Increase:** For stable contexts (better performance)
- **Zero:** Disable caching effectively

## Examples

### Example 1: Basic Setup

No configuration needed:

```python
from cloudctl_skill import CloudctlSkill

skill = CloudctlSkill()
context = await skill.get_context()
```

### Example 2: Custom Timeout

```bash
export CLOUDCTL_TIMEOUT=60
```

Or in `.cloudctl.yaml`:

```yaml
cloudctl:
  timeout_seconds: 60
```

### Example 3: Dry-Run Mode

Test configuration without changes:

```bash
export CLOUDCTL_DRY_RUN=true
```

Commands will return:
```
[DRY RUN] Would execute: cloudctl context switch myorg
```

### Example 4: Disable Caching

For active development:

```yaml
cloudctl:
  enable_caching: false
```

Or:

```bash
export CLOUDCTL_CACHE=false
```

### Example 5: CI/CD Setup

```yaml
# .cloudctl.yaml for CI/CD
cloudctl:
  timeout_seconds: 300
  max_retries: 5
  verify_context_after_switch: true
  enable_audit_logging: false  # Optional in CI/CD
  dry_run: false
  enable_caching: false

environment_overrides:
  AWS_REGION: "us-west-2"
  CI: "true"
```

## Troubleshooting

### cloudctl Not Found

**Error:**
```
cloudctl not found at cloudctl
Fix: Install cloudctl or set CLOUDCTL_PATH
```

**Solution:**

1. Check cloudctl is installed:
   ```bash
   which cloudctl
   cloudctl --version
   ```

2. Set CLOUDCTL_PATH:
   ```bash
   export CLOUDCTL_PATH=/full/path/to/cloudctl
   ```

### Timeout Errors

**Error:**
```
Command timeout after 30s
Fix: Increase CLOUDCTL_TIMEOUT or check network connection
```

**Solution:**

Increase timeout:
```bash
export CLOUDCTL_TIMEOUT=60
```

Or in `.cloudctl.yaml`:
```yaml
cloudctl:
  timeout_seconds: 60
```

### Invalid Configuration

**Error:**
```
CLOUDCTL_TIMEOUT must be an integer
```

**Solution:**

```bash
# Wrong
export CLOUDCTL_TIMEOUT="30s"

# Correct
export CLOUDCTL_TIMEOUT=30
```

### Context Cache Issues

If you're seeing stale context:

1. Disable caching temporarily:
   ```bash
   export CLOUDCTL_CACHE=false
   ```

2. Or reduce TTL:
   ```bash
   export CLOUDCTL_CACHE_TTL=30
   ```

### Configuration Not Loading

1. Check file exists:
   ```bash
   cat ~/.cloudctl.yaml
   ```

2. Check YAML syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('.cloudctl.yaml'))"
   ```

3. Verify precedence (environment vars override files):
   ```bash
   env | grep CLOUDCTL_
   ```

## Best Practices

1. **Use configuration files** for shared settings
2. **Use environment variables** for sensitive/temporary settings
3. **Enable audit logging** for compliance/debugging
4. **Adjust timeout** based on your network and cloud API latency
5. **Use dry-run** to test configuration changes
6. **Keep `.cloudctl.yaml` out of git** (add to `.gitignore`)
7. **Document custom settings** for your team
