import asyncio
import json

from mcp_client.config import EXA_MCP_URL
from mcp_client.client import MCPClient


async def main():
    exa_client = MCPClient(
        name="exa",
        url=EXA_MCP_URL,
    )

    try:
        print("[TEST] Connecting to Exa...")

        await exa_client.connect()

        print("[TEST] Connected to Exa.")

        tools = await exa_client.get_tool_definitions()

        print("\n========== EXA TOOL DEFINITIONS ==========\n")

        print(
            json.dumps(
                tools,
                indent=4,
                ensure_ascii=False,
            )
        )

        print(f"\nTotal Exa tools: {len(tools)}")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")

    finally:
        await exa_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())