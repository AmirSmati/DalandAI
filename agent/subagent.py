from dataclasses import dataclass

from openai import OpenAI

from config.settings import (
    INNKUBE_API_KEY,
    INNKUBE_BASE_URL,
    INNKUBE_MODEL,
    INNKUBE_TEMPERATURE,
)

import json

import uuid

#observability hooks
import time
from Observability.hooks import ObservabilityHooks
@dataclass
class SubAgentRequest:
    """
    Describes a task delegated by the main agent.
    """
    task: str
    role: str
    instructions: str
    context: str = ""
    max_tool_calls: int = 10
    parent_run_id: str | None = None

class SubAgent:
    """
    Specialized agent created to execute one delegated task.

    The sub-agent uses the same Harness as the parent agent.
    """

    MAX_DEFAULT_TOOL_CALLS = 10

    def __init__(
        self,
        harness,
        all_tools,
        tool_router,
        client=None,
        model=None,
        observability: ObservabilityHooks | None = None
    ):
        self.harness = harness
        self.all_tools = all_tools
        self.tool_router = tool_router

        self.client = client or OpenAI(
            api_key=INNKUBE_API_KEY,
            base_url=INNKUBE_BASE_URL,
        )

        self.model = model or INNKUBE_MODEL

        self.observability=observability
    async def run(self, request: SubAgentRequest) -> str:
        """
        Execute a delegated task using the sub-agent's own context.
        """
        #id 
        run_id=str(uuid.uuid4())

        #parent id
        parent_run_id = request.parent_run_id

        # Observability Hooks :
        if self.observability:
            self.observability.agent_start(run_id)
            self.observability.subagent_start(run_id,subagent_type=request.role)
        #start of sub agent : 
        print("***********************************************[SUB-AGENT START]**********************************************")
        print(
            f"[SUB-AGENT START] run_id={run_id} "
            f"parent_run_id={parent_run_id}"
            f"[TASK ========= {request.task} ==================]"
        )

        start_time = time.perf_counter()
        # actual start of the agent
        try :
            selected_tools = self.tool_router.select_tools(request.task)

            if not selected_tools:
                print(
                    "[SUB-AGENT ROUTER] No tools selected. "
                    "Falling back to all available tools."
                )
                selected_tools = self.all_tools
            print(
                f"[SUB-AGENT ROUTER] Selected "
                f"{len(selected_tools)} / {len(self.all_tools)} tools"
            )

            system_prompt = f"""
                You are a specialized sub-agent.

                Role:
                {request.role}

                Instructions:
                {request.instructions}

                Your assigned task:
                {request.task}

                Additional context from the parent agent:
                {request.context}

                Execution constraint:
                You may perform at most {request.max_tool_calls} tool calls.

                Complete only the assigned task.
                Return the result to the parent agent.
                Do not attempt to take over the parent's overall objective.
                """

            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": request.task,
                },
            ]

            tool_calls_used = 0
            run_status = False
            while True:

                llm_kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": INNKUBE_TEMPERATURE,
                }

                if selected_tools:
                    llm_kwargs["tools"] = selected_tools
                    llm_kwargs["tool_choice"] = "auto"

                # LLM Obs
                llm_start = time.perf_counter()
                if self.observability: 
                    self.observability.LLM_start(run_id)
                response = self.client.chat.completions.create(**llm_kwargs)

                llm_duration = time.perf_counter() - llm_start
                input_tkns = None
                output_tkns = None

                if response.usage is not None:
                    input_tkns = response.usage.prompt_tokens
                    output_tkns = response.usage.completion_tokens

                if self.observability:
                    self.observability.LLM_finish(
                        run_id,
                        llm_duration,
                        input_tkns,
                        output_tkns,
                    )

                message = response.choices[0].message

                messages.append(
                    message.model_dump(exclude_none=True)
                )

                # No tool call -> sub-agent is finished
                if not message.tool_calls:
                    run_status = True
                    print(
                        f"[SUB-AGENT FINISH] run_id={run_id} "
                        f"parent_run_id={parent_run_id}"
                    )
                    print("***********************************************[SUB-AGENT Finish]**********************************************")
                    return message.content

                requested_tool_calls = len(message.tool_calls)

                # Enforce sub-agent-specific limit
                if (
                    tool_calls_used + requested_tool_calls
                    > request.max_tool_calls
                ):
                    return (
                        "Sub-agent stopped because it exceeded its "
                        f"tool-call limit of {request.max_tool_calls}."
                    )

                tool_calls_used += requested_tool_calls

                # Execute each requested tool through the shared Harness
                for tool_call in message.tool_calls:

                    tool_name = tool_call.function.name

                    try:
                        arguments = json.loads(
                            tool_call.function.arguments
                        )
                    except json.JSONDecodeError:

                        tool_result = {
                            "success": False,
                            "error": "Invalid JSON arguments.",
                        }

                    else:

                        if tool_name in self.harness.tools:
                            tool_type = "Local"

                        elif any(
                            tool.get("function", {}).get("name") == tool_name
                            for tool in self.all_tools
                        ):
                            tool_type = "MCP"

                        else:
                            tool_type = "Unknown"

                        tool_result = await self.harness.execute(
                            tool_name,
                            tool_type,
                            arguments,
                            run_id=run_id,
                        )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result),
                        }
                    )
        finally :
            duration = time.perf_counter() - start_time
            if self.observability:
                self.observability.agent_finish(
                    run_id,
                    duration
                )
                self.observability.subagent_finish(
                    run_id,
                    request.role,duration,
                    run_status
                )