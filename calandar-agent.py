import asyncio
import os
from pathlib import Path

from agent.agent import Agent
from config.settings import INNKUBE_MODEL


async def main():
    print()
    print("========================================")
    print(" Google Calendar AI Agent (Harness)")
    print("========================================")
    print()

    agent = Agent()
    await agent.start()

    try:
        print("Model:", INNKUBE_MODEL)
        print("Type /reset to clear short-term memory, or /exit to quit.")

        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit", "/exit", "/quit"}:
                print("Goodbye.")
                break

            if user_input == "/reset":
                agent.reset_context()
                print("Short-term memory cleared.")
                continue

            await agent.run(user_input)
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())