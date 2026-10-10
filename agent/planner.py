from openai import OpenAI

from agent.prompts import PLANNER_PROMPT
from tools.memory import load_all_memories_formatted
from config.settings import INNKUBE_TEMPERATURE

import json

from datetime import date

today = date.today()

class Planner:
    """Generates a temporary execution plan for a user request."""

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model


    # Thinking ability, Making a plan that then can be Scheduleed by the scheduling tool
    # Agent comprehinsble plan
    def create_task_plan(self, user_task: str) -> list[dict]:
        """Generate structured tasks with dependencies."""

        system_prompt = f"""
            You are a task planner for an AI agent system.

            Break the user's request into clear, executable tasks ONLY when
            decomposition is genuinely useful.

            For every task:
            - Give it a unique ID.
            - Write a precise description.
            - Explicitly mention the required tool category when applicable.
            - Use "web search tools" for searching, researching, or finding online information.
            - Use "web extraction tools" for retrieving detailed content from URLs or sources.
            - Use "Notion tools" when creating or updating Notion pages.
            - Use "filesystem tools" when working with local files.
            - Include dependencies using task IDs.
            - Do not invent tool names.
            - Keep tasks focused on one objective.

            Date and time rules:
            - Today's date is `{today.strftime("%Y-%m-%d")}`.
            - Timezone is `Europe/Berlin`.
            - When a task involves a date, resolve relative dates such as
            "today", "tomorrow", "next week", or "the 23rd" using this
            runtime date and timezone.
            - Do not use dates from prior conversation context as the current date.

            Decomposition rules:
            - If the request can be completed directly by the main agent
            with one coherent action or a short ReAct sequence, return:
            NONE
            - Do NOT create a task merely because a tool is required.
            - A single calendar operation, filesystem operation, memory lookup,
            or similar direct action should normally remain with the main agent.
            - Decompose when the request contains multiple distinct objectives,
            independent work that can run in parallel, or meaningful
            dependencies between tasks.
            - When decomposition is used, prefer independent tasks without
            dependencies so they can execute in parallel.

            Available tool categories:
            - web search and extraction
            - Notion
            - filesystem
            - memory
            - email
            - calendar

            Return ONLY valid JSON.

            For no decomposition:
            NONE

            Otherwise:
            [
                {{
                    "id": "unique_task_id",
                    "description": "Specific executable task",
                    "depends_on": []
                }}
            ]
            """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_task},
                ],
                temperature=INNKUBE_TEMPERATURE,
            )

            content = response.choices[0].message.content or ""

            print("\n[DEBUG] Raw task planner response:")
            print(repr(content))

            if content.strip().upper() == "NONE":
                return []

            # Handle possible markdown JSON fences
            content = content.strip()

            if content.startswith("```"):
                content = content.replace("```json", "")
                content = content.replace("```", "").strip()

            tasks = json.loads(content)

            if not isinstance(tasks, list):
                raise ValueError("Planner output must be a JSON list.")

            for task in tasks:
                if not all(
                    key in task
                    for key in ("id", "description", "depends_on")
                ):
                    raise ValueError(f"Invalid task structure: {task}")
                # DEBUG: Print the generated task plan
            print("\n[DEBUG] Generated task plan:")
            print(json.dumps(tasks, indent=2))
            
            return tasks

        except Exception as exc:
            print(f"[PLANNER] Task decomposition skipped: {exc}")
            return []

    def create_plan(self, user_task: str) -> str:
        """Generate a visible plan before the main agent loop starts."""
        system_content = PLANNER_PROMPT

        try:
            ltm_content = load_all_memories_formatted()

            if ltm_content:
                system_content += (
                    "\n\nPersistent Long-Term Memory (facts and preferences):\n"
                    f"{ltm_content}"
                )
        except Exception as exc:
            print(f"[MEMORY] Warning: Could not load memory for planner: {exc}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_content,
                    },
                    {
                        "role": "user",
                        "content": user_task,
                    },
                ],
                temperature=INNKUBE_TEMPERATURE,
            )

            return response.choices[0].message.content or ""

        except Exception as exc:
            print(f"[PLANNER] Plan generation skipped: {exc}")
            return ""