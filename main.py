import asyncio

from agent.agent import Agent
from mcp_client.server_process import MCPServerProcess
from tools.definitions import TOOLS
from tools.ScheduleTool import SCHEDULE_FOLLOWUP_TOOL
from config.dalanda_banner import print_banner,print_features

#Observability Server start
from prometheus_client import start_http_server

from Observability.tracing import init_tracing

# Permission 
from permissions.manager import PermissionMode, MODE_DESCRIPTIONS
async def main():

    
    email_server = MCPServerProcess()
    email_server.start()

    start_http_server(8001)
    print("Prometheus metrics available at http://localhost:8001/metrics")

    init_tracing()
    
    agent = Agent()
    await agent.start()

    print_banner( version="0.1.0",  status="Starting", tagline="Local Workspace Agent",)
    print_features()

    try:

        while True:

            task = input("\nYou: ").strip()

            if task in {"/exit", "/quit"}:
                print("Goodbye.")
                break

        
            if task == "/help":
                print("\nAvailable commands:")
                print("- /help  Show this help message")
                print("- /reset Clear short-term memory")
                print("- /mode [name]  Show or switch permission mode (default, auto, bypass)")
                print("- /exit  Exit the agent")

                print("\nAvailable tools:")
                print("\nInternal tools:")

                for tool in TOOLS:
                    print("-", tool["function"]["name"])

                print("\nScheduler:")
                print("-", SCHEDULE_FOLLOWUP_TOOL["function"]["name"])

                print("\nMCP tools:")

                for tool in agent.mcp_tools:
                    print("-", tool["function"]["name"])

                continue


            if task == "/reset":
                agent.reset_context()
                print("Short-term memory cleared.")
                continue

            # Permission Choice Feature
            if task == "/mode" or task.startswith("/mode "):
                parts = task.split(maxsplit=1)
                arg = parts[1].strip().lower() if len(parts) > 1 else None
                current_mode = agent.get_permission_mode()

                if arg is None:
                    print(f"\nCurrent permission mode: {current_mode.value}")
                    print("Available modes:")
                    for mode in PermissionMode:
                        marker = "*" if mode == current_mode else " "
                        print(f" {marker} {mode.value:<8} - {MODE_DESCRIPTIONS[mode]}")
                    continue

                try:
                    requested_mode = PermissionMode(arg)
                except ValueError:
                    valid = ", ".join(m.value for m in PermissionMode)
                    print(f"Unknown mode '{arg}'. Valid modes: {valid}")
                    continue

                if requested_mode == PermissionMode.BYPASS:
                    confirm = input(
                        "[WARNING] 'bypass' mode allows ALL tool calls, including "
                        "deletes, with NO confirmation prompts. This removes the "
                        "last safety net. Type 'bypass' again to confirm: "
                    ).strip().lower()

                    if confirm != "bypass":
                        print("Bypass mode not enabled; mode unchanged.")
                        continue

                agent.set_permission_mode(requested_mode)
                print(f"Permission mode set to: {requested_mode.value}")
                continue

            if not task:
                continue

            await agent.run(task)


    finally:
        await agent.close()
        email_server.stop()


if __name__ == "__main__":
    asyncio.run(main())