# CloudctlSkill Troubleshooting Guide

Solutions for common CloudctlSkill issues.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Authentication Issues](#authentication-issues)
- [Context Switching Issues](#context-switching-issues)
- [Performance Issues](#performance-issues)
- [Error Messages](#error-messages)
- [Debugging Tips](#debugging-tips)

## Installation Issues

### cloudctl not installed

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

2. If not installed, install cloudctl:
   ```bash
   # macOS
   brew install cloudctl
   
   # Linux
   curl -L https://releases.example.com/cloudctl | sudo tar xz -C /usr/local/bin/
   
   # Windows
   # Download from https://releases.example.com/
   ```

3. If installed but not in PATH, set CLOUDCTL_PATH:
   ```bash
   export CLOUDCTL_PATH="/full/path/to/cloudctl"
   ```

### Wrong cloudctl version

**Error:**
```
cloudctl version mismatch
```

**Solution:**

1. Check your version:
   ```bash
   cloudctl --version
   ```

2. Check required version:
   ```bash
   grep cloudctl-skill pyproject.toml
   ```

3. Upgrade cloudctl:
   ```bash
   brew upgrade cloudctl
   # or download latest from releases
   ```

### CloudctlSkill not in PATH

**Error:**
```
ModuleNotFoundError: No module named 'cloudctl_skill'
```

**Solution:**

Install CloudctlSkill:

```bash
# From PyPI (when published)
pip install cloudctl-skill

# From source
git clone https://github.com/rhyscraig/cloudctl-skill
cd cloudctl-skill
pip install -e .
```

## Authentication Issues

### GCP authentication failed

**Error:**
```
gcloud auth login failed
could not authenticate to GCP
```

**Solution:**

1. Manually authenticate:
   ```bash
   gcloud auth login
   # Browser window will open, complete OAuth
   ```

2. Verify authentication:
   ```bash
   gcloud auth list
   gcloud auth application-default print-access-token > /dev/null
   ```

3. Try CloudctlSkill again:
   ```python
   result = await skill.login("gcp-org")
   ```

### AWS credentials expired

**Error:**
```
AWS authentication failed
Token has expired
```

**Solution:**

1. Refresh credentials:
   ```bash
   aws sso login
   # or
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   ```

2. Verify credentials:
   ```bash
   aws sts get-caller-identity
   ```

3. Let CloudctlSkill auto-refresh:
   ```python
   result = await skill.ensure_cloud_access("aws-org")
   ```

### Azure subscription not found

**Error:**
```
Azure subscription not found
Could not find subscription
```

**Solution:**

1. List available subscriptions:
   ```bash
   az account list -o table
   ```

2. Set active subscription:
   ```bash
   az account set --subscription "subscription-name"
   ```

3. Verify access:
   ```bash
   az account show
   ```

### Credentials not refreshing

**Error:**
```
Reauthentication failed
Cannot prompt during non-interactive execution
```

**Solution:**

1. Manually login through browser:
   ```bash
   gcloud auth login
   aws sso login
   az login
   ```

2. Use `ensure_cloud_access()` which auto-refreshes:
   ```python
   result = await skill.ensure_cloud_access("myorg")
   ```

3. Increase timeout to allow browser interactions:
   ```bash
   export CLOUDCTL_TIMEOUT=120
   ```

## Context Switching Issues

### Context switch timeout

**Error:**
```
Command timeout after 30s
```

**Solution:**

1. Increase timeout:
   ```bash
   export CLOUDCTL_TIMEOUT=60
   ```

2. Check network connectivity:
   ```bash
   ping cloudctl-api.example.com
   ```

3. Try manual switch:
   ```bash
   cloudctl context switch myorg
   ```

### Context switch fails silently

**Error:**
```
Context switch appeared to succeed but context didn't change
```

**Solution:**

1. Disable context caching:
   ```bash
   export CLOUDCTL_CACHE=false
   ```

2. Verify context after switch:
   ```python
   context = await skill.get_context()
   print(context)
   ```

3. Check verification is enabled:
   ```bash
   export CLOUDCTL_VERIFY=true
   ```

### Invalid organization

**Error:**
```
Organization 'myorg' not found
Available organizations: aws-prod, gcp-dev
```

**Solution:**

1. List available organizations:
   ```python
   orgs = await skill.list_organizations()
   for org in orgs:
       print(org['name'])
   ```

2. Use correct organization name:
   ```python
   result = await skill.switch_context("aws-prod")
   ```

### Region not available

**Error:**
```
Region 'invalid-region' not available
```

**Solution:**

1. List available regions:
   ```bash
   # AWS
   aws ec2 describe-regions --query 'Regions[].RegionName'
   
   # GCP
   gcloud compute regions list
   
   # Azure
   az account list-locations -o table
   ```

2. Use valid region:
   ```python
   await skill.switch_region("us-west-2")
   ```

## Performance Issues

### Slow context switches

**Issue:** Context switches take >500ms

**Solution:**

1. Enable caching:
   ```bash
   export CLOUDCTL_CACHE=true
   export CLOUDCTL_CACHE_TTL=600
   ```

2. Disable verification:
   ```bash
   export CLOUDCTL_VERIFY=false
   ```

3. Check network latency:
   ```bash
   time cloudctl context get
   ```

### High memory usage

**Issue:** CloudctlSkill using too much memory

**Solution:**

1. Disable audit logging:
   ```bash
   export CLOUDCTL_AUDIT=false
   ```

2. Clear audit logs:
   ```bash
   rm -rf ~/.config/cloudctl/audit/
   ```

3. Limit context cache:
   ```bash
   export CLOUDCTL_CACHE_TTL=60
   ```

### Too many retries

**Issue:** Operations retrying too many times

**Solution:**

1. Reduce retry count:
   ```bash
   export CLOUDCTL_RETRIES=2
   ```

2. Increase timeout:
   ```bash
   export CLOUDCTL_TIMEOUT=60
   ```

3. Check if issue is persistent:
   ```bash
   # If errors continue, it's a permanent issue
   # Reduce retries to fail faster
   export CLOUDCTL_RETRIES=1
   ```

## Error Messages

### "cloudctl not found"

**Cause:** cloudctl binary not installed or not in PATH

**Fix:**
```bash
brew install cloudctl
export CLOUDCTL_PATH="/path/to/cloudctl"
```

### "Command timeout after Xs"

**Cause:** Command took longer than configured timeout

**Fix:**
```bash
export CLOUDCTL_TIMEOUT=120  # Increase timeout
```

### "Failed to parse context"

**Cause:** Unexpected cloudctl output format

**Fix:**
```bash
cloudctl context get  # Check output format
cloudctl --version   # Verify version
```

### "Credentials not valid"

**Cause:** Stored credentials expired or invalid

**Fix:**
```bash
skill.login("myorg")  # Refresh credentials
gcloud auth login     # Re-authenticate
aws sso login         # Re-authenticate
```

### "Organization not found"

**Cause:** Organization name doesn't exist

**Fix:**
```python
orgs = await skill.list_organizations()
print([o['name'] for o in orgs])
```

### "Token expired"

**Cause:** Access token expired

**Fix:**
```python
result = await skill.ensure_cloud_access("myorg")
# Auto-refresh will handle it
```

## Debugging Tips

### Enable verbose logging

Create `.cloudctl.yaml`:

```yaml
cloudctl:
  enable_audit_logging: true
```

Check logs:
```bash
cat ~/.config/cloudctl/audit/operations_$(date +%Y%m%d).jsonl | python -m json.tool
```

### Check configuration

View loaded configuration:

```python
from cloudctl_skill.config import load_config
config = load_config()
print(f"cloudctl_path: {config.cloudctl_path}")
print(f"timeout: {config.cloudctl_timeout}s")
print(f"retries: {config.cloudctl_retries}")
```

### Test cloudctl directly

```bash
cloudctl --version
cloudctl context get
cloudctl org list
```

### Enable dry-run mode

Test without making changes:

```bash
export CLOUDCTL_DRY_RUN=true
```

Commands will output what they would do:
```
[DRY RUN] Would execute: cloudctl context switch myorg
```

### Check environment variables

```bash
env | grep CLOUDCTL_
env | grep AWS_
env | grep GCLOUD_
env | grep AZURE_
```

### Verify configuration files

```bash
# Check home directory config
cat ~/.cloudctl.yaml

# Check local config
cat ./.cloudctl.yaml

# Validate YAML syntax
python -c "import yaml; print(yaml.safe_load(open('.cloudctl.yaml')))"
```

### Monitor command execution

```bash
# Watch what cloudctl commands are being run
strace -e execve cloudctl ...

# Or use verbose logging
export CLOUDCTL_DEBUG=true
```

### Check audit logs

```bash
# View today's operations
cat ~/.config/cloudctl/audit/operations_$(date +%Y%m%d).jsonl | python -m json.tool

# Find errors
grep '"success": false' ~/.config/cloudctl/audit/operations_*.jsonl

# Count operations by type
grep '"operation"' ~/.config/cloudctl/audit/operations_*.jsonl | grep -o '"operation": "[^"]*' | sort | uniq -c
```

## Getting Help

If you're still stuck:

1. **Check the logs:**
   ```bash
   cat ~/.config/cloudctl/audit/operations_*.jsonl | tail -20 | python -m json.tool
   ```

2. **Enable dry-run and test:**
   ```bash
   export CLOUDCTL_DRY_RUN=true
   ```

3. **Check README and documentation:**
   - [README.md](../README.md)
   - [API Reference](./API.md)
   - [Architecture](./ARCHITECTURE.md)
   - [Configuration](./CONFIGURATION.md)

4. **Open an issue on GitHub:**
   - [https://github.com/rhyscraig/cloudctl-skill/issues](https://github.com/rhyscraig/cloudctl-skill/issues)
   - Include error message and configuration
   - Include output of `cloudctl --version`
   - Include `cloudctl context get` output (without secrets)

5. **Start a discussion:**
   - [https://github.com/rhyscraig/cloudctl-skill/discussions](https://github.com/rhyscraig/cloudctl-skill/discussions)

## Common Solutions Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| cloudctl not found | `brew install cloudctl` or set `CLOUDCTL_PATH` |
| Timeout error | `export CLOUDCTL_TIMEOUT=60` |
| Authentication failed | `gcloud auth login` or `aws sso login` |
| Context not switching | `export CLOUDCTL_VERIFY=true` and check logs |
| Slow performance | Enable caching: `export CLOUDCTL_CACHE=true` |
| Memory usage high | `export CLOUDCTL_AUDIT=false` |
| Credential expired | Use `ensure_cloud_access()` for auto-refresh |
| Organization not found | `skill.list_organizations()` to see available |
