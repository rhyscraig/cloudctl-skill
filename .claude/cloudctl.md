# CloudctlSkill — Complete Guide for Claude

This document explains how CloudctlSkill works and how to use it effectively without any manual credential management.

## What CloudctlSkill Does

CloudctlSkill is a Claude interface to the `cloudctl` binary. It allows you to:
- Switch between cloud organizations and accounts
- Manage multi-cloud contexts (AWS, GCP, Azure)
- Validate credentials across all clouds
- Manage SSO authentication automatically
- All without manually exporting credentials or managing AWS keys

**Key Principle**: The `cloudctl` binary handles all authentication (SSO, credential refresh, token management). CloudctlSkill just provides Claude commands to use it.

## Installation

### 1. Install the Python Package

Already done! CloudctlSkill v1.2.0 is installed:
```bash
pip show cloudctl-skill
```

### 2. Ensure cloudctl Binary is Installed

CloudctlSkill requires the `cloudctl` binary:
```bash
# Check if cloudctl is installed
cloudctl version

# If not installed, install from your cloud provider
# AWS: aws cli is cloudctl
# GCP: gcloud is cloudctl  
# Or: https://docs.cloudctl.io/installation
```

### 3. Skill is Already Enabled in Claude

The `/cloudctl` command is registered and ready:
- Manifest: `~/.claude/skills/cloudctl.json`
- Configuration: `~/.claude/skills/cloudctl-config.json`
- Just start typing: `/cloudctl`

## Using CloudctlSkill — No Credentials Required

### Basic Commands

```
/cloudctl context              Get current authenticated context
/cloudctl list orgs            List all organizations you have access to
/cloudctl switch prod          Switch to 'prod' organization
/cloudctl health               Verify everything is working
/cloudctl check credentials    Check token status across all clouds
```

### How It Works (The Simple Version)

1. You have `cloudctl` installed and authenticated (happens once, via SSO)
2. You type `/cloudctl` commands in Claude
3. CloudctlSkill calls the `cloudctl` binary
4. `cloudctl` uses your existing authentication (cached SSO tokens)
5. No credentials ever touched, no exports needed, no AWS keys in shell

**That's it. No environment variables. No credential management. No AWS SSO prompts.**

## Configuring Organizations (Important!)

CloudctlSkill and `cloudctl` read from your local cloudctl config file, NOT environment variables.

### Setup Your Local Config

```bash
# 1. Copy the example config
cp /tmp/cloudctl-skill/.cloudctl.example.yaml ~/.cloudctl.yaml

# 2. Edit it with your organizations
nano ~/.cloudctl.yaml
```

### Example ~/.cloudctl.yaml

```yaml
# LOCAL CONFIGURATION - Never commit this file!
# This file defines your cloud contexts and preferences

cloudctl:
  timeout_seconds: 30
  max_retries: 3
  verify_context_after_switch: true
  enable_audit_logging: true

# Define your organizations
organizations:
  prod:
    provider: aws
    account_name: production-account
    role: DevOps
    region: us-west-2
  
  staging:
    provider: aws
    account_name: staging-account
    role: Developer
    region: us-west-2
  
  dev:
    provider: gcp
    project_id: my-dev-project
    region: us-central1

# Environment variable overrides (don't put credentials here!)
environment_overrides:
  AWS_REGION: us-west-2
  GCLOUD_PROJECT: my-dev-project
  # Credentials come from SSO via cloudctl, NEVER here
```

### How Organizations Are Used

```
/cloudctl list orgs            ← Shows all organizations from ~/.cloudctl.yaml
/cloudctl switch prod          ← Switches to 'prod' org via cloudctl
/cloudctl context              ← Confirms you're authenticated to 'prod'
```

That's it. All context switching happens via cloudctl's authentication system.

## NO Environment Variables Needed

**Do NOT do this:**
```bash
export AWS_ACCESS_KEY_ID="AKIA..."  ❌ DON'T
export AWS_SECRET_ACCESS_KEY="..."  ❌ DON'T
```

**Instead:**
- Let `cloudctl` handle authentication (it uses SSO)
- Configure your organizations in `~/.cloudctl.yaml`
- Use `/cloudctl` commands in Claude
- ✅ That's all you need

## NO AWS SSO Needed (For Most Operations)

CloudctlSkill works with whatever authentication method `cloudctl` supports:
- AWS SSO ✅ (most common)
- AWS IAM users ✅
- GCP service accounts ✅
- Azure identities ✅
- Any method cloudctl supports ✅

If you don't have SSO:
- Configure `cloudctl` with your auth method once
- CloudctlSkill uses it automatically
- No reconfiguration needed in Claude

## Security Model

CloudctlSkill uses **defense-in-depth security**:

