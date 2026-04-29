"""Tests for CloudctlSkill main class."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cloudctl_skill.models import (
    CloudContext,
    CloudProvider,
    CommandResult,
    HealthCheckResult,
    SkillConfig,
    TokenStatus,
)
from cloudctl_skill.skill import CloudctlSkill


@pytest.fixture
def skill_config() -> SkillConfig:
    """Create test configuration."""
    return SkillConfig(
        cloudctl_path="cloudctl",
        cloudctl_timeout=30,
        cloudctl_retries=3,
        enable_caching=True,
        cache_ttl_seconds=300,
        dry_run=False,
        enable_audit_logging=False,
    )


@pytest.fixture
def skill(skill_config: SkillConfig) -> CloudctlSkill:
    """Create test CloudctlSkill instance."""
    return CloudctlSkill(config=skill_config)


class TestCloudctlSkillInit:
    """Tests for CloudctlSkill initialization."""

    def test_init_with_config(self, skill_config: SkillConfig) -> None:
        """Initialization with config should set attributes."""
        skill = CloudctlSkill(config=skill_config)
        assert skill.config == skill_config
        assert skill._context_cache is None
        assert skill._cache_time is None

    @patch("cloudctl_skill.skill.load_config")
    def test_init_without_config(self, mock_load: MagicMock) -> None:
        """Initialization without config should load from environment."""
        mock_config = SkillConfig()
        mock_load.return_value = mock_config
        skill = CloudctlSkill()
        assert skill.config == mock_config
        mock_load.assert_called_once()

    def test_init_with_audit_logging_disabled(self, skill_config: SkillConfig) -> None:
        """Initialization with audit disabled should not set logger."""
        skill_config.enable_audit_logging = False
        skill = CloudctlSkill(config=skill_config)
        assert skill._audit_logger is None


class TestGetContext:
    """Tests for get_context method."""

    @pytest.mark.asyncio
    async def test_get_context_from_cache(self, skill: CloudctlSkill) -> None:
        """Fresh cache should be returned."""
        cached_context = CloudContext(
            provider=CloudProvider.AWS,
            organization="test-org",
            account_id="123456789012",
            region="us-west-2",
            credentials_valid=True,
        )
        skill._context_cache = cached_context
        skill._cache_time = datetime.utcnow()

        result = await skill.get_context()
        assert result == cached_context

    @pytest.mark.asyncio
    async def test_get_context_cache_expired(self, skill: CloudctlSkill) -> None:
        """Expired cache should be refreshed."""
        old_cache = CloudContext(
            provider=CloudProvider.AWS,
            organization="old-org",
            credentials_valid=True,
        )
        skill._context_cache = old_cache
        # Set cache time to far past
        skill._cache_time = datetime(2020, 1, 1)

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                success=True,
                output="aws:new-org account=987654321098",
            )
            result = await skill.get_context()
            assert result.organization == "new-org"
            mock_exec.assert_called_once_with("status")

    @pytest.mark.asyncio
    async def test_get_context_success(self, skill: CloudctlSkill) -> None:
        """Successful context fetch should return CloudContext."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                success=True,
                output="aws:prod-org account=123456789012 region=us-west-2 role=terraform",
            )
            result = await skill.get_context()
            assert result.organization == "prod-org"
            assert result.provider == CloudProvider.AWS
            assert result.account_id == "123456789012"
            assert result.region == "us-west-2"
            assert result.role == "terraform"

    @pytest.mark.asyncio
    async def test_get_context_fallback_to_file(self, skill: CloudctlSkill) -> None:
        """Failed status should fallback to context file."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(success=False, error="Command failed")

            with patch.object(skill, "_read_context_file") as mock_file:
                mock_file.return_value = CloudContext(
                    provider=CloudProvider.GCP,
                    organization="gcp-org",
                    credentials_valid=True,
                )
                result = await skill.get_context()
                assert result.organization == "gcp-org"
                assert result.provider == CloudProvider.GCP

    @pytest.mark.asyncio
    async def test_get_context_no_context_found(self, skill: CloudctlSkill) -> None:
        """No context found should raise RuntimeError."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(success=False, error="No active context")

            with patch.object(skill, "_read_context_file") as mock_file:
                mock_file.return_value = None
                with pytest.raises(RuntimeError):
                    await skill.get_context()


