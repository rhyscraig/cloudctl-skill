#!/usr/bin/env python3
"""CloudctlSkill error handling examples."""

import asyncio
from cloudctl_skill import CloudctlSkill


async def main() -> None:
    """Error handling and recovery patterns."""
    skill = CloudctlSkill()

    # Example 1: Handle invalid organization
    print("=== Example 1: Invalid Organization ===")
    try:
        await skill.switch_context("non-existent-org")
    except ValueError as e:
        print(f"❌ ValueError: {e}")
    except RuntimeError as e:
        print(f"❌ RuntimeError: {e}")
    print()

    # Example 2: Ensure cloud access with auto-recovery
    print("=== Example 2: Ensure Cloud Access (Auto-Recovery) ===")
    result = await skill.ensure_cloud_access("myorg")
    if result["success"]:
        print(f"✅ Access confirmed: {result['context']}")
        if result.get("auto_refreshed"):
            print("   (Credentials were auto-refreshed)")
    else:
        print(f"❌ Access failed: {result['error']}")
        print(f"💡 Suggested fix: {result['fix']}")
    print()

    # Example 3: Handle timeout
    print("=== Example 3: Timeout Handling ===")
    # This would happen if cloudctl command takes too long
    # CloudctlSkill will auto-retry with exponential backoff
    try:
        orgs = await skill.list_organizations()
        print(f"✅ Listed {len(orgs)} organizations")
    except RuntimeError as e:
        print(f"❌ Failed after retries: {e}")
    print()

    # Example 4: Check credentials before operation
    print("=== Example 4: Pre-flight Credential Check ===")
    try:
        orgs = await skill.list_organizations()
        if orgs:
            org_name = orgs[0]["name"]
            is_valid = await skill.verify_credentials(org_name)
            if not is_valid:
                print(f"⚠️  Credentials invalid for {org_name}")
                result = await skill.login(org_name)
                if result.success:
                    print(f"✅ Refreshed credentials")
                else:
                    print(f"❌ Refresh failed: {result.error}")
            else:
                print(f"✅ Credentials valid for {org_name}")
    except RuntimeError as e:
        print(f"❌ Error: {e}")
    print()

    # Example 5: Health check before operations
    print("=== Example 5: Health Check Before Operations ===")
    health = await skill.health_check()
    if not health.is_healthy:
        print("⚠️  System is not healthy:")
        print(f"   cloudctl installed: {health.cloudctl_installed}")
        print(f"   organizations available: {health.organizations_available}")
        if health.checks_failed > 0:
            print(f"   {health.checks_failed} checks failed")
    else:
        print("✅ System is healthy")
        print(f"   cloudctl v{health.cloudctl_version}")
        print(f"   {health.organizations_available} organizations available")
        print(f"   {health.checks_passed}/{health.checks_passed + health.checks_failed} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
