#!/usr/bin/env python3
"""Basic CloudctlSkill usage examples."""

import asyncio
from cloudctl_skill import CloudctlSkill


async def main() -> None:
    """Basic CloudctlSkill examples."""
    skill = CloudctlSkill()

    # Get current context
    print("=== Current Context ===")
    context = await skill.get_context()
    print(f"Provider: {context.provider.value}")
    print(f"Organization: {context.organization}")
    print(f"Account: {context.account_id}")
    print(f"Region: {context.region}")
    print(f"Credentials Valid: {context.credentials_valid}")
    print()

    # List all organizations
    print("=== Available Organizations ===")
    orgs = await skill.list_organizations()
    for org in orgs:
        print(f"  • {org['name']} ({org['provider']})")
    print()

    # Check credentials for first org
    if orgs:
        org_name = orgs[0]["name"]
        print(f"=== Checking Credentials for {org_name} ===")
        is_valid = await skill.verify_credentials(org_name)
        print(f"Valid: {is_valid}")

        if is_valid:
            token_status = await skill.get_token_status(org_name)
            print(f"Token Valid: {token_status.valid}")
            if token_status.expires_in_seconds:
                print(f"Expires in: {token_status.expires_in_seconds}s")
        print()

    # Health check
    print("=== System Health ===")
    health = await skill.health_check()
    print(f"System Healthy: {health.is_healthy}")
    print(f"cloudctl Installed: {health.cloudctl_installed}")
    print(f"cloudctl Version: {health.cloudctl_version}")
    print(f"Organizations Available: {health.organizations_available}")
    print(f"Checks Passed: {health.checks_passed}")
    print(f"Checks Failed: {health.checks_failed}")
    print()

    # Ensure cloud access (recommended for operations)
    if orgs:
        org_name = orgs[0]["name"]
        print(f"=== Ensuring Cloud Access for {org_name} ===")
        result = await skill.ensure_cloud_access(org_name)
        if result["success"]:
            print(f"✅ Access Confirmed: {result['context']}")
            if result["auto_refreshed"]:
                print("   (Token was auto-refreshed)")
        else:
            print(f"❌ Access Failed: {result['error']}")
            print(f"   Fix: {result['fix']}")


if __name__ == "__main__":
    asyncio.run(main())