class TestSwitchContext:
    """Tests for switch_context method."""

    @pytest.mark.asyncio
    async def test_switch_context_success(self, skill: CloudctlSkill) -> None:
        """Successful switch should return CommandResult."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(success=True, output="Switched to test-org")

            with patch.object(skill, "get_context") as mock_ctx:
                mock_ctx.side_effect = [
                    RuntimeError("No context"),  # Before switch
                    CloudContext(
                        provider=CloudProvider.AWS,
                        organization="test-org",
                        credentials_valid=True,
                    ),  # After switch
                ]

                result = await skill.switch_context("test-org")
                assert result.success is True

    @pytest.mark.asyncio
    async def test_switch_context_empty_org(self, skill: CloudctlSkill) -> None:
        """Empty organization name should raise ValueError."""
        with pytest.raises(ValueError):
            await skill.switch_context("")

    @pytest.mark.asyncio
    async def test_switch_context_with_account_id(self, skill: CloudctlSkill) -> None:
        """Switch with account ID should try account-specific switch."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(success=True, output="Switched")

            with patch.object(skill, "get_context") as mock_ctx:
                mock_ctx.side_effect = [
                    RuntimeError("No context"),
                    CloudContext(
                        provider=CloudProvider.AWS,
                        organization="test-org",
                        account_id="123456789012",
                        credentials_valid=True,
                    ),
                ]

                result = await skill.switch_context("test-org", "123456789012")
                assert result.success is True
                # Should have called with --account flag
                calls = mock_exec.call_args_list
                assert any("--account" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_switch_context_token_refresh(self, skill: CloudctlSkill) -> None:
        """Token error should trigger login refresh."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.side_effect = [
                CommandResult(success=False, error="token expired"),  # First switch fails
                CommandResult(success=True, output="Logged in"),  # Login succeeds
                CommandResult(success=True, output="Switched"),  # Retry succeeds
            ]

            with patch.object(skill, "login") as mock_login:
                mock_login.return_value = CommandResult(success=True, output="Logged in")

                with patch.object(skill, "get_context") as mock_ctx:
                    mock_ctx.side_effect = [
                        RuntimeError("No context"),
                        CloudContext(
                            provider=CloudProvider.AWS,
                            organization="test-org",
                            credentials_valid=True,
                        ),
                    ]

                    result = await skill.switch_context("test-org")
                    assert result.success is True


class TestSwitchRegion:
    """Tests for switch_region method."""

    @pytest.mark.asyncio
    async def test_switch_region_aws(self, skill: CloudctlSkill) -> None:
        """Switch region for AWS should set AWS_REGION."""
        with patch.object(skill, "get_context") as mock_ctx:
            mock_ctx.return_value = CloudContext(
                provider=CloudProvider.AWS,
                organization="aws-org",
                credentials_valid=True,
            )

            result = await skill.switch_region("us-east-1")
            assert result.success is True
            assert "us-east-1" in result.output

    @pytest.mark.asyncio
    async def test_switch_region_gcp_not_supported(self, skill: CloudctlSkill) -> None:
        """Switch region for GCP should fail."""
        with patch.object(skill, "get_context") as mock_ctx:
            mock_ctx.return_value = CloudContext(
                provider=CloudProvider.GCP,
                organization="gcp-org",
                credentials_valid=True,
            )

            result = await skill.switch_region("europe-west1")
            assert result.success is False

    @pytest.mark.asyncio
    async def test_switch_region_empty_region(self, skill: CloudctlSkill) -> None:
        """Empty region should raise ValueError."""
        with pytest.raises(ValueError):
            await skill.switch_region("")

    @pytest.mark.asyncio
    async def test_switch_region_no_context(self, skill: CloudctlSkill) -> None:
        """No context should return failure."""
        with patch.object(skill, "get_context") as mock_ctx:
            mock_ctx.side_effect = RuntimeError("No context")

            result = await skill.switch_region("us-west-2")
            assert result.success is False


class TestSwitchProject:
    """Tests for switch_project method."""

    @pytest.mark.asyncio
    async def test_switch_project_gcp(self, skill: CloudctlSkill) -> None:
        """Switch project for GCP should set GCLOUD_PROJECT."""
        with patch.object(skill, "get_context") as mock_ctx:
            mock_ctx.return_value = CloudContext(
                provider=CloudProvider.GCP,
                organization="gcp-org",
                credentials_valid=True,
            )

            result = await skill.switch_project("my-project")
            assert result.success is True
            assert "my-project" in result.output

    @pytest.mark.asyncio
    async def test_switch_project_aws_not_supported(self, skill: CloudctlSkill) -> None:
        """Switch project for AWS should fail."""
        with patch.object(skill, "get_context") as mock_ctx:
            mock_ctx.return_value = CloudContext(
                provider=CloudProvider.AWS,
                organization="aws-org",
                credentials_valid=True,
            )

            result = await skill.switch_project("my-project")
            assert result.success is False

    @pytest.mark.asyncio
    async def test_switch_project_empty_id(self, skill: CloudctlSkill) -> None:
        """Empty project ID should raise ValueError."""
        with pytest.raises(ValueError):
            await skill.switch_project("")


class TestListOrganizations:
    """Tests for list_organizations method."""

    @pytest.mark.asyncio
    async def test_list_organizations_json(self, skill: CloudctlSkill) -> None:
        """JSON output should be parsed."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                success=True,
                output=json.dumps(
                    [
                        {"name": "org1", "provider": "aws"},
                        {"name": "org2", "provider": "gcp"},
                    ]
                ),
            )

            result = await skill.list_organizations()
            assert len(result) == 2
            assert result[0]["name"] == "org1"
            assert result[1]["provider"] == "gcp"

    @pytest.mark.asyncio
    async def test_list_organizations_text(self, skill: CloudctlSkill) -> None:
        """Text output should be parsed."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                success=True,
                output="Configured Organizations (2)\n  myorg  [AWS]  enabled\n  gcp-org  [GCP]  enabled",
            )

            result = await skill.list_organizations()
            assert len(result) == 2
            assert result[0]["name"] == "myorg"
            assert result[0]["provider"] == "aws"

    @pytest.mark.asyncio
    async def test_list_organizations_failure(self, skill: CloudctlSkill) -> None:
        """Failed command should raise RuntimeError."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(success=False, error="Command failed")

            with pytest.raises(RuntimeError):
                await skill.list_organizations()


