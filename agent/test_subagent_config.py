from agent.subagent import SubAgent, SubAgentRequest
from harness.harness import Harness
from mcp_client.manager import MCPManager
from agent.task_scheduler import TaskScheduler
from tools.definitions import TOOLS
from tools.ScheduleTool import SCHEDULE_FOLLOWUP_TOOL
from tools.router import ToolRouter

async def main():
    mcp = MCPManager()
    scheduler = TaskScheduler()

    harness = Harness(
        mcp,
        scheduler,
    )

    await mcp.connect_all()
    mcp_tools = await mcp.get_tool_definitions()

    request = SubAgentRequest(
        task="Search online for the latest Formula 1 news and summarize the three most important developments.",
        role="Web research specialist",
        instructions=(
            "Research the requested topic using reliable online sources. "
            "Return the key findings with sources. "
            "Do not modify files or perform unrelated tasks."
        ),
        context=(
            "The parent agent will use your findings in a larger response."
        ),
        max_tool_calls=5,
    )

    all_tools = (
        TOOLS
        + [SCHEDULE_FOLLOWUP_TOOL]
        + mcp_tools
        )

    tool_router = ToolRouter(
        all_tools,
        mcp.tool_servers,
    )
    agent = SubAgent(harness, all_tools, tool_router)

    result = await agent.run(request)

    print("\n[SUB-AGENT RESULT]")
    print(result)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())