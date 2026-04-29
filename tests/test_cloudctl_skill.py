"""Comprehensive test suite for CloudctlSkill.

Tests cover: models, configuration, context operations, credentials,
health checks, login, multi-cloud, error handling, and integration scenarios.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from cloudctl_skill import CloudctlSkill
from cloudctl_skill.models import (
    CloudContext,
    CloudProvider,
    CommandResult,
    CommandStatus,
    HealthCheckResult,
    OperationLog,
    SkillConfig,
    TokenStatus,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def skill_config() -> SkillConfig:
    """Create test SkillConfig."""
    return SkillConfig(
        cloudctl_path="/usr/bin/cloudctl",
        cloudctl_timeout=10,
        cloudctl_retries=2,
        verify_context_after_switch=True,
        enable_audit_logging=False,
        dry_run=False,
    )


@pytest.fixture
def cloudctl_skill(skill_config: SkillConfig) -> CloudctlSkill:
    """Create test CloudctlSkill instance."""
    return CloudctlSkill(config=skill_config)


@pytest.fixture
def aws_context() -> CloudContext:
    """Create test AWS context."""
    return CloudContext(
        provider=CloudProvider.AWS,
        organization="aws-prod",
        account_id="123456789012",
        region="us-west-2",
        role="terraform",
        credentials_valid=True,
    )


@pytest.fixture
def gcp_context() -> CloudContext:
    """Create test GCP context."""
    return CloudContext(
        provider=CloudProvider.GCP,
        organization="gcp-prod",
        account_id="my-project-id",
        region="us-central1",
        credentials_valid=True,
    )


@pytest.fixture
def command_result_success() -> CommandResult:
    """Create successful CommandResult."""
    return CommandResult(
        success=True,
        status=CommandStatus.SUCCESS,
        output="Operation completed successfully",
        exit_code=0,
    )


@pytest.fixture
def command_result_failure() -> CommandResult:
    """Create failed CommandResult."""
    return CommandResult(
        success=False,
        status=CommandStatus.FAILURE,
        error="Operation failed",
        fix="Try again later",
        exit_code=1,
    )


# ============================================================================
# Model Tests
# ============================================================================


class TestCloudProvider:
    """Tests for CloudProvider enum."""

    def test_provider_values(self) -> None:
        """Test CloudProvider enum values."""
        assert CloudProvider.AWS.value == "aws"
        assert CloudProvider.GCP.value == "gcp"
        assert CloudProvider.AZURE.value == "azure"
        assert CloudProvider.OCI.value == "oci"

    def test_provider_from_string(self) -> None:
        """Test creating CloudProvider from string."""
        assert CloudProvider("aws") == CloudProvider.AWS
        assert CloudProvider("gcp") == CloudProvider.GCP
        assert CloudProvider("azure") == CloudProvider.AZURE
        assert CloudProvider("oci") == CloudProvider.OCI


class TestTokenStatus:
    """Tests for TokenStatus model."""

    def test_valid_token_status(self) -> None:
        """Test creating valid TokenStatus."""
        status = TokenStatus(valid=True, expires_in_seconds=3600)
        assert status.valid is True
        assert status.expires_in_seconds == 3600

    def test_expired_token_status(self) -> None:
        """Test expired token status."""
        expired_at = datetime.utcnow() - timedelta(hours=1)
        status = TokenStatus(valid=False, expired_at=expired_at)
        assert status.valid is False
        assert status.expired_at is not None


class TestCommandResult:
    """Tests for CommandResult model."""

    def test_successful_result(self, command_result_success: CommandResult) -> None:
        """Test successful command result."""
        assert command_result_success.success is True
        assert command_result_success.status == CommandStatus.SUCCESS
        assert command_result_success.exit_code == 0

    def test_failed_result(self, command_result_failure: CommandResult) -> None:
        """Test failed command result."""
        assert command_result_failure.success is False
        assert command_result_failure.status == CommandStatus.FAILURE
        assert command_result_failure.error is not None


class TestCloudContext:
    """Tests for CloudContext model."""

    def test_aws_context(self, aws_context: CloudContext) -> None:
        """Test AWS context creation."""
        assert aws_context.provider == CloudProvider.AWS
        assert aws_context.organization == "aws-prod"
        assert aws_context.account_id == "123456789012"
        assert aws_context.credentials_valid is True

    def test_gcp_context(self, gcp_context: CloudContext) -> None:
        """Test GCP context creation."""
        assert gcp_context.provider == CloudProvider.GCP
        assert gcp_context.organization == "gcp-prod"
        assert gcp_context.account_id == "my-project-id"

    def test_context_string_representation(self, aws_context: CloudContext) -> None:
        """Test context string representation."""
        context_str = str(aws_context)
        assert "aws:aws-prod" in context_str
        assert "account=123456789012" in context_str
        assert "region=us-west-2" in context_str


class TestSkillConfig:
    """Tests for SkillConfig model."""

    def test_default_config(self) -> None:
        """Test default SkillConfig values."""
        config = SkillConfig()
        assert config.cloudctl_path == "cloudctl"
        assert config.cloudctl_timeout == 30
        assert config.cloudctl_retries == 3
        assert config.enable_caching is True

    def test_config_validation(self) -> None:
        """Test SkillConfig validation."""
        # Invalid timeout (too high)
        with pytest.raises(ValidationError):
            SkillConfig(cloudctl_timeout=500)

        # Invalid retries (negative)
        with pytest.raises(ValidationError):
            SkillConfig(cloudctl_retries=-1)


class TestOperationLog:
    """Tests for OperationLog model."""

    def test_operation_log_creation(self, aws_context: CloudContext) -> None:
        """Test creating operation log."""
        log = OperationLog(
            operation="switch_context",
            context_before=aws_context.model_dump(),
            success=True,
        )
        assert log.operation == "switch_context"
        assert log.success is True

    def test_operation_log_jsonl(self) -> None:
        """Test JSONL serialization."""
        log = OperationLog(operation="test", success=True)
        jsonl = log.to_jsonl()
        parsed = json.loads(jsonl)
        assert parsed["operation"] == "test"
        assert parsed["success"] is True


# ============================================================================
# Configuration Tests
# ============================================================================


class TestConfiguration:
    """Tests for configuration loading."""

    def test_config_from_env(self) -> None:
        """Test loading config from environment."""
        import os

        with patch.dict(os.environ, {"CLOUDCTL_TIMEOUT": "60"}):
            from cloudctl_skill.config import load_config

            config = load_config()
            assert config.cloudctl_timeout == 60

    def test_config_validation_timeout(self) -> None:
        """Test config timeout validation."""
        with pytest.raises(ValidationError):
            SkillConfig(cloudctl_timeout=1000)

    def test_config_validation_retries(self) -> None:
        """Test config retries validation."""
        with pytest.raises(ValidationError):
            SkillConfig(cloudctl_retries=100)


# ============================================================================
# CloudctlSkill Tests - Context Operations
# ============================================================================


class TestContextOperations:
    """Tests for context-related operations."""

    @pytest.mark.asyncio
    async def test_parse_context(self, cloudctl_skill: CloudctlSkill) -> None:
        """Test parsing cloud context."""
        output = "aws:myorg account=123456789 role=terraform region=us-west-2"
        context = cloudctl_skill._parse_context(output)

        assert context.provider == CloudProvider.AWS
        assert context.organization == "myorg"
        assert context.account_id == "123456789"
        assert context.role == "terraform"
        assert context.region == "us-west-2"

    @pytest.mark.asyncio
    async def test_parse_context_minimal(self, cloudctl_skill: CloudctlSkill) -> None:
        """Test parsing minimal context."""
        output = "gcp:myproject"
        context = cloudctl_skill._parse_context(output)

        assert context.provider == CloudProvider.GCP
        assert context.organization == "myproject"
        assert context.account_id is None

    @pytest.mark.asyncio
    async def test_switch_context_invalid_org(self, cloudctl_skill: CloudctlSkill) -> None:
        """Test switching to invalid organization."""
        with pytest.raises(ValueError):
            await cloudctl_skill.switch_context("")

    @pytest.mark.asyncio
    async def test_switch_region_invalid_region(self, cloudctl_skill: CloudctlSkill) -> None:
        """Test switching to invalid region."""
        with pytest.raises(ValueError):
            await cloudctl_skill.switch_region("")


# ============================================================================
# CloudctlSkill Tests - Credentials
# ============================================================================


class TestCredentials:
    """Tests for credential operations."""

    @pytest.mark.asyncio
    async def test_verify_credentials_valid(self, cloudctl_skill: CloudctlSkill) -> None:
        """Test verifying valid credentials."""
        mock_result = CommandResult(
            success=True,
            status=CommandStatus.SUCCESS,
            output=json.dumps({"valid": True, "expires_in_seconds": 3600}),
        )

        with patch.object(cloudctl_skill, "_execute_cloudctl", return_value=mock_result):
            is_valid = await cloudctl_skill.verify_credentials("myorg")
            assert is_valid is True

    @pytest.mark.asyncio
    async def test_login_invalid_org(self, cloudctl_skill: CloudctlSkill) -> None:
        """Test login with invalid organization."""
        with pytest.raises(ValueError):
            await cloudctl_skill.login("")


# ============================================================================
# CloudctlSkill Tests - Health Check
# ============================================================================


class TestHealthCheck:
    """Tests for health check operations."""

    @pytest.mark.asyncio
    async def test_health_check_result(self) -> None:
        """Test health check result."""
        health = HealthCheckResult(
            is_healthy=True,
            cloudctl_installed=True,
            organizations_available=2,
            credentials_valid={"aws-prod": True, "gcp-prod": True},
            checks_passed=5,
            checks_failed=0,
        )

        assert health.is_healthy is True
        assert health.cloudctl_installed is True
        assert health.organizations_available == 2


# ============================================================================
# CloudctlSkill Tests - Multi-Cloud
# ============================================================================


class TestMultiCloud:
    """Tests for multi-cloud operations."""

    @pytest.mark.asyncio
    async def test_context_aws(self, aws_context: CloudContext) -> None:
        """Test AWS context."""
        assert aws_context.provider == CloudProvider.AWS
        assert aws_context.organization == "aws-prod"

    @pytest.mark.asyncio
    async def test_context_gcp(self, gcp_context: CloudContext) -> None:
        """Test GCP context."""
        assert gcp_context.provider == CloudProvider.GCP
        assert gcp_context.organization == "gcp-prod"

    @pytest.mark.asyncio
    async def test_azure_context(self) -> None:
        """Test Azure context."""
        azure_context = CloudContext(
            provider=CloudProvider.AZURE,
            organization="azure-prod",
            account_id="subscription-id",
            credentials_valid=True,
        )
        assert azure_context.provider == CloudProvider.AZURE


# ============================================================================
# CloudctlSkill Tests - Error Handling
# ============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_execute_cloudctl_not_found(self, cloudctl_skill: CloudctlSkill) -> None:
        """Test handling missing cloudctl."""
        with patch(
            "cloudctl_skill.skill.asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError(),
        ):
            result = await cloudctl_skill._execute_cloudctl("test")
            assert result.success is False
            assert "cloudctl not found" in result.error


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests requiring cloudctl."""

    def test_skill_initialization(self, skill_config: SkillConfig) -> None:
        """Test CloudctlSkill initialization."""
        skill = CloudctlSkill(config=skill_config)
        assert skill.config == skill_config

    def test_default_skill_initialization(self) -> None:
        """Test CloudctlSkill initialization with default config."""
        with patch("cloudctl_skill.skill.load_config") as mock_load_config:
            mock_config = SkillConfig()
            mock_load_config.return_value = mock_config

            skill = CloudctlSkill()
            assert skill.config is not None


# ============================================================================
# Async Tests
# ============================================================================


@pytest.mark.asyncio
async def test_async_operations() -> None:
    """Test async operations."""
    config = SkillConfig(dry_run=True)
    skill = CloudctlSkill(config=config)

    # Test operations with dry-run mode
    result = await skill._execute_cloudctl("test")
    assert result.success is True
    assert "[DRY RUN]" in result.output