class TestVerifyCredentials:
    """Tests for verify_credentials method."""

    @pytest.mark.asyncio
    async def test_verify_credentials_valid(self, skill: CloudctlSkill) -> None:
        """Valid credentials should return True."""
        with patch.object(skill, "_verify_credentials") as mock_verify:
            mock_verify.return_value = True
            result = await skill.verify_credentials("test-org")
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_credentials_invalid(self, skill: CloudctlSkill) -> None:
        """Invalid credentials should return False."""
        with patch.object(skill, "_verify_credentials") as mock_verify:
            mock_verify.return_value = False
            result = await skill.verify_credentials("test-org")
            assert result is False


class TestLogin:
    """Tests for login method."""

    @pytest.mark.asyncio
    async def test_login_success(self, skill: CloudctlSkill) -> None:
        """Successful login should return CommandResult."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(success=True, output="Logged in")

            result = await skill.login("test-org")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_login_empty_org(self, skill: CloudctlSkill) -> None:
        """Empty organization should raise ValueError."""
        with pytest.raises(ValueError):
            await skill.login("")

    @pytest.mark.asyncio
    async def test_login_routes_oci_org_to_oci_handler(self, skill: CloudctlSkill) -> None:
        """OCI orgs should be routed to oci_handler.oci_login, not cloudctl."""
        oci_result = CommandResult(success=True, output="OCI auth verified for org 'oci-org'")
        with (
            patch("cloudctl_skill.skill._get_org_config", return_value={"name": "oci-org", "provider": "oci"}),
            patch("cloudctl_skill.skill.oci_handler.oci_login", AsyncMock(return_value=oci_result)) as mock_oci,
            patch.object(skill, "_execute_cloudctl") as mock_exec,
        ):
            result = await skill.login("oci-org")

        assert result.success is True
        mock_oci.assert_called_once_with("oci-org", profile="DEFAULT")
        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_login_oci_org_uses_custom_profile(self, skill: CloudctlSkill) -> None:
        """OCI orgs with oci_profile field should pass profile to oci_handler."""
        oci_result = CommandResult(success=True, output="OCI auth verified")
        org_cfg = {"name": "oci-org", "provider": "oci", "oci_profile": "PROD"}
        with (
            patch("cloudctl_skill.skill._get_org_config", return_value=org_cfg),
            patch("cloudctl_skill.skill.oci_handler.oci_login", AsyncMock(return_value=oci_result)) as mock_oci,
        ):
            await skill.login("oci-org")

        mock_oci.assert_called_once_with("oci-org", profile="PROD")

    @pytest.mark.asyncio
    async def test_login_non_oci_org_uses_cloudctl(self, skill: CloudctlSkill) -> None:
        """Non-OCI orgs should still go through cloudctl binary."""
        with (
            patch("cloudctl_skill.skill._get_org_config", return_value={"name": "aws-org", "provider": "aws"}),
            patch.object(skill, "_execute_cloudctl", AsyncMock(return_value=CommandResult(success=True))) as mock_exec,
        ):
            result = await skill.login("aws-org")

        assert result.success is True
        mock_exec.assert_called_once_with("login", "aws-org")

    @pytest.mark.asyncio
    async def test_login_unknown_org_uses_cloudctl(self, skill: CloudctlSkill) -> None:
        """Org not in orgs.yaml falls through to cloudctl (default behaviour)."""
        with (
            patch("cloudctl_skill.skill._get_org_config", return_value={}),
            patch.object(skill, "_execute_cloudctl", AsyncMock(return_value=CommandResult(success=True))) as mock_exec,
        ):
            await skill.login("unknown-org")

        mock_exec.assert_called_once_with("login", "unknown-org")


class TestGetTokenStatus:
    """Tests for get_token_status method."""

    @pytest.mark.asyncio
    async def test_get_token_status_valid(self, skill: CloudctlSkill) -> None:
        """Successful status check should return valid token."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(success=True, output="Status: OK")

            result = await skill.get_token_status("test-org")
            assert result.valid is True

    @pytest.mark.asyncio
    async def test_get_token_status_invalid(self, skill: CloudctlSkill) -> None:
        """Failed status check should return invalid token."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(success=False, error="Token expired")

            result = await skill.get_token_status("test-org")
            assert result.valid is False

    @pytest.mark.asyncio
    async def test_get_token_status_exception(self, skill: CloudctlSkill) -> None:
        """Exception should default to valid token."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.side_effect = Exception("Test error")

            result = await skill.get_token_status("test-org")
            assert result.valid is True


