"""CloudctlSkill — Enterprise-grade cloud context management."""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from . import oci_handler
from .config import load_config
from .models import (
    CloudContext,
    CloudProvider,
    CommandResult,
    CommandStatus,
    HealthCheckResult,
    OperationLog,
    SkillConfig,
    TokenStatus,
)
from .utils import setup_audit_logging, write_audit_log

# Path to cloudctl orgs configuration
_ORGS_CONFIG_PATH = Path.home() / ".config" / "cloudctl" / "orgs.yaml"


def _load_orgs_yaml() -> dict[str, Any]:
    """Load ~/.config/cloudctl/orgs.yaml and return its contents.

    Returns:
        Parsed YAML dict, or empty dict if not found / unreadable.
    """
    if not _ORGS_CONFIG_PATH.exists():
        return {}
    try:
        with open(_ORGS_CONFIG_PATH, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


def _get_org_config(org_name: str) -> dict[str, Any]:
    """Return the orgs.yaml config dict for *org_name*, or {} if not found.

    Args:
        org_name: Organisation name as defined in orgs.yaml.

    Returns:
        Dict of org configuration keys.
    """
    data = _load_orgs_yaml()
    for org in data.get("orgs", []):
        if isinstance(org, dict) and org.get("name") == org_name:
            return org
    return {}


class CloudctlSkill:
    """Enterprise cloud context management for Claude.

    Provides autonomous multi-cloud context switching, credential management,
    and audit logging for AWS, Azure, and GCP.

    Attributes:
        config: Skill configuration
        _context_cache: Cached cloud context
        _cache_time: When cache was created
        _audit_logger: Path to audit log
    """

    def __init__(self, config: SkillConfig | None = None) -> None:
        """Initialize CloudctlSkill.

        Args:
            config: Optional SkillConfig. If None, loads from environment/files.
        """
        self.config = config or load_config()
        self._context_cache: CloudContext | None = None
        self._cache_time: datetime | None = None
        self._audit_logger = setup_audit_logging() if self.config.enable_audit_logging else None

    async def get_context(self) -> CloudContext:
        """Get current cloud context.

        Uses cached context if available and fresh, otherwise queries cloudctl.
        Falls back to reading context file if cloudctl status fails.

        Returns:
            CloudContext: Current cloud context state

        Raises:
            RuntimeError: If unable to determine context
        """
        # Check cache
        if self._context_cache and self._cache_time:
            age = (datetime.utcnow() - self._cache_time).total_seconds()
            if age < self.config.cache_ttl_seconds and self.config.enable_caching:
                return self._context_cache

        # Query cloudctl status
        result = await self._execute_cloudctl("status")
        if result.success:
            # Parse context from output
            try:
                context = self._parse_context(result.output)
                # Context is already frozen, so we can't modify credentials_valid after creation
                # Cache result
                if self.config.enable_caching:
                    self._context_cache = context
                    self._cache_time = datetime.utcnow()
                return context
            except RuntimeError:
                pass  # Try fallback method

        # Fallback: Try to read context from file (~/.config/cloudctl/context)
        try:
            context = await self._read_context_file()
            if context:
                # Context is already frozen, so we can't modify credentials_valid
                # Cache result
                if self.config.enable_caching:
                    self._context_cache = context
                    self._cache_time = datetime.utcnow()
                return context
        except Exception:
            pass  # Continue to error

        # Neither method worked - provide helpful error
        raise RuntimeError(
            "No active context found. Use '/cloudctl list orgs' to see available organizations, "
            "then run 'cloudctl switch <org>' to set one."
        )

    async def switch_context(self, organization: str, account_id: str | None = None) -> CommandResult:
        """Switch cloud context to specified organization.

        Validates context switch and updates state. Automatically
        refreshes token if expired.

        Args:
            organization: Organization name
            account_id: Optional account ID to switch to. If not provided, will list and use first.

        Returns:
            CommandResult with switch operation status

        Raises:
            ValueError: If organization name is empty
            RuntimeError: If context switch fails
        """
        if not organization or not organization.strip():
            raise ValueError("Organization name cannot be empty")

        # Get context before switch
        context_before = None
        try:
            context_before = await self.get_context()
        except RuntimeError:
            pass  # No prior context

        # If no account specified, try to get first available account
        if not account_id:
            try:
                accounts_result = await self._execute_cloudctl("accounts", organization)
                if accounts_result.success:
                    # Parse accounts output to find first account ID
                    # Format is like: "624426145233 │ hcp-craighoad-prod  │       │"
                    for line in accounts_result.output.split("\n"):
                        if "│" in line and any(char.isdigit() for char in line):
                            parts = line.split("│")
                            if parts:
                                potential_id = parts[0].strip()
                                if potential_id.isdigit() and len(potential_id) == 12:
                                    account_id = potential_id
                                    break
            except Exception:
                pass  # If we can't get accounts, let cloudctl handle it interactively

        # Attempt switch with or without account ID
        start_time = time.time()
        if account_id:
            # Try switching with account ID (if supported)
            result = await self._execute_cloudctl("switch", organization, "--account", account_id)
            if not result.success:
                # Fallback: try without account ID
                result = await self._execute_cloudctl("switch", organization)
        else:
            result = await self._execute_cloudctl("switch", organization)

        duration = (time.time() - start_time) * 1000

        if not result.success:
            # Check if it's an interactive prompt failure
            if "input is not a terminal" in result.error.lower() or "select account" in result.error.lower():
                # Create new result with better error message
                result = CommandResult(
                    success=False,
                    status=CommandStatus.FAILURE,
                    error=(
                        f"Unable to switch to '{organization}' non-interactively. "
                        "Please run 'cloudctl switch {organization}' manually to set up context. "
                        "Then /cloudctl commands will work."
                    ),
                    fix=f"Run: cloudctl switch {organization}",
                    output=result.output,
                )
            # Try auto-refresh on token error
            elif "token" in result.error.lower() or "credential" in result.error.lower():
                refresh_result = await self.login(organization)
                if refresh_result.success:
                    # Retry switch after refresh
                    result = await self._execute_cloudctl("switch", organization)

        # Get context after switch
        context_after = None
        if result.success:
            try:
                context_after = await self.get_context()
                # Invalidate cache to force fresh fetch
                self._context_cache = None
                self._cache_time = None
            except RuntimeError:
                pass

        # Log operation
        if self._audit_logger:
            log = OperationLog(
                operation="switch_context",
                context_before=context_before.model_dump() if context_before else None,
                context_after=context_after.model_dump() if context_after else None,
                success=result.success,
                error=result.error,
                duration_ms=duration,
            )
            await write_audit_log(self._audit_logger, log)

        return result

    async def switch_region(self, region: str) -> CommandResult:
        """Switch cloud region.

        Note: Region switching via cloudctl may be limited. This method
        updates the AWS_REGION environment variable for the session.

        Args:
            region: Region identifier (e.g., 'us-west-2', 'europe-west1')

        Returns:
            CommandResult with operation status
        """
        if not region or not region.strip():
            raise ValueError("Region cannot be empty")

        # Get current context to validate region
        try:
            context = await self.get_context()
            if context.provider == CloudProvider.AWS:
                # For AWS, set the region in environment
                os.environ["AWS_REGION"] = region
                return CommandResult(
                    success=True,
                    status=CommandStatus.SUCCESS,
                    output=f"Region switched to {region} (AWS_REGION={region})",
                )
            else:
                return CommandResult(
                    success=False,
                    status=CommandStatus.FAILURE,
                    error=f"Region switching not supported for {context.provider.value} provider",
                    fix="Region switching is primarily for AWS. For GCP, use project switching.",
                )
        except RuntimeError as e:
            return CommandResult(
                success=False,
                status=CommandStatus.FAILURE,
                error=str(e),
                fix="Set a context first with 'cloudctl switch <org>'",
            )

    async def switch_project(self, project_id: str) -> CommandResult:
        """Switch GCP project.

        Updates the GCLOUD_PROJECT environment variable for the session.

        Args:
            project_id: GCP project ID

        Returns:
            CommandResult with operation status
        """
        if not project_id or not project_id.strip():
            raise ValueError("Project ID cannot be empty")

        # Get current context to validate provider
        try:
            context = await self.get_context()
            if context.provider == CloudProvider.GCP:
                # For GCP, set the project in environment
                os.environ["GCLOUD_PROJECT"] = project_id
                os.environ["CLOUDSDK_CORE_PROJECT"] = project_id
                return CommandResult(
                    success=True,
                    status=CommandStatus.SUCCESS,
                    output=f"GCP project switched to {project_id} (GCLOUD_PROJECT={project_id})",
                )
            else:
                return CommandResult(
                    success=False,
                    status=CommandStatus.FAILURE,
                    error=f"Project switching not supported for {context.provider.value} provider",
                    fix="Project switching is primarily for GCP. For AWS, use region switching.",
                )
        except RuntimeError as e:
            return CommandResult(
                success=False,
                status=CommandStatus.FAILURE,
                error=str(e),
                fix="Set a context first with 'cloudctl switch <org>'",
            )

    async def list_organizations(self) -> list[dict[str, str]]:
        """List all available organizations.

        Returns:
            List of org dicts with 'name' and 'provider' keys

        Raises:
            RuntimeError: If unable to list organizations
        """
        # Use cloudctl org list command
        result = await self._execute_cloudctl("org", "list")
        if not result.success:
            raise RuntimeError(f"Failed to list organizations: {result.error}")

        try:
            # Try JSON parsing first
            orgs = json.loads(result.output)
            return orgs if isinstance(orgs, list) else [orgs]
        except json.JSONDecodeError:
            # Parse text output - expected format:
            # "Configured Organizations (2)
            #   myorg  [AWS]  enabled
            #     https://d-9c67661145.awsapps.com/start
            #   gcp-terrorgems  [GCP]  enabled
            #     asatst-gemini-api-v2"
            orgs = []
            lines = result.output.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line and "[" in line and "]" in line:
                    # Parse line like "myorg  [AWS]  enabled"
                    parts = line.split()
                    if parts:
                        org_name = parts[0]
                        # Extract provider from [PROVIDER]
                        provider_start = line.find("[")
                        provider_end = line.find("]")
                        if provider_start >= 0 and provider_end > provider_start:
                            provider = line[provider_start + 1 : provider_end]
                            orgs.append({"name": org_name, "provider": provider.lower()})

            if orgs:
                return orgs
            raise RuntimeError("Failed to parse organization list") from None

    async def verify_credentials(self, organization: str) -> bool:
        """Verify credentials exist and are valid for organization.

        Args:
            organization: Organization name

        Returns:
            True if credentials valid, False otherwise
        """
        return await self._verify_credentials(organization)

    async def login(self, organization: str) -> CommandResult:
        """Login to organization and refresh credentials.

        For OCI organisations (provider: oci in orgs.yaml) this calls the
        oci_handler directly, bypassing the cloudctl binary which does not yet
        support Oracle Cloud Infrastructure.

        Args:
            organization: Organization name to login to

        Returns:
            CommandResult with login status
        """
        if not organization or not organization.strip():
            raise ValueError("Organization cannot be empty")

        # Route OCI orgs to the dedicated OCI handler
        org_config = _get_org_config(organization)
        if oci_handler.is_oci_org(org_config):
            profile = str(org_config.get("oci_profile", "DEFAULT"))
            return await oci_handler.oci_login(organization, profile=profile)

        # Use cloudctl login command for AWS / GCP / Azure
        return await self._execute_cloudctl("login", organization)

    async def get_token_status(self, organization: str) -> TokenStatus:
        """Get token status for organization.

        Args:
            organization: Organization name

        Returns:
            TokenStatus with validity and expiration info

        Raises:
            RuntimeError: If unable to get token status
        """
        # Cloudctl status doesn't support --format flag, so we fallback to assuming
        # if we can communicate with cloudctl, tokens are generally valid
        try:
            # Try to get status without format flag
            result = await self._execute_cloudctl("status")
            if result.success:
                # If cloudctl status works, assume token is valid
                return TokenStatus(
                    valid=True,
                    expires_in_seconds=None,
                    expired_at=None,
                    refreshed_at=None,
                )
            else:
                # If status fails, token might be invalid
                return TokenStatus(
                    valid=False,
                    expires_in_seconds=None,
                    expired_at=None,
                    refreshed_at=None,
                )
        except Exception:
            # Default to valid if we can't determine
            return TokenStatus(
                valid=True,
                expires_in_seconds=None,
                expired_at=None,
                refreshed_at=None,
            )

    async def check_all_credentials(self) -> dict[str, dict[str, Any]]:
        """Check credentials across all organizations.

        Automatically refreshes expired tokens.

        Returns:
            Dict mapping org name to credential status

        Raises:
            RuntimeError: If unable to check credentials
        """
        try:
            orgs = await self.list_organizations()
        except RuntimeError as e:
            raise RuntimeError(f"Failed to check credentials: {e}") from e

        results = {}
        for org in orgs:
            org_name = org.get("name", "")
            if not org_name:
                continue

            try:
                status = await self.get_token_status(org_name)
                results[org_name] = {
                    "valid": status.valid,
                    "expires_in_seconds": status.expires_in_seconds,
                    "expired_at": status.expired_at.isoformat() if status.expired_at else None,
                    "refreshed_at": status.refreshed_at.isoformat() if status.refreshed_at else None,
                }

                # Auto-refresh if expired or expiring soon (within 5 minutes)
                if status.expires_in_seconds is not None and status.expires_in_seconds < 300:
                    login_result = await self.login(org_name)
                    results[org_name]["auto_refreshed"] = login_result.success
            except RuntimeError as e:
                results[org_name] = {
                    "valid": False,
                    "error": str(e),
                }

        return results

    async def health_check(self) -> HealthCheckResult:
        """Perform comprehensive health check.

        Checks cloudctl installation, organizations, and credentials.

        Returns:
            HealthCheckResult with detailed health status
        """
        checks_passed = 0
        checks_failed = 0

        # Check cloudctl installation
        cloudctl_installed = await self._is_cloudctl_installed()
        if cloudctl_installed:
            checks_passed += 1
        else:
            checks_failed += 1

        # Get cloudctl version
        cloudctl_version = None
        if cloudctl_installed:
            result = await self._execute_cloudctl("--version")
            if result.success:
                cloudctl_version = result.output.strip()
                checks_passed += 1
            else:
                checks_failed += 1

        # List organizations
        organizations_available = 0
        credentials_valid = {}
        try:
            orgs = await self.list_organizations()
            organizations_available = len(orgs)
            checks_passed += 1

            # Check credentials for each org
            for org in orgs:
                org_name = org.get("name", "")
                if org_name:
                    try:
                        is_valid = await self._verify_credentials(org_name)
                        credentials_valid[org_name] = is_valid
                        if is_valid:
                            checks_passed += 1
                        else:
                            checks_failed += 1
                    except RuntimeError:
                        credentials_valid[org_name] = False
                        checks_failed += 1
        except RuntimeError:
            checks_failed += 1

        # Overall health: healthy if cloudctl installed and has valid orgs
        is_healthy = cloudctl_installed and organizations_available > 0

        return HealthCheckResult(
            is_healthy=is_healthy,
            cloudctl_installed=cloudctl_installed,
            cloudctl_version=cloudctl_version,
            organizations_available=organizations_available,
            credentials_valid=credentials_valid,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    async def ensure_cloud_access(self, organization: str) -> dict[str, Any]:
        """Ensure access to cloud organization with auto-recovery.

        Comprehensive check with automatic remediation:
        - Verifies cloudctl is installed
        - Checks organization exists
        - Verifies credentials
        - Auto-refreshes expired tokens
        - Validates context switch

        Args:
            organization: Organization name to access

        Returns:
            Dict with keys:
            - success (bool): Whether access is confirmed
            - context (str): Current context string
            - error (str): Error message if failed
            - fix (str): Suggested remediation
            - auto_refreshed (bool): Whether token was auto-refreshed

        Raises:
            ValueError: If organization is empty
        """
        if not organization or not organization.strip():
            raise ValueError("Organization cannot be empty")

        # Health check
        health = await self.health_check()
        if not health.cloudctl_installed:
            return {
                "success": False,
                "context": None,
                "error": "cloudctl not installed",
                "fix": f"Install cloudctl from {self.config.cloudctl_path}",
                "auto_refreshed": False,
            }

        # Verify organization exists
        try:
            orgs = await self.list_organizations()
            org_names = [o.get("name", "") for o in orgs]
            if organization not in org_names:
                return {
                    "success": False,
                    "context": None,
                    "error": f"Organization '{organization}' not found",
                    "fix": f"Available organizations: {', '.join(org_names)}",
                    "auto_refreshed": False,
                }
        except RuntimeError as e:
            return {
                "success": False,
                "context": None,
                "error": f"Failed to list organizations: {e}",
                "fix": "Check cloudctl installation and credentials",
                "auto_refreshed": False,
            }

        # Check and auto-refresh credentials
        auto_refreshed = False
        try:
            status = await self.get_token_status(organization)
            if not status.valid:
                login_result = await self.login(organization)
                if not login_result.success:
                    return {
                        "success": False,
                        "context": None,
                        "error": f"Failed to login: {login_result.error}",
                        "fix": login_result.fix or "Try manual login",
                        "auto_refreshed": False,
                    }
                auto_refreshed = True
        except RuntimeError:
            # Try login anyway
            login_result = await self.login(organization)
            if not login_result.success:
                return {
                    "success": False,
                    "context": None,
                    "error": f"Failed to login: {login_result.error}",
                    "fix": login_result.fix or "Check credentials",
                    "auto_refreshed": False,
                }
            auto_refreshed = True

        # Switch to organization
        switch_result = await self.switch_context(organization)
        if not switch_result.success:
            return {
                "success": False,
                "context": None,
                "error": f"Failed to switch context: {switch_result.error}",
                "fix": switch_result.fix or "Verify organization configuration",
                "auto_refreshed": auto_refreshed,
            }

        # Get final context
        try:
            context = await self.get_context()
            return {
                "success": True,
                "context": str(context),
                "error": None,
                "fix": None,
                "auto_refreshed": auto_refreshed,
            }
        except RuntimeError as e:
            return {
                "success": False,
                "context": None,
                "error": f"Failed to verify context: {e}",
                "fix": "Context may not be properly configured",
                "auto_refreshed": auto_refreshed,
            }

    async def validate_switch(self) -> bool:
        """Validate that context switch is working.

        Returns:
            True if context switching works, False otherwise
        """
        try:
            await self.get_context()
            return True
        except RuntimeError:
            return False

    # Private methods

    async def _execute_cloudctl(self, *args: str) -> CommandResult:
        """Execute cloudctl command with retry logic.

        Args:
            *args: Command arguments

        Returns:
            CommandResult with output and status
        """
        if self.config.dry_run:
            return CommandResult(
                success=True,
                status=CommandStatus.SUCCESS,
                output=f"[DRY RUN] Would execute: {' '.join(args)}",
            )

        cmd = [self.config.cloudctl_path] + list(args)
        last_error = None

        for attempt in range(self.config.cloudctl_retries + 1):
            try:
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
                except TimeoutError:
                    process.kill()
                    return CommandResult(
                        success=False,
                        status=CommandStatus.FAILURE,
                        error=f"Command timeout after {self.config.cloudctl_timeout}s",
                        fix="Increase CLOUDCTL_TIMEOUT or check network connection",
                        exit_code=-1,
                    )

                output = stdout.decode("utf-8", errors="replace").strip()
                error = stderr.decode("utf-8", errors="replace").strip()

                if process.returncode == 0:
                    return CommandResult(
                        success=True,
                        status=CommandStatus.SUCCESS,
                        output=output,
                        exit_code=process.returncode,
                    )

                last_error = error or output

                # Retry on transient errors
                if attempt < self.config.cloudctl_retries:
                    if "timeout" in error.lower() or "temporarily unavailable" in error.lower():
                        await asyncio.sleep(2**attempt)  # Exponential backoff
                        continue

                # Permanent error
                return CommandResult(
                    success=False,
                    status=CommandStatus.FAILURE,
                    output=output,
                    error=error or "Unknown error",
                    exit_code=process.returncode,
                )

            except FileNotFoundError:
                return CommandResult(
                    success=False,
                    status=CommandStatus.FAILURE,
                    error=f"cloudctl not found at {self.config.cloudctl_path}",
                    fix="Install cloudctl or set CLOUDCTL_PATH",
                    exit_code=-1,
                )
            except Exception as e:
                last_error = str(e)
                if attempt < self.config.cloudctl_retries:
                    await asyncio.sleep(2**attempt)
                    continue

        return CommandResult(
            success=False,
            status=CommandStatus.FAILURE,
            error=last_error or "Command failed after retries",
            fix="Check cloudctl installation and credentials",
            exit_code=-1,
        )

    async def _read_context_file(self) -> CloudContext | None:
        """Read context from ~/.config/cloudctl/context file.

        This is a fallback method when cloudctl status doesn't work.

        Returns:
            CloudContext if context file exists and is valid, None otherwise
        """
        try:
            context_file = Path.home() / ".config" / "cloudctl" / "context"
            if not context_file.exists():
                return None

            with open(context_file) as f:
                data = json.load(f)

            # Make sure we have an organization
            org = data.get("org") or data.get("organization")
            if not org:
                return None

            # Parse context data
            provider_str = data.get("provider", "aws").lower()
            try:
                provider = CloudProvider(provider_str)
            except ValueError:
                provider = CloudProvider.AWS

            context = CloudContext(
                provider=provider,
                organization=org,
                account_id=data.get("account"),
                region=data.get("region"),
                role=data.get("role"),
                credentials_valid=True,
            )
            return context
        except (json.JSONDecodeError, FileNotFoundError, KeyError, ValueError):
            # Return None only for expected file/format errors
            return None
        except Exception:
            # Return None for any other errors
            return None

    async def _verify_credentials(self, organization: str) -> bool:
        """Verify credentials exist for organization.

        Args:
            organization: Organization name

        Returns:
            True if credentials valid, False otherwise
        """
        try:
            status = await self.get_token_status(organization)
            return status.valid
        except RuntimeError:
            return False

    async def _is_cloudctl_installed(self) -> bool:
        """Check if cloudctl is installed and accessible.

        Returns:
            True if cloudctl found, False otherwise
        """
        result = await self._execute_cloudctl("--version")
        return result.success

    def _parse_context(self, output: str) -> CloudContext:
        """Parse CloudContext from cloudctl output.

        Handles both new format and legacy formats:
        - "No active context found." → return None/raise
        - "aws:myorg account=123456789 role=terraform region=us-west-2"
        - "Organization: myorg\nProvider: aws\nAccount: 123456789\nRegion: us-west-2"

        Args:
            output: Raw cloudctl output

        Returns:
            Parsed CloudContext

        Raises:
            RuntimeError: If unable to parse context or no active context
        """
        try:
            # Handle "No active context" message
            if "no active context" in output.lower() or not output.strip():
                raise RuntimeError("No active context found. Use 'cloudctl switch <org>' to set one.")

            parts = output.split()
            if not parts:
                raise ValueError("Empty context output")

            # Try to parse as key=value pairs (alternative format)
            if "=" in output:
                # Parse line-by-line for key=value format
                provider = None
                org = None
                account_id = None
                region = None
                role = None

                for line in output.split("\n"):
                    line = line.strip()
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        if key == "provider" or key == "Provider":
                            try:
                                provider = CloudProvider(value)
                            except ValueError:
                                provider = CloudProvider.AWS
                        elif key == "organization" or key == "Organization":
                            org = value
                        elif key == "account" or key == "Account":
                            account_id = value
                        elif key == "region" or key == "Region":
                            region = value
                        elif key == "role" or key == "Role":
                            role = value

                if org:
                    return CloudContext(
                        provider=provider or CloudProvider.AWS,
                        organization=org,
                        account_id=account_id,
                        region=region,
                        role=role,
                        credentials_valid=True,
                    )

            # Try legacy format: 'aws:myorg account=123456789 role=terraform region=us-west-2'
            provider_org = parts[0]
            if ":" not in provider_org:
                raise ValueError(f"Invalid context format: {provider_org}")

            provider_str, org = provider_org.split(":", 1)

            # Find provider
            try:
                provider = CloudProvider(provider_str)
            except ValueError as e:
                raise ValueError(f"Unknown provider: {provider_str}") from e

            # Parse optional fields
            account_id = None
            region = None
            role = None

            for part in parts[1:]:
                if "=" in part:
                    key, value = part.split("=", 1)
                    if key == "account":
                        account_id = value
                    elif key == "region":
                        region = value
                    elif key == "role":
                        role = value

            return CloudContext(
                provider=provider,
                organization=org,
                account_id=account_id,
                region=region,
                role=role,
                credentials_valid=True,
            )

        except (ValueError, IndexError) as e:
            raise RuntimeError(f"Failed to parse context: {e}") from e
