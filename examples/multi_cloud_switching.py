#!/usr/bin/env python3
"""Multi-cloud context switching examples."""

import asyncio
from cloudctl_skill import CloudctlSkill, CloudProvider


async def main() -> None:
    """Switch between multiple clouds."""
    skill = CloudctlSkill()

    # List all organizations
    orgs = await skill.list_organizations()

    # Group by provider
    aws_orgs = [o for o in orgs if o.get("provider") == "aws"]
    gcp_orgs = [o for o in orgs if o.get("provider") == "gcp"]
    azure_orgs = [o for o in orgs if o.get("provider") == "azure"]

    print("=== Multi-Cloud Organizations ===")
    if aws_orgs:
        print(f"\nAWS ({len(aws_orgs)}):")
        for org in aws_orgs:
            print(f"  • {org['name']}")

    if gcp_orgs:
        print(f"\nGCP ({len(gcp_orgs)}):")
        for org in gcp_orgs:
            print(f"  • {org['name']}")

    if azure_orgs:
        print(f"\nAzure ({len(azure_orgs)}):")
        for org in azure_orgs:
            print(f"  • {org['name']}")

    # Switch to AWS organization
    if aws_orgs:
        aws_org = aws_orgs[0]["name"]
        print(f"\n=== Switching to AWS: {aws_org} ===")
        result = await skill.switch_context(aws_org)
        if result.success:
            context = await skill.get_context()
            print(f"✅ Switched to {context}")
        else:
            print(f"❌ Failed: {result.error}")

    # Switch to GCP organization
    if gcp_orgs:
        gcp_org = gcp_orgs[0]["name"]
        print(f"\n=== Switching to GCP: {gcp_org} ===")
        result = await skill.switch_context(gcp_org)
        if result.success:
            context = await skill.get_context()
            print(f"✅ Switched to {context}")
        else:
            print(f"❌ Failed: {result.error}")

    # Check all credentials
    print(f"\n=== All Credentials Status ===")
    creds = await skill.check_all_credentials()
    for org, status in creds.items():
        valid = "✅" if status.get("valid") else "❌"
        print(f"{valid} {org}: {status}")


if __name__ == "__main__":
    asyncio.run(main())