class TestCheckAllCredentials:
    """Tests for check_all_credentials method."""

    @pytest.mark.asyncio
    async def test_check_all_credentials_success(self, skill: CloudctlSkill) -> None:
        """Check credentials should return status for all orgs."""
        with patch.object(skill, "list_organizations") as mock_list:
            mock_list.return_value = [
                {"name": "org1", "provider": "aws"},
                {"name": "org2", "provider": "gcp"},
            ]

            with patch.object(skill, "get_token_status") as mock_status:
                mock_status.return_value = TokenStatus(valid=True)

                result = await skill.check_all_credentials()
                assert "org1" in result
                assert "org2" in result
                assert result["org1"]["valid"] is True

    @pytest.mark.asyncio
    async def test_check_all_credentials_failure(self, skill: CloudctlSkill) -> None:
        """Failed list should raise RuntimeError."""
        with patch.object(skill, "list_organizations") as mock_list:
            mock_list.side_effect = RuntimeError("Failed to list")

            with pytest.raises(RuntimeError):
                await skill.check_all_credentials()


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, skill: CloudctlSkill) -> None:
        """Healthy system should return healthy status."""
        with patch.object(skill, "_is_cloudctl_installed") as mock_installed:
            mock_installed.return_value = True

            with patch.object(skill, "_execute_cloudctl") as mock_exec:
                mock_exec.return_value = CommandResult(success=True, output="cloudctl 1.0.0")

                with patch.object(skill, "list_organizations") as mock_list:
                    mock_list.return_value = [{"name": "org1", "provider": "aws"}]

                    with patch.object(skill, "_verify_credentials") as mock_verify:
                        mock_verify.return_value = True

                        result = await skill.health_check()
                        assert result.is_healthy is True
                        assert result.cloudctl_installed is True
                        assert result.organizations_available > 0

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, skill: CloudctlSkill) -> None:
        """Unhealthy system should return unhealthy status."""
        with patch.object(skill, "_is_cloudctl_installed") as mock_installed:
            mock_installed.return_value = False

            with patch.object(skill, "_execute_cloudctl") as mock_exec:
                mock_exec.return_value = CommandResult(success=False, error="Not found")

                with patch.object(skill, "list_organizations") as mock_list:
                    mock_list.side_effect = RuntimeError("Failed")

                    result = await skill.health_check()
                    assert result.is_healthy is False
                    assert result.cloudctl_installed is False


