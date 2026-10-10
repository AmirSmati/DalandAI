import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_client.manager import MCPManager



async def main():

    manager = MCPManager()

    try:
        await manager.connect_all()

        tools = await manager.get_tool_definitions()

        print("\nAvailable MCP tools:")

        for tool in tools:
            print("-", tool["function"]["name"])

        print("\nTesting send_email...")

        result = await manager.call_tool(
            "send_email",
            {
                "recipient": "salmakhlifi92@gmail.com",
                "subject": "AI Lab MCP Test",
                "body": (
                    "Hello!\n\n"
                    "This email was sent using the "
                    "Email MCP server from our AI Lab project."
                ),
            },
        )

        print("\nEmail tool result:")
        print(result)

    finally:
        await manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())