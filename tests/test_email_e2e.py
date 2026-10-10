import asyncio

from agent.agent import Agent


async def main():
    print("=" * 60)
    print("EMAIL MCP END-TO-END TEST")
    print("=" * 60)

    agent = Agent()

    try:
        # 1. Start agent and connect to MCP servers
        print("\n[1] Starting agent...")
        await agent.start()

        # 2. Verify email tools were discovered dynamically
        print("\n[2] Checking discovered MCP tools...")

        tool_names = [
            tool["function"]["name"]
            for tool in agent.mcp_tools
        ]

        print("Discovered tools:")
        for name in tool_names:
            print(f"  - {name}")

        assert "write_email" in tool_names, \
            "write_email was not discovered"

        assert "send_email" in tool_names, \
            "send_email was not discovered"

        print("✓ Email tools discovered successfully")

        # 3. Ask the agent to compose and send an email
        print("\n[3] Asking agent to send an email...")

        result = await agent.run(
            """
            Send an email to salmakhlifi92@gmail.com.

            Subject: E2E MCP Email Test

            Write a short message saying:
            "This email confirms that the AI Lab agent successfully "
            "discovered and used the email MCP tools end-to-end."
            """
        )

        print("\n[4] Agent result:")
        print(result)

        print("\n" + "=" * 60)
        print("✓ EMAIL E2E TEST COMPLETED")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ EMAIL E2E TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        raise

    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())