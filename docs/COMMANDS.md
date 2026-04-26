# CloudctlSkill Commands Reference

Complete reference for all `/cloudctl` commands available in Claude.

## Core Commands

### context
**Get current cloud context**

```
/cloudctl context
```

Returns:
- Cloud provider (AWS, GCP, Azure)
- Organization/project name
- Account ID
- Region
- Role (if applicable)

**Example output:**
```
aws:production account=123456789012 role=terraform region=us-west-2
```

---

### list orgs
**List all configured organizations**

```
/cloudctl list orgs
```

Returns:
- All available organizations
- Cloud provider for each organization
- Whether organization is enabled

**Example output:**
```
[
  {"name": "production", "provider": "aws"},
  {"name": "staging", "provider": "aws"},
  {"name": "dev-gcp", "provider": "gcp"}
]
```

---

### switch \<org\>
**Switch to a different organization**

```
/cloudctl switch production
/cloudctl switch dev-gcp
```

Uses `cloudctl` binary's SSO mechanism - no manual credential entry needed.

**Returns:**
- New context after successful switch
- Error message if switch fails

**Note:** May require interactive SSO confirmation depending on your authentication setup.

---

## Information Commands

### health
**Run comprehensive health diagnostics**

```
/cloudctl health
```

Checks:
1. Is cloudctl installed?
2. How many organizations are configured?
3. Are credentials valid for each organization?
4. Overall system health status

**Returns:**
```json
{
  "is_healthy": true,
  "cloudctl_installed": true,
  "cloudctl_version": "4.0.0",
  "organizations_available": 3,
  "credentials_valid": {
    "production": true,
    "staging": true,
    "dev-gcp": true
  },
  "checks_passed": 5,
  "checks_failed": 0,
  "timestamp": "2026-04-26T12:00:00Z"
}
```

---

### check credentials
**Verify all credentials are valid**

```
/cloudctl check credentials
```

Tests credential validity for all configured organizations.

**Returns:**
```json
{
  "production": {"valid": true, "expires_in_seconds": 3600},
  "staging": {"valid": true, "expires_in_seconds": 3600},
  "dev-gcp": {"valid": true}
}
```

---

### token status \<org\>
**Get token status for specific organization**

```
/cloudctl token status production
/cloudctl token status dev-gcp
```

**Returns:**
- Token validity status
- Expiration time (if available)
- Last refresh time (if available)

---

## Context Management Commands

### verify credentials \<org\>
**Verify access to specific organization**

```
/cloudctl verify credentials production
```

Tests that you can authenticate to a specific organization.

**Returns:**
- true/false for credential validity
- Error message if verification fails

---

### validate switch
**Validate context switch operation**

```
/cloudctl validate switch
```

Confirms that the last context switch was successful.

**Returns:**
- Current context after last switch
- Validation status

---

### ensure access \<org\>
**Ensure access with auto-recovery**

```
/cloudctl ensure access production
```

Attempts to ensure you have access to an organization, with automatic recovery mechanisms.

**Returns:**
- Status of access verification
- Current context
- Recovery actions taken (if any)

---

## Region & Project Commands

### switch region \<region\>
**Switch AWS region**

```
/cloudctl switch region us-east-1
/cloudctl switch region eu-west-2
```

Sets `AWS_REGION` environment variable for current session.

**Valid regions:** Any AWS region code (us-east-1, eu-west-1, ap-southeast-1, etc.)

**Returns:**
- Confirmation of region switch
- New AWS_REGION value

---

### switch project \<project\>
**Switch GCP project**

```
/cloudctl switch project my-dev-project
/cloudctl switch project my-prod-project
```

Sets `GCLOUD_PROJECT` and `CLOUDSDK_CORE_PROJECT` environment variables.

**Returns:**
- Confirmation of project switch
- New GCLOUD_PROJECT value

---

## Authentication Commands

### login \<org\>
**Initiate SSO login for organization**

```
/cloudctl login production
/cloudctl login dev-gcp
```

Starts the SSO login flow for a specific organization.

**Returns:**
- Login status
- Current context after successful login
- Error message if login fails

---

## Command Groups

### Diagnostic Commands
- `context` — Get current context
- `health` — System diagnostics
- `check credentials` — Verify all credentials
- `token status` — Token status for org
- `verify credentials` — Verify org access

### Switching Commands
- `switch <org>` — Switch organization
- `switch region` — Switch AWS region
- `switch project` — Switch GCP project
- `login` — Start SSO login

### Advanced Commands
- `validate switch` — Validate last switch
- `ensure access` — Ensure access with recovery

---

## Common Usage Patterns

### Check Current Context and Verify Credentials
```
/cloudctl context
/cloudctl check credentials
/cloudctl health
```

### Switch Organizations
```
/cloudctl list orgs
/cloudctl switch production
/cloudctl context
```

### Multi-Cloud Workflow
```
# Check current context
/cloudctl context

# Switch to GCP
/cloudctl switch dev-gcp
/cloudctl context

# Switch back to AWS and change region
/cloudctl switch production
/cloudctl switch region us-east-1
/cloudctl context
```

### Verify System Health
```
/cloudctl health
/cloudctl check credentials
/cloudctl validate switch
```

---

## Error Messages & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "No active context found" | No cloudctl credentials configured | `cloudctl login` |
| "Organization not found" | Org name doesn't match config | `/cloudctl list orgs` to see valid names |
| "Authentication failed" | Can't access organization | `cloudctl status` and `cloudctl switch <org>` |
| "cloudctl not found" | cloudctl binary not installed | Install cloudctl for your cloud provider |
| "Invalid region" | Region code is incorrect | Use valid AWS region code |
| "Invalid project" | Project name is incorrect | Use valid GCP project ID |

---

## Tips & Best Practices

1. **Always check context before operations**: `/cloudctl context`
2. **Run health check regularly**: `/cloudctl health`
3. **Verify credentials before long operations**: `/cloudctl check credentials`
4. **List orgs if unsure of names**: `/cloudctl list orgs`
5. **Use SSO for login**: `/cloudctl login <org>` instead of manual tokens
6. **Validate after switching**: `/cloudctl context` after `/cloudctl switch`

---

## Command Syntax Notes

- All commands are lowercase
- Organization/project names are case-sensitive
- Region codes use format: `region-direction-number` (e.g., `us-west-2`)
- Spaces in commands are single spaces only
- No quotes needed for org/region names unless they contain spaces
