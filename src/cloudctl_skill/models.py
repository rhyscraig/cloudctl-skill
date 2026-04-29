"""Pydantic v2 data models for CloudctlSkill."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CloudProvider(str, Enum):
    """Supported cloud providers."""

    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    OCI = "oci"


class CommandStatus(str, Enum):
    """Status of a command execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class TokenStatus(BaseModel):
    """Token validity status and expiration."""

    model_config = ConfigDict(frozen=True)

    valid: bool = Field(description="Whether token is currently valid")
    expires_in_seconds: int | None = Field(None, description="Seconds until expiry")
    expired_at: datetime | None = Field(None, description="When token expired")
    refreshed_at: datetime | None = Field(None, description="When token was last refreshed")


class CommandResult(BaseModel):
    """Result of a cloud command execution."""

    model_config = ConfigDict(frozen=True)

    success: bool = Field(description="Whether command succeeded")
    status: CommandStatus = Field(default=CommandStatus.SUCCESS, description="Command execution status")
    output: str = Field(default="", description="Command output")
    error: str | None = Field(None, description="Error message if failed")
    fix: str | None = Field(None, description="Suggested fix if failed")
    stderr: str | None = Field(None, description="Standard error output")
    exit_code: int = Field(default=0, description="Command exit code")

    @field_validator("status", mode="before")
    @classmethod
    def infer_status_from_success(cls, v: Any, info: Any) -> CommandStatus:
        """Infer status from success field if not provided."""
        if v is not None:
            return v
        success = info.data.get("success")
        if success:
            return CommandStatus.SUCCESS
        else:
            return CommandStatus.FAILURE


class CloudContext(BaseModel):
    """Current cloud context state."""

    model_config = ConfigDict(frozen=True)

    provider: CloudProvider = Field(description="Cloud provider")
    organization: str = Field(description="Organization name")
    account_id: str | None = Field(None, description="AWS account ID or GCP project ID")
    region: str | None = Field(None, description="Current region")
    role: str | None = Field(None, description="IAM role name")
    credentials_valid: bool = Field(default=False, description="Whether credentials are valid")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="When context was last updated")

    def __str__(self) -> str:
        """String representation of context."""
        parts = [f"{self.provider.value}:{self.organization}"]
        if self.account_id:
            parts.append(f"account={self.account_id}")
        if self.role:
            parts.append(f"role={self.role}")
        if self.region:
            parts.append(f"region={self.region}")
        return " ".join(parts)


class SkillConfig(BaseModel):
    """CloudctlSkill configuration."""

    model_config = ConfigDict()

    cloudctl_path: str = Field(default="cloudctl", description="Path to cloudctl binary")
    cloudctl_timeout: int = Field(default=30, description="Command timeout in seconds")
    cloudctl_retries: int = Field(default=3, description="Max retry attempts")
    verify_context_after_switch: bool = Field(default=True, description="Verify context after switch")
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    dry_run: bool = Field(default=False, description="Dry-run mode (don't execute commands)")
    enable_caching: bool = Field(default=True, description="Enable context caching")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")

    @field_validator("cloudctl_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is between 1-300 seconds."""
        if not 1 <= v <= 300:
            raise ValueError("cloudctl_timeout must be between 1-300 seconds")
        return v

    @field_validator("cloudctl_retries")
    @classmethod
    def validate_retries(cls, v: int) -> int:
        """Validate retries is between 0-10."""
        if not 0 <= v <= 10:
            raise ValueError("cloudctl_retries must be between 0-10")
        return v


class OperationLog(BaseModel):
    """Audit log entry for a cloud operation."""

    model_config = ConfigDict()

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When operation occurred")
    operation: str = Field(description="Operation name (e.g., 'switch_context')")
    context_before: dict[str, Any] | None = Field(None, description="Context before operation")
    context_after: dict[str, Any] | None = Field(None, description="Context after operation")
    user: str | None = Field(None, description="Username performing operation")
    success: bool = Field(description="Whether operation succeeded")
    error: str | None = Field(None, description="Error message if failed")
    duration_ms: float | None = Field(None, description="Duration of operation in milliseconds")

    def to_jsonl(self) -> str:
        """Convert to JSONL format."""
        return self.model_dump_json()


class HealthCheckResult(BaseModel):
    """Result of a health check."""

    model_config = ConfigDict(frozen=True)

    is_healthy: bool = Field(description="Overall health status")
    cloudctl_installed: bool = Field(description="Whether cloudctl is installed")
    cloudctl_version: str | None = Field(None, description="Installed cloudctl version")
    organizations_available: int = Field(default=0, description="Number of available organizations")
    credentials_valid: dict[str, bool] = Field(default_factory=dict, description="Per-org credential status")
    checks_passed: int = Field(default=0, description="Number of checks passed")
    checks_failed: int = Field(default=0, description="Number of checks failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When check was performed")
