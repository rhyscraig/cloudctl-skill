"""Comprehensive tests for cloudctl_skill.oci_handler.

Covers:
  - Configuration detection helpers
  - Config parsing
  - Async CLI runner
  - get_oci_context
  - verify_oci_auth
  - oci_login
  - is_oci_org
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cloudctl_skill.models import CloudProvider, CommandStatus, TokenStatus
from cloudctl_skill.oci_handler import (
    OCIHandlerError,
    _is_oci_configured,
    _read_oci_config,
    _run_oci_async,
    get_oci_context,
    is_oci_org,
    oci_login,
    verify_oci_auth,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_CONFIG_TEXT = """\
[DEFAULT]
user=ocid1.user.oc1..AAAAAA
fingerprint=aa:bb:cc:dd
tenancy=ocid1.tenancy.oc1..TTTTTT
region=eu-frankfurt-1
key_file=~/.oci/key.pem

[STAGING]
user=ocid1.user.oc1..STAGING
fingerprint=11:22:33:44
tenancy=ocid1.tenancy.oc1..STAGING_T
region=us-ashburn-1
key_file=~/.oci/staging.pem
"""


def _fake_config_path(tmp_path: Path) -> Path:
    cfg = tmp_path / ".oci" / "config"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(FAKE_CONFIG_TEXT)
    return cfg


# ---------------------------------------------------------------------------
# _is_oci_configured
# ---------------------------------------------------------------------------


class TestIsOciConfigured:
    def test_returns_true_when_config_exists(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg):
            assert _is_oci_configured() is True

    def test_returns_false_when_config_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent" / "config"
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", missing):
            assert _is_oci_configured() is False

    def test_returns_false_when_config_empty(self, tmp_path: Path) -> None:
        cfg = tmp_path / ".oci" / "config"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("")
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg):
            assert _is_oci_configured() is False


# ---------------------------------------------------------------------------
# _read_oci_config
# ---------------------------------------------------------------------------


class TestReadOciConfig:
    def test_reads_default_profile(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg):
            result = _read_oci_config("DEFAULT")
        assert result["user"] == "ocid1.user.oc1..AAAAAA"
        assert result["tenancy"] == "ocid1.tenancy.oc1..TTTTTT"
        assert result["region"] == "eu-frankfurt-1"

    def test_reads_named_profile(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg):
            result = _read_oci_config("STAGING")
        assert result["region"] == "us-ashburn-1"
        assert result["tenancy"] == "ocid1.tenancy.oc1..STAGING_T"

    def test_raises_when_not_configured(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent" / "config"
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", missing):
            with pytest.raises(OCIHandlerError, match="not configured"):
                _read_oci_config()

    def test_raises_when_profile_not_found(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg):
            with pytest.raises(OCIHandlerError, match="not found"):
                _read_oci_config("MISSING_PROFILE")


# ---------------------------------------------------------------------------
# _run_oci_async
# ---------------------------------------------------------------------------


class TestRunOciAsync:
    @pytest.mark.asyncio
    async def test_success_returns_zero_rc_and_output(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"hello", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            rc, stdout, stderr = await _run_oci_async(["iam", "user", "get", "--user-id", "xxx"])

        assert rc == 0
        assert stdout == "hello"
        assert stderr == ""

    @pytest.mark.asyncio
    async def test_failure_returns_nonzero_rc(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"ServiceError"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            rc, stdout, stderr = await _run_oci_async(["bad", "cmd"])

        assert rc == 1
        assert "ServiceError" in stderr

    @pytest.mark.asyncio
    async def test_timeout_kills_process_and_returns_error(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = None
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_proc.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            rc, stdout, stderr = await _run_oci_async(["slow", "cmd"], timeout=1)

        assert rc == 1
        assert stdout == ""
        assert "timed out" in stderr.lower()
        mock_proc.kill.assert_called_once()


# ---------------------------------------------------------------------------
# get_oci_context
# ---------------------------------------------------------------------------


class TestGetOciContext:
    @pytest.mark.asyncio
    async def test_returns_cloud_context(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg):
            ctx = await get_oci_context("my-oci-org")

        assert ctx.provider == CloudProvider.OCI
        assert ctx.organization == "my-oci-org"
        assert ctx.account_id == "ocid1.tenancy.oc1..TTTTTT"
        assert ctx.region == "eu-frankfurt-1"
        assert ctx.role == "ocid1.user.oc1..AAAAAA"
        assert ctx.credentials_valid is True

    @pytest.mark.asyncio
    async def test_uses_named_profile(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg):
            ctx = await get_oci_context("staging-oci", profile="STAGING")

        assert ctx.organization == "staging-oci"
        assert ctx.region == "us-ashburn-1"

    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self, tmp_path: Path) -> None:
        missing = tmp_path / "no" / "config"
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", missing):
            with pytest.raises(OCIHandlerError):
                await get_oci_context("my-oci-org")


# ---------------------------------------------------------------------------
# verify_oci_auth
# ---------------------------------------------------------------------------


class TestVerifyOciAuth:
    @pytest.mark.asyncio
    async def test_returns_invalid_when_not_configured(self, tmp_path: Path) -> None:
        missing = tmp_path / "no" / "config"
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", missing):
            status = await verify_oci_auth()

        assert status.valid is False

    @pytest.mark.asyncio
    async def test_returns_invalid_when_profile_missing(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg):
            status = await verify_oci_auth(profile="NO_SUCH_PROFILE")

        assert status.valid is False

    @pytest.mark.asyncio
    async def test_returns_invalid_when_api_call_fails(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with (
            patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg),
            patch(
                "cloudctl_skill.oci_handler._run_oci_async",
                AsyncMock(return_value=(1, "", "ServiceError: 401")),
            ),
        ):
            status = await verify_oci_auth()

        assert status.valid is False

    @pytest.mark.asyncio
    async def test_returns_invalid_when_json_decode_fails(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with (
            patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg),
            patch(
                "cloudctl_skill.oci_handler._run_oci_async",
                AsyncMock(return_value=(0, "not-valid-json{{{", "")),
            ),
        ):
            status = await verify_oci_auth()

        assert status.valid is False

    @pytest.mark.asyncio
    async def test_returns_valid_on_successful_api_call(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        api_response = json.dumps({"data": {"name": "craig"}})
        with (
            patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg),
            patch(
                "cloudctl_skill.oci_handler._run_oci_async",
                AsyncMock(return_value=(0, api_response, "")),
            ),
        ):
            status = await verify_oci_auth()

        assert status.valid is True

    @pytest.mark.asyncio
    async def test_passes_profile_flag_for_non_default(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        api_response = json.dumps({"data": {"name": "craig"}})
        captured: list[Any] = []

        async def _capture(*args: Any, **kwargs: Any) -> tuple[int, str, str]:
            captured.extend(args[0])
            return 0, api_response, ""

        with (
            patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg),
            patch("cloudctl_skill.oci_handler._run_oci_async", side_effect=_capture),
        ):
            await verify_oci_auth(profile="STAGING")

        assert "--profile" in captured
        assert "STAGING" in captured

    @pytest.mark.asyncio
    async def test_no_profile_flag_for_default(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        api_response = json.dumps({"data": {}})
        captured: list[Any] = []

        async def _capture(*args: Any, **kwargs: Any) -> tuple[int, str, str]:
            captured.extend(args[0])
            return 0, api_response, ""

        with (
            patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg),
            patch("cloudctl_skill.oci_handler._run_oci_async", side_effect=_capture),
        ):
            await verify_oci_auth(profile="DEFAULT")

        assert "--profile" not in captured


# ---------------------------------------------------------------------------
# oci_login
# ---------------------------------------------------------------------------


class TestOciLogin:
    @pytest.mark.asyncio
    async def test_returns_failure_when_not_configured(self, tmp_path: Path) -> None:
        missing = tmp_path / "no" / "config"
        with patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", missing):
            result = await oci_login("my-org")

        assert result.success is False
        assert result.status == CommandStatus.FAILURE
        assert "not configured" in result.error.lower()

    @pytest.mark.asyncio
    async def test_returns_success_when_auth_valid(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        api_response = json.dumps({"data": {"name": "craig"}})
        with (
            patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg),
            patch(
                "cloudctl_skill.oci_handler._run_oci_async",
                AsyncMock(return_value=(0, api_response, "")),
            ),
        ):
            result = await oci_login("my-org")

        assert result.success is True
        assert result.status == CommandStatus.SUCCESS
        assert "my-org" in result.output
        assert "eu-frankfurt-1" in result.output

    @pytest.mark.asyncio
    async def test_returns_failure_when_auth_invalid(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        with (
            patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg),
            patch(
                "cloudctl_skill.oci_handler._run_oci_async",
                AsyncMock(return_value=(1, "", "ServiceError 401")),
            ),
        ):
            result = await oci_login("my-org")

        assert result.success is False
        assert "failed" in result.error.lower()
        assert result.fix is not None

    @pytest.mark.asyncio
    async def test_returns_failure_when_config_read_fails(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        # Patch verify_oci_auth to return valid so the auth check passes,
        # then patch _read_oci_config to blow up on the subsequent read.
        with (
            patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg),
            patch(
                "cloudctl_skill.oci_handler.verify_oci_auth",
                AsyncMock(return_value=TokenStatus(valid=True)),
            ),
            patch(
                "cloudctl_skill.oci_handler._read_oci_config",
                side_effect=OCIHandlerError("config blown up"),
            ),
        ):
            result = await oci_login("my-org")

        assert result.success is False
        assert "config blown up" in result.error

    @pytest.mark.asyncio
    async def test_uses_named_profile(self, tmp_path: Path) -> None:
        cfg = _fake_config_path(tmp_path)
        api_response = json.dumps({"data": {}})
        with (
            patch("cloudctl_skill.oci_handler.OCI_CONFIG_PATH", cfg),
            patch(
                "cloudctl_skill.oci_handler._run_oci_async",
                AsyncMock(return_value=(0, api_response, "")),
            ),
        ):
            result = await oci_login("staging-org", profile="STAGING")

        assert result.success is True
        assert "us-ashburn-1" in result.output


# ---------------------------------------------------------------------------
# is_oci_org
# ---------------------------------------------------------------------------


class TestIsOciOrg:
    def test_returns_true_for_oci_provider(self) -> None:
        assert is_oci_org({"provider": "oci"}) is True

    def test_returns_true_for_uppercase_oci(self) -> None:
        assert is_oci_org({"provider": "OCI"}) is True

    def test_returns_true_for_mixed_case(self) -> None:
        assert is_oci_org({"provider": "Oci"}) is True

    def test_returns_false_for_aws(self) -> None:
        assert is_oci_org({"provider": "aws"}) is False

    def test_returns_false_for_gcp(self) -> None:
        assert is_oci_org({"provider": "gcp"}) is False

    def test_returns_false_for_azure(self) -> None:
        assert is_oci_org({"provider": "azure"}) is False

    def test_returns_false_for_empty_dict(self) -> None:
        assert is_oci_org({}) is False

    def test_returns_false_when_provider_key_missing(self) -> None:
        assert is_oci_org({"name": "my-org"}) is False
