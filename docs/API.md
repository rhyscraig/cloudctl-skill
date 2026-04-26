# CloudctlSkill API Reference

Complete API documentation for CloudctlSkill methods and models.

## Table of Contents

- [CloudctlSkill Class](#cloudctlskill-class)
- [Core Methods](#core-methods)
- [Data Models](#data-models)
- [Configuration](#configuration)
- [Error Handling](#error-handling)

## CloudctlSkill Class

Main class for enterprise cloud context management.

```python
from cloudctl_skill import CloudctlSkill

skill = CloudctlSkill()
result = await skill.get_context()
```

### Constructor

```python
CloudctlSkill(config: Optional[SkillConfig] = None)
```

**Parameters:**
- `config` (SkillConfig, optional): Configuration object. If None, loads from environment/files.

## Core Methods

### get_context()

Get current cloud context.

```python
async def get_context() -> CloudContext
```

**Returns:** `CloudContext` — Current cloud context state

**Raises:** `RuntimeError` — If unable to determine context

**Example:**
```python
context = await skill.get_context()
print(context.organization)  # "myorg"
print(context.provider)      # CloudProvider.AWS
print(context.account_id)    # "123456789"
print(context.region)        # "us-west-2"
```

### switch_context()

Switch cloud context to specified organization.

```python
async def switch_context(organization: str) -> CommandResult
```

**Parameters:**
- `organization` (str): Organization name to switch to

**Returns:** `CommandResult` — Switch operation status

**Raises:**
- `ValueError` — If organization is empty
- `RuntimeError` — If context switch fails

**Example:**
```python
result = await skill.switch_context("production-org")
if result.success:
    print(f"✅ Switched to {result.output}")
else:
    print(f"❌ {result.error}")
    print(f"💡 {result.fix}")
```

### switch_region()

Switch cloud region.

```python
async def switch_region(region: str) -> CommandResult
```

**Parameters:**
- `region` (str): Region identifier (e.g., 'us-west-2', 'europe-west1')

**Returns:** `CommandResult` — Operation status

**Example:**
```python
await skill.switch_region("eu-west-1")
```

### switch_project()

Switch GCP project.

```python
async def switch_project(project_id: str) -> CommandResult
```

**Parameters:**
- `project_id` (str): GCP project ID

**Returns:** `CommandResult` — Operation status

### list_organizations()

List all available organizations.

```python
async def list_organizations() -> list[dict[str, str]]
```

**Returns:** List of org dicts with 'name' and 'provider' keys

**Raises:** `RuntimeError` — If unable to list organizations

**Example:**
```python
orgs = await skill.list_organizations()
for org in orgs:
    print(f"{org['name']} ({org['provider']})")
```

### verify_credentials()

Verify credentials exist and are valid for organization.

```python
async def verify_credentials(organization: str) -> bool
```

**Parameters:**
- `organization` (str): Organization name

**Returns:** True if credentials valid, False otherwise

**Example:**
```python
is_valid = await skill.verify_credentials("myorg")
if is_valid:
    print("✅ Credentials are valid")
```

### login()

Login to organization and refresh credentials.

```python
async def login(organization: str) -> CommandResult
```

**Parameters:**
- `organization` (str): Organization name to login to

**Returns:** `CommandResult` — Login status

**Raises:** `ValueError` — If organization is empty

**Example:**
```python
result = await skill.login("myorg")
if result.success:
    print("✅ Logged in successfully")
```

### get_token_status()

Get token status for organization.

```python
async def get_token_status(organization: str) -> TokenStatus
```

**Parameters:**
- `organization` (str): Organization name

**Returns:** `TokenStatus` — Token validity and expiration info

**Raises:** `RuntimeError` — If unable to get token status

**Example:**
```python
status = await skill.get_token_status("myorg")
print(f"Valid: {status.valid}")
print(f"Expires in: {status.expires_in_seconds}s")
```

### check_all_credentials()

Check credentials across all organizations.

```python
async def check_all_credentials() -> dict[str, dict[str, Any]]
```

**Returns:** Dict mapping org name to credential status

**Example:**
```python
creds = await skill.check_all_credentials()
for org, status in creds.items():
    print(f"{org}: {status['valid']}")
```

### health_check()

Perform comprehensive health check.

```python
async def health_check() -> HealthCheckResult
```

**Returns:** `HealthCheckResult` — Detailed health status

**Example:**
```python
health = await skill.health_check()
print(f"System healthy: {health.is_healthy}")
print(f"cloudctl installed: {health.cloudctl_installed}")
print(f"Organizations: {health.organizations_available}")
```

### ensure_cloud_access()

Ensure access to cloud organization with auto-recovery.

```python
async def ensure_cloud_access(organization: str) -> dict[str, Any]
```

**Parameters:**
- `organization` (str): Organization name to access

**Returns:** Dict with keys:
- `success` (bool): Whether access is confirmed
- `context` (str): Current context string
- `error` (str): Error message if failed
- `fix` (str): Suggested remediation
- `auto_refreshed` (bool): Whether token was auto-refreshed

**Example:**
```python
result = await skill.ensure_cloud_access("myorg")
if result["success"]:
    print(f"✅ Ready: {result['context']}")
else:
    print(f"❌ {result['error']}")
    print(f"💡 {result['fix']}")
```

### validate_switch()

Validate that context switch is working.

```python
async def validate_switch() -> bool
```

**Returns:** True if context switching works

## Data Models

### CloudContext

Current cloud context state.

```python
class CloudContext:
    provider: CloudProvider
    organization: str
    account_id: Optional[str]
    region: Optional[str]
    role: Optional[str]
    credentials_valid: bool
    last_updated: datetime
```

### CloudProvider

Enum of supported cloud providers.

```python
class CloudProvider(str, Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
```

### CommandResult

Result of a cloud command execution.

```python
class CommandResult:
    success: bool
    status: CommandStatus
    output: str
    error: Optional[str]
    fix: Optional[str]
    stderr: Optional[str]
    exit_code: int
```

### CommandStatus

Status of a command execution.

```python
class CommandStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
```

### TokenStatus

Token validity status and expiration.

```python
class TokenStatus:
    valid: bool
    expires_in_seconds: Optional[int]
    expired_at: Optional[datetime]
    refreshed_at: Optional[datetime]
```

### HealthCheckResult

Result of a health check.

```python
class HealthCheckResult:
    is_healthy: bool
    cloudctl_installed: bool
    cloudctl_version: Optional[str]
    organizations_available: int
    credentials_valid: dict[str, bool]
    checks_passed: int
    checks_failed: int
    timestamp: datetime
```

### SkillConfig

CloudctlSkill configuration.

```python
class SkillConfig:
    cloudctl_path: str = "cloudctl"
    cloudctl_timeout: int = 30
    cloudctl_retries: int = 3
    verify_context_after_switch: bool = True
    enable_audit_logging: bool = True
    dry_run: bool = False
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
```

## Configuration

### Environment Variables

```bash
CLOUDCTL_PATH="/usr/local/bin/cloudctl"   # Path to cloudctl binary
CLOUDCTL_TIMEOUT="30"                     # Command timeout (1-300s)
CLOUDCTL_RETRIES="3"                      # Max retries (0-10)
CLOUDCTL_VERIFY="true"                    # Verify context after switch
CLOUDCTL_AUDIT="true"                     # Enable audit logging
CLOUDCTL_DRY_RUN="false"                  # Dry-run mode
```

### Configuration Files

Create `.cloudctl.yaml` in home directory or current directory:

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
```

## Error Handling

### Exception Types

```python
ValueError          # Invalid input parameters
RuntimeError        # Operation failed
FileNotFoundError   # cloudctl not installed
asyncio.TimeoutError # Command timeout
```

### Error Recovery

CloudctlSkill automatically handles many errors:

- **Token expiration** — Auto-refresh on `ensure_cloud_access()`
- **Transient errors** — Auto-retry with exponential backoff
- **Context errors** — Validation and helpful messages
- **Timeout** — Configurable timeout with clear message

### Example Error Handling

```python
try:
    result = await skill.ensure_cloud_access("myorg")
    if not result["success"]:
        print(f"Error: {result['error']}")
        print(f"Fix: {result['fix']}")
except ValueError as e:
    print(f"Invalid input: {e}")
except RuntimeError as e:
    print(f"Operation failed: {e}")
```

## Audit Logging

CloudctlSkill writes audit logs to:

```
~/.config/cloudctl/audit/operations_YYYYMMDD.jsonl
```

Format:
```json
{
  "timestamp": "2026-04-26T10:30:45.123456",
  "operation": "switch_context",
  "context_before": {...},
  "context_after": {...},
  "user": "craig",
  "success": true,
  "duration_ms": 125.34
}
```

View logs:
```bash
cat ~/.config/cloudctl/audit/operations_20260426.jsonl | python -m json.tool
```