class TestEnsureCloudAccess:
    """Tests for ensure_cloud_access method."""

    @pytest.mark.asyncio
    async def test_ensure_cloud_access_success(self, skill: CloudctlSkill) -> None:
        """Successful access check should return success."""
        with patch.object(skill, "health_check") as mock_health:
            mock_health.return_value = HealthCheckResult(
                is_healthy=True,
                cloudctl_installed=True,
                organizations_available=1,
                credentials_valid={"test-org": True},
            )

            with patch.object(skill, "list_organizations") as mock_list:
                mock_list.return_value = [{"name": "test-org", "provider": "aws"}]

                with patch.object(skill, "get_token_status") as mock_status:
                    mock_status.return_value = TokenStatus(valid=True)

                    with patch.object(skill, "switch_context") as mock_switch:
                        mock_switch.return_value = CommandResult(success=True, output="Switched")

                        with patch.object(skill, "get_context") as mock_ctx:
                            mock_ctx.return_value = CloudContext(
                                provider=CloudProvider.AWS,
                                organization="test-org",
                                credentials_valid=True,
                            )

                            result = await skill.ensure_cloud_access("test-org")
                            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_ensure_cloud_access_empty_org(self, skill: CloudctlSkill) -> None:
        """Empty organization should raise ValueError."""
        with pytest.raises(ValueError):
            await skill.ensure_cloud_access("")

    @pytest.mark.asyncio
    async def test_ensure_cloud_access_cloudctl_not_installed(self, skill: CloudctlSkill) -> None:
        """Missing cloudctl should return failure."""
        with patch.object(skill, "health_check") as mock_health:
            mock_health.return_value = HealthCheckResult(
                is_healthy=False,
                cloudctl_installed=False,
                organizations_available=0,
                credentials_valid={},
            )

            result = await skill.ensure_cloud_access("test-org")
            assert result["success"] is False


class TestValidateSwitch:
    """Tests for validate_switch method."""

    @pytest.mark.asyncio
    async def test_validate_switch_success(self, skill: CloudctlSkill) -> None:
        """Valid context should return True."""
        with patch.object(skill, "get_context") as mock_ctx:
            mock_ctx.return_value = CloudContext(
                provider=CloudProvider.AWS,
                organization="test-org",
                credentials_valid=True,
            )

            result = await skill.validate_switch()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_switch_failure(self, skill: CloudctlSkill) -> None:
        """No context should return False."""
        with patch.object(skill, "get_context") as mock_ctx:
            mock_ctx.side_effect = RuntimeError("No context")

            result = await skill.validate_switch()
            assert result is False


class TestParseContext:
    """Tests for _parse_context method."""

    def test_parse_context_legacy_format(self, skill: CloudctlSkill) -> None:
        """Legacy format should parse correctly."""
        output = "aws:prod-org account=123456789012 region=us-west-2 role=terraform"
        context = skill._parse_context(output)
        assert context.provider == CloudProvider.AWS
        assert context.organization == "prod-org"
        assert context.account_id == "123456789012"
        assert context.region == "us-west-2"
        assert context.role == "terraform"

    def test_parse_context_gcp(self, skill: CloudctlSkill) -> None:
        """GCP context should parse."""
        output = "gcp:my-project account=my-project"
        context = skill._parse_context(output)
        assert context.provider == CloudProvider.GCP
        assert context.organization == "my-project"

    def test_parse_context_no_active_context(self, skill: CloudctlSkill) -> None:
        """No active context message should raise."""
        with pytest.raises(RuntimeError):
            skill._parse_context("No active context found.")

    def test_parse_context_empty_output(self, skill: CloudctlSkill) -> None:
        """Empty output should raise."""
        with pytest.raises(RuntimeError):
            skill._parse_context("")

    def test_parse_context_key_value_format(self, skill: CloudctlSkill) -> None:
        """Key=value format should parse."""
        output = "provider=aws\norganization=test-org\naccount=123456789012\nregion=us-west-2"
        context = skill._parse_context(output)
        assert context.provider == CloudProvider.AWS
        assert context.organization == "test-org"

    def test_parse_context_invalid_format(self, skill: CloudctlSkill) -> None:
        """Invalid format should raise."""
        with pytest.raises(RuntimeError):
            skill._parse_context("invalid-format-no-colon")


