"""MCP (Model Context Protocol) server for CloudctlSkill.

This module provides the MCP interface for CloudctlSkill, enabling integration
with Claude and other LLM applications via the Model Context Protocol.
"""

import asyncio
import json
import sys
from typing import Any, Optional

from cloudctl_skill import CloudctlSkill


class CloudctlMCPServer:
    """MCP server for CloudctlSkill."""

    def __init__(self):
        """Initialize the MCP server."""
        self.skill = CloudctlSkill()

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP request.

        Args:
            request: MCP request with method and params

        Returns:
            MCP response with result or error
        """
        try:
            method = request.get("method")
            params = request.get("params", {})

            if method == "context":
                result = await self.skill.get_context()
                return {"result": str(result)}

            elif method == "switch":
                org = params.get("organization")
                if not org:
                    return {"error": "organization parameter required"}
                result = await self.skill.switch_context(org)
                return {"result": result}

            elif method == "list_orgs":
                result = await self.skill.list_organizations()
                return {"result": result}

            elif method == "check_credentials":
                result = await self.skill.check_all_credentials()
                return {"result": result}

            elif method == "health":
                result = await self.skill.health_check()
                return {"result": result.model_dump()}

            elif method == "token_status":
                org = params.get("organization")
                if not org:
                    return {"error": "organization parameter required"}
                result = await self.skill.get_token_status(org)
                return {"result": result.model_dump()}

            elif method == "verify_credentials":
                org = params.get("organization")
                if not org:
                    return {"error": "organization parameter required"}
                result = await self.skill.verify_credentials(org)
                return {"result": result}

            elif method == "switch_region":
                region = params.get("region")
                if not region:
                    return {"error": "region parameter required"}
                result = await self.skill.switch_region(region)
                return {"result": result}

            elif method == "switch_project":
                project = params.get("project")
                if not project:
                    return {"error": "project parameter required"}
                result = await self.skill.switch_project(project)
                return {"result": result}

            elif method == "ensure_access":
                org = params.get("organization")
                if not org:
                    return {"error": "organization parameter required"}
                result = await self.skill.ensure_cloud_access(org)
                return {"result": result}

            elif method == "validate_switch":
                result = await self.skill.validate_switch()
                return {"result": result}

            elif method == "login":
                org = params.get("organization")
                if not org:
                    return {"error": "organization parameter required"}
                result = await self.skill.login(org)
                return {"result": result}

            else:
                return {"error": f"Unknown method: {method}"}

        except Exception as e:
            return {"error": f"Error: {str(e)}"}


async def main():
    """Main entry point for MCP server."""
    server = CloudctlMCPServer()

    # Read requests from stdin
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = await server.handle_request(request)
            print(json.dumps(response), flush=True)

        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON"}), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