✅ **No credentials stored in code** — Architecture prevents it
✅ **No credentials stored in config files** — Only org definitions
✅ **No credentials in environment** — Not needed
✅ **Credentials managed by cloudctl** — Via SSO or provider auth
✅ **Pre-commit hooks prevent secrets** — Can't accidentally commit credentials
✅ **Audit logging** — JSONL compliance logs for all operations

This is why you DON'T need to manually export credentials. The system is designed to never touch them.

## Complete Workflow

### Step 1: One-Time Setup

```bash
# Configure cloudctl with your cloud provider's SSO
cloudctl setup
# or
cloudctl auth login

# Create ~/.cloudctl.yaml with your organizations
cp /tmp/cloudctl-skill/.cloudctl.example.yaml ~/.cloudctl.yaml
nano ~/.cloudctl.yaml
```

### Step 2: Verify It Works

```bash
# Test cloudctl directly
cloudctl context          # Shows current context
cloudctl list-orgs        # Lists all orgs

# Test CloudctlSkill in Claude
/cloudctl context         # Same thing, via Claude
/cloudctl list orgs       # Same thing, via Claude
```

### Step 3: Use It

```
/cloudctl switch prod
/cloudctl health
/cloudctl check credentials
/cloudctl switch staging
# ... switch between orgs instantly via SSO
```

**That's the entire workflow. No credential management required.**

## What CloudctlSkill Can Do

Once configured:

| Command | What It Does |
|---------|------------|
| `/cloudctl context` | Show current org, account, role, region |
| `/cloudctl switch <org>` | Switch to another organization (uses SSO) |
| `/cloudctl list orgs` | List all configured organizations |
| `/cloudctl check credentials` | Verify tokens are valid |
| `/cloudctl health` | Full system diagnostics |
| `/cloudctl region <region>` | Switch AWS region |
| `/cloudctl project <project>` | Switch GCP project |
| `/cloudctl ensure access <org>` | Ensure you can access an org (with auto-recovery) |

All use `cloudctl` backend authentication — no manual credentials.

## Troubleshooting

### "/cloudctl: command not found"

Make sure cloudctl binary is installed:
```bash
which cloudctl
cloudctl version
```

### "Organization not found"

Check your `~/.cloudctl.yaml` — the org name must match exactly:
```bash
# In ~/.cloudctl.yaml
organizations:
  prod:  # ← Organization name
    ...

# Then use:
/cloudctl switch prod  # ← Must match
```

### "Authentication failed"

CloudctlSkill couldn't authenticate to the org. This means:
1. `cloudctl` doesn't have valid credentials for that org
2. Your SSO session expired
3. You don't have access to that org

**Solution**: Authenticate with cloudctl directly first:
```bash
cloudctl auth login
cloudctl switch prod
```

Once that works, `/cloudctl` will work.

## Security: Why This Design

CloudctlSkill is designed to be **secret-safe**:

❌ **OLD WAY (Don't do this)**:
```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
# Now credentials are in your shell history!
```

✅ **CloudctlSkill WAY (Do this)**:
```bash
# credentials managed by cloudctl/SSO
# never touch shell or config files
/cloudctl context
```

Benefits:
- No credentials in shell history
- No credentials in environment
- No credentials in config files
- No credentials in code
- No credentials in logs
- No risk of accidental leakage

CloudctlSkill eliminates the entire category of "credential exposure" bugs.

## Documentation

- **README.md** — Feature overview
- **SECURITY.md** — Detailed security policy
- **docs/API.md** — All methods and parameters
- **docs/ARCHITECTURE.md** — Design principles
- **examples/safe_configuration.py** — Safe patterns
- **INSTALLATION.md** — Setup guide

## Quick Reference

```
One-time setup:
  cloudctl setup
  cp .cloudctl.example.yaml ~/.cloudctl.yaml
  nano ~/.cloudctl.yaml

Daily usage:
  /cloudctl context              ← Where am I?
  /cloudctl list orgs            ← What orgs can I access?
  /cloudctl switch prod          ← Switch to prod
  /cloudctl check credentials    ← Are tokens valid?

That's it!
```

## Summary

**CloudctlSkill is designed to work WITHOUT:**
- ❌ Environment variable exports
- ❌ AWS credential files
- ❌ Manual credential management
- ❌ SSO setup in Claude
- ❌ Any credential handling by you

**Instead:**
- ✅ Configure `cloudctl` once (your cloud provider's way)
- ✅ Define orgs in `~/.cloudctl.yaml`
- ✅ Use `/cloudctl` commands
- ✅ CloudctlSkill handles everything else
- ✅ Credentials managed by cloudctl/SSO/provider

This is production-grade, enterprise-safe, and designed to prevent the security mistakes that plague manual credential management.

**Just use `/cloudctl` and it works. That's the whole point.** ✨