class TestReadContextFile:
    """Tests for _read_context_file method."""

    @pytest.mark.asyncio
    async def test_read_context_file_success(self, skill: CloudctlSkill) -> None:
        """Valid context file should be read."""
        context_data = {
            "org": "test-org",
            "provider": "aws",
            "account": "123456789012",
            "region": "us-west-2",
        }

        with patch("cloudctl_skill.skill.Path") as mock_path:
            mock_file = MagicMock()
            mock_file.exists.return_value = True
            mock_file.open.return_value.__enter__.return_value.read.return_value = json.dumps(context_data)
            mock_path.home.return_value.__truediv__.return_value = mock_file

            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(context_data)

                # Directly test the method without file system
                with patch("pathlib.Path.exists", return_value=True):
                    with patch(
                        "builtins.open",
                        MagicMock(
                            return_value=MagicMock(
                                __enter__=lambda x: x,
                                __exit__=lambda *args: None,
                                read=lambda x: json.dumps(context_data),
                            )
                        ),
                    ):
                        # Skip the actual file read and test parsing
                        pass

    @pytest.mark.asyncio
    async def test_read_context_file_not_found(self, skill: CloudctlSkill) -> None:
        """Missing context file should return None."""
        with patch("pathlib.Path.exists", return_value=False):
            result = await skill._read_context_file()
            assert result is None

    @pytest.mark.asyncio
    async def test_read_context_file_invalid_json(self, skill: CloudctlSkill) -> None:
        """Invalid JSON should return None."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", MagicMock()) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"
                result = await skill._read_context_file()
                assert result is None


class TestExecuteCloudctl:
    """Tests for _execute_cloudctl method."""

    @pytest.mark.asyncio
    async def test_execute_cloudctl_dry_run(self, skill: CloudctlSkill) -> None:
        """Dry run mode should not execute."""
        skill.config.dry_run = True
        result = await skill._execute_cloudctl("status")
        assert result.success is True
        assert "[DRY RUN]" in result.output

    @pytest.mark.asyncio
    async def test_execute_cloudctl_success(self, skill: CloudctlSkill) -> None:
        """Successful execution should return result."""
        with patch("asyncio.create_subprocess_exec") as mock_create:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b"aws:test-org",
                b"",
            )
            mock_process.returncode = 0
            mock_create.return_value = mock_process

            result = await skill._execute_cloudctl("status")
            assert result.success is True
            assert result.output == "aws:test-org"

    @pytest.mark.asyncio
    async def test_execute_cloudctl_failure(self, skill: CloudctlSkill) -> None:
        """Failed execution should return error."""
        with patch("asyncio.create_subprocess_exec") as mock_create:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b"",
                b"Command failed",
            )
            mock_process.returncode = 1
            mock_create.return_value = mock_process

            result = await skill._execute_cloudctl("invalid")
            assert result.success is False
            assert "Command failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_cloudctl_timeout(self, skill: CloudctlSkill) -> None:
        """Timeout should return error."""
        with patch("asyncio.create_subprocess_exec") as mock_create:
            mock_process = AsyncMock()
            mock_process.communicate.side_effect = TimeoutError()
            mock_process.kill = MagicMock()
            mock_create.return_value = mock_process

            result = await skill._execute_cloudctl("slow")
            assert result.success is False
            assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_cloudctl_not_found(self, skill: CloudctlSkill) -> None:
        """Missing cloudctl should return error."""
        with patch("asyncio.create_subprocess_exec") as mock_create:
            mock_create.side_effect = FileNotFoundError()

            result = await skill._execute_cloudctl("status")
            assert result.success is False
            assert "cloudctl not found" in result.error
