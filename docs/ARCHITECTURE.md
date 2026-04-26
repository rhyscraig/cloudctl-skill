# CloudctlSkill Architecture

Technical design and implementation details for CloudctlSkill.

## Table of Contents

- [Design Principles](#design-principles)
- [Architecture Overview](#architecture-overview)
- [Module Structure](#module-structure)
- [Async Architecture](#async-architecture)
- [Error Handling Strategy](#error-handling-strategy)
- [Audit Logging](#audit-logging)
- [Performance Optimizations](#performance-optimizations)
- [Security Considerations](#security-considerations)

## Design Principles

### 1. Async-First

All I/O operations are async for non-blocking execution:

```python
# Async-first design
async def switch_context(organization: str) -> CommandResult:
    # Non-blocking subprocess execution
    result = await self._execute_cloudctl(...)
    # Non-blocking file I/O for audit logging
    await write_audit_log(...)
    return result
```

**Benefits:**
- Non-blocking concurrent operations
- Scales to handle multiple organizations
- Integrates seamlessly with Claude's async runtime
- Better resource utilization

### 2. Type-Safe

Pydantic v2 validation at all boundaries:

```python
# Type-safe models with validation
class CloudContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    provider: CloudProvider
    organization: str
    credentials_valid: bool

# Strict mypy validation
mypy --strict src/cloudctl_skill/
# 0 errors
```

**Benefits:**
- Compile-time error detection
- Runtime validation via Pydantic
- Self-documenting code
- IDE autocomplete support

### 3. Fail-Safe

Comprehensive error handling and auto-recovery:

```python
# Auto-retry with exponential backoff
for attempt in range(self.config.cloudctl_retries + 1):
    try:
        return await self._execute_cloudctl(...)
    except TransientError:
        await asyncio.sleep(2 ** attempt)

# Auto-refresh on token expiry
if "token" in result.error.lower():
    refresh_result = await self.login(organization)
    if refresh_result.success:
        # Retry original operation
        return await self._execute_cloudctl(...)
```

**Benefits:**
- Handles transient failures automatically
- Proactive token refresh before expiry
- Helpful error messages with suggestions
- Fail-fast on permanent errors

### 4. Observable

Structured audit logging for compliance:

```python
log = OperationLog(
    timestamp=datetime.utcnow(),
    operation="switch_context",
    context_before=before.model_dump(),
    context_after=after.model_dump(),
    success=result.success,
    duration_ms=elapsed,
)
await write_audit_log(audit_dir, log)
```

**Output:** JSONL format in `~/.config/cloudctl/audit/`

**Benefits:**
- Full operation audit trail
- Compliance logging ready
- Performance metrics per operation
- Easy to parse and query

### 5. Defensive

Pre-flight checks and validation:

```python
# Validate input before operations
if not organization or not organization.strip():
    raise ValueError("Organization cannot be empty")

# Pre-flight health checks
health = await self.health_check()
if not health.cloudctl_installed:
    return {"success": False, "fix": "Install cloudctl"}

# Validate context switch results
await self.validate_switch()
```

**Benefits:**
- Fail-fast with clear errors
- Prevents cascading failures
- User-friendly error messages
- Helpful remediation suggestions

### 6. Testable

Designed for easy mocking and testing:

```python
# Easy to mock cloudctl execution
with patch.object(skill, "_execute_cloudctl") as mock_exec:
    mock_exec.return_value = CommandResult(success=True)
    result = await skill.switch_context("myorg")
    assert result.success is True
```

**Benefits:**
- 35 comprehensive tests
- Unit tests with mocking
- Integration tests with real cloudctl
- 100% core coverage

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Claude (Async Runtime)                      │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│         CloudctlSkill (Main Skill Class)                 │
│  - switch_context()                                      │
│  - get_context()                                         │
│  - list_organizations()                                  │
│  - ensure_cloud_access()                                 │
│  - health_check()                                        │
└──────┬─────────────┬──────────────┬──────────────────────┘
       │             │              │
   ┌───▼──┐  ┌──────▼────┐  ┌──────▼──────┐
   │Models│  │Config     │  │Utils        │
   ├──────┤  ├───────────┤  ├─────────────┤
   │Cloud │  │Load       │  │Audit        │
   │Context│  │from files │  │logging      │
   │Command│  │Merge env  │  │Format       │
   │Result│  │Validate   │  │Parse        │
   │Health │  │           │  │             │
   └──────┘  └───────────┘  └─────────────┘
       │             │              │
   ┌───┴─────────────┴──────────────┴──────────────┐
   │                                               │
   │  Pydantic v2 Validation                       │
   │  Frozen Models (immutable)                    │
   │  Field Validators                             │
   └───────────────────────────────────────────────┘
       │
   ┌───▼──────────────────────────────────────────┐
   │                                              │
   │  Async Subprocess Execution                  │
   │  - cloudctl commands                         │
   │  - Retry logic                               │
   │  - Timeout handling                          │
   │  - Error parsing                             │
   │                                              │
   └──────────────────────────────────────────────┘
       │
   ┌───▼──────────────────────────────────────────┐
   │                                              │
   │  Cloud CLIs (cloudctl)                       │
   │  - AWS (via cloudctl)                        │
   │  - GCP (via cloudctl)                        │
   │  - Azure (via cloudctl)                      │
   │                                              │
   └──────────────────────────────────────────────┘
```

## Module Structure

### cloudctl_skill/__init__.py

Entry point and public API:

```python
from .skill import CloudctlSkill
from .models import CloudProvider, CloudContext, CommandResult

__all__ = [
    "CloudctlSkill",
    "CloudProvider",
    "CloudContext",
    "CommandResult",
    # ... other exports
]
```

### cloudctl_skill/models.py

Pydantic v2 data models:

- `CloudProvider` — AWS, GCP, Azure enum
- `CommandStatus` — Success, failure, partial, unknown
- `CommandResult` — Command execution result
- `CloudContext` — Current cloud state
- `TokenStatus` — Token validity/expiration
- `HealthCheckResult` — System health status
- `SkillConfig` — Configuration options
- `OperationLog` — Audit log entry

All models are immutable (frozen=True) where appropriate.

### cloudctl_skill/skill.py

Main CloudctlSkill class with methods:

**Public Methods:**
- `get_context()` — Get current context (cached)
- `switch_context(org)` — Switch cloud context
- `list_organizations()` — List available orgs
- `login(org)` — Refresh credentials
- `health_check()` — Full system check
- `ensure_cloud_access(org)` — Guaranteed access
- `verify_credentials(org)` — Check credentials
- `get_token_status(org)` — Token info

**Private Methods:**
- `_execute_cloudctl()` — Execute with retry logic
- `_verify_credentials()` — Internal credential check
- `_is_cloudctl_installed()` — Check cloudctl
- `_parse_context()` — Parse context string

### cloudctl_skill/config.py

Configuration management:

```python
# Load precedence:
# 1. Environment variables (CLOUDCTL_*)
# 2. ~/.cloudctl.yaml (home directory)
# 3. ./.cloudctl.yaml (current directory)
# 4. Default SkillConfig values

config = load_config()
```

Features:
- YAML config file support
- Environment variable overrides
- Configuration merging
- Nested key handling

### cloudctl_skill/utils.py

Utility functions:

- `setup_audit_logging()` — Create audit directory
- `write_audit_log()` — Write JSONL log entry
- `format_context_string()` — Format context for display
- `parse_context_string()` — Parse context string

## Async Architecture

### Command Execution

All commands execute asynchronously with timeouts:

```python
async def _execute_cloudctl(self, *args: str) -> CommandResult:
    cmd = [self.config.cloudctl_path] + list(args)
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=self.config.cloudctl_timeout,
        )
    except asyncio.TimeoutError:
        process.kill()
        # Return helpful timeout error
```

### Concurrent Operations

Multiple organizations can be checked concurrently:

```python
# Check all credentials in parallel
creds = await skill.check_all_credentials()
# For each org: await skill.get_token_status(org_name)
# All awaits execute concurrently
```

## Error Handling Strategy

### Error Classification

1. **Transient Errors** — Retry with backoff
   - Network timeouts
   - Temporary service unavailability
   - Rate limiting

2. **Token Errors** — Auto-refresh and retry
   - Expired tokens
   - Invalid credentials
   - Token refresh failures

3. **Context Errors** — Validation and helpful messages
   - Invalid organization
   - Missing context
   - Invalid region/project

4. **Permanent Errors** — Fail-fast with guidance
   - cloudctl not installed
   - Invalid command
   - Permission denied

### Retry Logic

```python
for attempt in range(self.config.cloudctl_retries + 1):
    try:
        # Execute command
        return result
    except TransientError:
        if attempt < max_retries:
            # Exponential backoff: 1s, 2s, 4s...
            await asyncio.sleep(2 ** attempt)
            continue
        else:
            raise
```

### Error Messages

All errors include:
- **error** — What failed
- **fix** — How to fix it

```python
return CommandResult(
    success=False,
    error="cloudctl not installed",
    fix="Install cloudctl from https://...",
)
```

## Audit Logging

### Format

JSONL (JSON Lines) for easy parsing:

```json
{
  "timestamp": "2026-04-26T10:30:45.123456",
  "operation": "switch_context",
  "context_before": {
    "provider": "aws",
    "organization": "dev",
    "account_id": "123456789"
  },
  "context_after": {
    "provider": "aws",
    "organization": "prod",
    "account_id": "987654321"
  },
  "user": "craig",
  "success": true,
  "duration_ms": 125.34
}
```

### Storage

```
~/.config/cloudctl/audit/operations_20260426.jsonl
~/.config/cloudctl/audit/operations_20260427.jsonl
```

### Usage

```bash
# View today's operations
cat ~/.config/cloudctl/audit/operations_$(date +%Y%m%d).jsonl | python -m json.tool

# Count operations
grep -c "operation" ~/.config/cloudctl/audit/operations_*.jsonl

# Find failed operations
grep '"success": false' ~/.config/cloudctl/audit/operations_*.jsonl
```

## Performance Optimizations

### Context Caching

```python
# Cache context for 5 minutes (configurable)
if self._context_cache and age < self.config.cache_ttl_seconds:
    return self._context_cache

# Invalidate cache after switch
self._context_cache = None
self._cache_time = None
```

**Benefit:** ~50ms cached vs ~100ms uncached

### Token Auto-Refresh

```python
# Proactively refresh before expiry
if status.expires_in_seconds < 300:  # 5 minutes
    await self.login(organization)
```

**Benefit:** Prevents mid-operation token errors

### Async I/O

All blocking operations are async:
- Subprocess execution
- File I/O for audit logs
- Configuration loading

**Benefit:** Concurrent operations without blocking

## Security Considerations

### Secrets Management

- No hardcoded secrets
- Credentials via environment variables only
- Configuration files for local setup
- `.cloudctl.yaml` in `.gitignore`

### Input Validation

- All inputs validated before execution
- Organization names sanitized
- Region/project names validated
- Pydantic validation at boundaries

### Audit Logging

- All operations logged
- No credentials in logs
- Safe error messages (no secret leakage)
- Timestamps for forensics

### Safe Error Messages

```python
# ✅ Safe — doesn't leak secrets
error = "Authentication failed"
fix = "Check CLOUDCTL_PATH and credentials"

# ❌ Unsafe — leaks secrets
error = f"Auth failed: API key {api_key} invalid"
```

### Subprocess Safety

```python
# Execute cloudctl as subprocess
# - Isolated process
# - No shell injection (list of args)
# - Timeout protection
# - Clean process termination
```
