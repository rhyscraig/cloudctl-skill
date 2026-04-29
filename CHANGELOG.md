# Changelog

All notable changes to CloudctlSkill are documented here.

---

## [2.0.0] - 2026-04-29 — Oracle Cloud Infrastructure (OCI) Provider

### 🌩️ Major New Feature: Oracle Cloud Infrastructure Support

This release adds **Oracle Cloud Infrastructure (OCI)** as a fully supported cloud provider, bringing the total to four: AWS, GCP, Azure, and OCI.

Because the `cloudctl` binary does not yet support OCI, CloudctlSkill handles OCI authentication and context management directly via the `oci` CLI binary. All credentials continue to live in `~/.oci/config` — zero credentials are stored in code.

#### What changed

**`CloudProvider` enum** (`models.py`)
```python
class CloudProvider(str, Enum):
    AWS   = "aws"
    GCP   = "gcp"
    AZURE = "azure"
    OCI   = "oci"   # ← new
```

**New module: `oci_handler.py`**

| Function | Description |
|---|---|
| `get_oci_context(org_name, profile)` | Build a `CloudContext` from `~/.oci/config` — no network call. |
| `verify_oci_auth(profile)` | Make a live `oci iam user get` API call; returns `TokenStatus`. |
| `oci_login(org_name, profile)` | Validate existing OCI config and API key; return `CommandResult`. |
| `is_oci_org(org_config)` | Return `True` if `orgs.yaml` entry has `provider: oci`. |

**`skill.py` — `login()` now routes OCI orgs automatically**

The `CloudctlSkill.login(organization)` method now reads `~/.config/cloudctl/orgs.yaml` and, if the org has `provider: oci`, delegates to `oci_handler.oci_login()` instead of the `cloudctl` binary. All non-OCI orgs (AWS, GCP, Azure) are unchanged.

To use a non-DEFAULT OCI profile, add `oci_profile: MYPROFILE` to the org entry in `orgs.yaml`.

**Example `orgs.yaml` entry:**
```yaml
orgs:
  - name: oci-craighoad
    provider: oci
    oci_profile: DEFAULT          # optional; defaults to DEFAULT
    default_region: eu-frankfurt-1
```

#### New tests

- **`tests/test_oci_handler.py`** — 33 tests covering all branches of `oci_handler.py`:
  - `_is_oci_configured` (3 cases)
  - `_read_oci_config` — DEFAULT + named profile + not configured + profile not found
  - `_run_oci_async` — success, failure, timeout
  - `get_oci_context` — happy path, named profile, not configured
  - `verify_oci_auth` — not configured, profile missing, API failure, bad JSON, success, profile flag handling
  - `oci_login` — not configured, success, auth failure, config-read failure, named profile
  - `is_oci_org` — all provider values

- **`tests/test_skill.py`** — 4 new OCI routing tests:
  - OCI org routes to `oci_handler`, not `cloudctl`
  - Custom `oci_profile` is passed through
  - AWS / GCP / Azure / unknown orgs still route to `cloudctl`

#### Coverage

| Module | Coverage |
|---|---|
| `oci_handler.py` | 98% |
| `skill.py` | 82% |
| `config.py` | 98% |
| `guardrails.py` | 90% |
| **Total** | **88.8%** (gate: 85%) |

**259 tests passing, 0 failures.**

### ✅ Compatibility

- **AWS, GCP, Azure** — completely unaffected. The `login()` routing change is a no-op for non-OCI orgs.
- **`cloudctl` binary** — still used for all AWS/GCP/Azure operations. OCI is the only provider that bypasses it.
- **MCP server** (`mcp.py`) — unchanged; all 12 tools work as before.

### 📋 Prerequisites

```bash
# OCI CLI must be installed
brew install oci-cli

# Credentials configured via
oci setup config
# or: awsctl oci login
```

### 🔖 Migration from v1.x

No breaking changes for existing AWS/GCP/Azure configurations. To add OCI:

1. Install OCI CLI and run `oci setup config`
2. Add an `oci` org entry to `~/.config/cloudctl/orgs.yaml`
3. `/cloudctl login oci-<orgname>` — done

---

## [1.2.0] - 2026-04-14 — Azure Provider

Added Microsoft Azure as a supported cloud provider. All 12 tools supported via Azure CLI (`az`).

## [1.1.0] - 2026-04-01 — GCP Provider

Added Google Cloud Platform support via `gcloud` CLI.

## [1.0.0] - 2026-03-15 — Initial Release

AWS multi-account SSO support via `cloudctl` binary. MCP server for Claude. 48 tests.
