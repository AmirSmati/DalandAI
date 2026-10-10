import json
import time
import uuid

from openai import OpenAI

from agent.memory import MemoryManager
from agent.planner import Planner
from agent.prompts import SYSTEM_PROMPT

from config.settings import (
    INNKUBE_API_KEY,
    INNKUBE_BASE_URL,
    INNKUBE_MODEL,
    INNKUBE_TEMPERATURE,
)

import asyncio


from harness.harness import Harness

from tools.definitions import (
    TOOLS,
    DELEGATE_TO_SUBAGENT_TOOL,
)

from mcp_client.manager import MCPManager

from tools.ScheduleTool import SCHEDULE_FOLLOWUP_TOOL
from agent.task_scheduler import TaskScheduler

# Observability
from Observability.hooks import ObservabilityHooks
from Observability.tracing import traced_span

# Tool Selector
from tools.router import ToolRouter

# Sub-agents
from agent.subagent import SubAgent, SubAgentRequest

from datetime import date

# Date iinjection
today = date.today()

#new Permission Feat
from permissions.manager import PermissionMode

from CntxMgmt.budget import (
    MAX_USER_PROMPT_TOKENS,
    MAX_INPUT_TOKENS,
    count_tokens,
    count_request_tokens,
    get_message_token_budget,
)

class Agent:
    """Local workspace agent that orchestrates planning, memory, and tool execution."""

    MAX_TOOL_CALLS_PER_TURN = 20

    def __init__(self):
        self.client = OpenAI(
            api_key=INNKUBE_API_KEY,
            base_url=INNKUBE_BASE_URL,
        )

        self.model = INNKUBE_MODEL

        self.scheduler = TaskScheduler()

        self.mcp = MCPManager()

        self.harness = Harness(
            self.mcp,
            self.scheduler,
        )

        self.planner = Planner(
            client=self.client,
            model=self.model,
        )

        self.memory = MemoryManager(
            client=self.client,
            model=self.model,
        )

        self.mcp_tools = []

        # Observability hooks
        self.observability = ObservabilityHooks()

        # Tool selector
        self.tool_router = ToolRouter([])

    def reset_context(self):
        """Clear short-term conversation memory."""
        self.memory.reset()

    def set_permission_mode(self, mode: PermissionMode) -> None:
        """Switch the runtime permission mode (human-triggered only)."""
        self.harness.permission_manager.set_mode(mode)

    def get_permission_mode(self) -> PermissionMode:
        return self.harness.permission_manager.get_mode()

    async def run(
        self,
        user_task: str,
        allow_decomposition: bool = True,
    ):
        """Run one complete agent request."""

        # Check request tkn size 
        #If too big don't process it at All
        prompt_tokens = count_tokens(user_task)
        
        if prompt_tokens > MAX_USER_PROMPT_TOKENS:
            return (
                "Prompt too large. Please make it shorter "
                f"(maximum {MAX_USER_PROMPT_TOKENS:,} tokens)."
            )
        # Every agent run gets a unique ID for observability.
        run_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        self.observability.agent_start(run_id)

        # OpenTelemetry trace for the complete agent run.
        with traced_span(
            "agent.run",
            attributes={
                "run.id": run_id,
                "agent.name": "dalanda-agent",
                "agent.type": "workspace_agent",
                "model.name": self.model,
            },
        ) as run_span:

            run_status = "success"

            try:
                # Available tools

                all_tools = (
                    TOOLS
                    + [SCHEDULE_FOLLOWUP_TOOL]
                    + [DELEGATE_TO_SUBAGENT_TOOL]
                    + self.mcp_tools
                )

                # Dynamic tool routing

                selected_tools = self.tool_router.select_tools(
                    user_task
                )

                print(
                    "[ROUTER] Selected tools:",
                    [
                        tool["function"]["name"]
                        for tool in selected_tools
                    ],
                )

                # Always make delegation available.
                if DELEGATE_TO_SUBAGENT_TOOL not in selected_tools:
                    selected_tools.append(
                        DELEGATE_TO_SUBAGENT_TOOL
                    )

                print(
                    "[ROUTER] Final tools:",
                    [
                        tool["function"]["name"]
                        for tool in selected_tools
                    ],
                )


                # Context Space calculation
                
                message_budget = get_message_token_budget(selected_tools)
                self.memory.set_context_token_budget(message_budget)


                # Planning

                plan = self.planner.create_plan(
                    user_task
                )

                if plan and plan.strip().upper() not in {
                    "NONE",
                    "NONE.",
                }:
                    print("\n[PLAN]")
                    print(plan)

                current_turn = [
                    {
                        "role": "user",
                        "content": user_task,
                    }
                ]

                tool_calls_used = 0
                
                # Task decomposition / scheduler

                if allow_decomposition:
                    scheduled_tasks = (
                        self.planner.create_task_plan(
                            user_task
                        )
                    )

                    if scheduled_tasks:
                        # Clear tasks from any previous request
                        self.scheduler.clear()

                        for task in scheduled_tasks:
                            result = self.scheduler.add_task(task)

                            if not result["success"]:
                                print(
                                    f"[SCHEDULER] Failed to add task: "
                                    f"{result['error']}"
                                )

                        print(
                            f"[SCHEDULER] Scheduled "
                            f"{len(scheduled_tasks)} task(s)."
                        )

                        # Send the Parallel Result back to the Agent to decide what to do with it 
                        print(
                            f"[SCHEDULER] Scheduled "
                            f"{len(scheduled_tasks)} task(s)."
                        )

                        batch_result = await self.run_scheduled_tasks()

                        current_turn.append(
                            {
                                "role": "user",
                                "content": (
                                    "The first scheduler batch has completed.\n\n"
                                    "Batch results:\n"
                                    f"{json.dumps(batch_result, indent=2)}\n\n"
                                    "Review the results and decide what to do next."
                                ),
                            }
                        )
                            
                # ReAct loop

                while True:

                    # Build context before starting the LLM timer.
                    messages = self.memory.build_context(
                        system_prompt=SYSTEM_PROMPT,
                        current_turn=current_turn,
                        memory_query=user_task,
                        tools=selected_tools,
                        run_id=run_id,
                    )

                    request_tokens = count_request_tokens(
                        messages,
                        selected_tools,
                    )

                    if request_tokens > MAX_INPUT_TOKENS:
                        final_message = (
                            "I stopped because the context became too large "
                            f"({request_tokens:,} input tokens, maximum "
                            f"{MAX_INPUT_TOKENS:,}). Please try a narrower request."
                        )

                        current_turn.append(
                            {
                                "role": "assistant",
                                "content": final_message,
                            }
                        )

                        self.memory.add_turn(current_turn)

                        print("\n[AGENT]")
                        print(final_message)

                        return final_message

                    # LLM observability

                    llm_start = time.perf_counter()

                    self.observability.LLM_start(
                        run_id
                    )

                    with traced_span(
                        "llm.request",
                        attributes={
                            "llm.model": self.model,
                            "llm.provider": "innkube",
                            "llm.operation": "chat.completions",
                        },
                    ) as llm_span:

                        try:

                            if selected_tools:
                                response = (
                                    self.client
                                    .chat.completions.create(
                                        model=self.model,
                                        messages=messages,
                                        tools=selected_tools,
                                        temperature=INNKUBE_TEMPERATURE,
                                        tool_choice="auto",
                                    )
                                )

                            else:
                                # Some vLLM backends reject tools=[].
                                # Therefore omit tools completely.
                                response = (
                                    self.client
                                    .chat.completions.create(
                                        model=self.model,
                                        messages=messages,
                                        temperature=INNKUBE_TEMPERATURE,
                                    )
                                )

                        except Exception as exc:

                            self.observability.llm_error(
                                run_id,
                                "agent",
                                str(exc),
                            )

                            llm_span.set_attribute(
                                "llm.status",
                                "error",
                            )

                            llm_span.record_exception(
                                exc
                            )

                            raise

                        message = (
                            response
                            .choices[0]
                            .message
                        )

                        
                        # LLM metrics
                        

                        llm_duration = (time.perf_counter() - llm_start)

                        input_tkns = None
                        output_tkns = None

                        if response.usage is not None:
                            input_tkns = (
                                response
                                .usage
                                .prompt_tokens
                            )

                            output_tkns = (
                                response
                                .usage
                                .completion_tokens
                            )
                              
                        # OpenTelemetry LLM attributes
                        

                        llm_span.set_attribute(
                            "llm.duration_seconds",
                            llm_duration,
                        )

                        if input_tkns is not None:
                            llm_span.set_attribute(
                                "llm.input_tokens",
                                input_tkns,
                            )

                        if output_tkns is not None:
                            llm_span.set_attribute(
                                "llm.output_tokens",
                                output_tkns,
                            )

                        if (
                            input_tkns is not None
                            and output_tkns is not None
                        ):
                            llm_span.set_attribute(
                                "llm.total_tokens",
                                input_tkns
                                + output_tkns,
                            )

                    # Prometheus hook
                    self.observability.LLM_finish(
                        run_id,
                        llm_duration,
                        input_tkns,
                        output_tkns,
                    )


                    # Store assistant response in current turn


                    current_turn.append(
                        message.model_dump(
                            exclude_none=True
                        )
                    )


                    # Final answer


                    if not message.tool_calls:

                        self.memory.add_turn(
                            current_turn
                        )

                        print("\n[AGENT]")
                        print(message.content)

                        return message.content


                    # Tool-call limit


                    requested_tool_calls = len(
                        message.tool_calls
                    )

                    if (
                        tool_calls_used
                        + requested_tool_calls
                        > self.MAX_TOOL_CALLS_PER_TURN
                    ):

                        for tool_call in message.tool_calls:

                            current_turn.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps(
                                        {
                                            "success": False,
                                            "error": (
                                                "Tool-call limit "
                                                "reached for this "
                                                "request."
                                            ),
                                        }
                                    ),
                                }
                            )

                        final_message = (
                            "I stopped because this request "
                            "exceeded the limit of "
                            f"{self.MAX_TOOL_CALLS_PER_TURN} "
                            "tool calls. "
                            "Please try a narrower request."
                        )

                        current_turn.append(
                            {
                                "role": "assistant",
                                "content": final_message,
                            }
                        )

                        self.memory.add_turn(
                            current_turn
                        )

                        print("\n[AGENT]")
                        print(final_message)

                        return final_message

                    tool_calls_used += requested_tool_calls


                    # Execute requested tools


                    for tool_call in message.tool_calls:

                        tool_name = (
                            tool_call.function.name
                        )
                        # Sub-agent delegatio====

                        if tool_name == "delegate_to_subagent":

                            arguments = json.loads(
                                tool_call.function.arguments
                            )
                            date= f"Date Standard: Always use the date format DD-MM-YYYY. Today's date is `{today.strftime("%d-%m-%Y")}`"
                            request = SubAgentRequest(
                                task = arguments["task"],
                                role=arguments["role"],
                                instructions=arguments[
                                    "instructions"
                                ],
                                context=arguments.get(
                                    date + "\n"+
                                    "context",
                                    "",
                                ),
                                max_tool_calls=arguments.get(
                                    "max_tool_calls",
                                    10,
                                ),
                                parent_run_id=run_id,
                            )

                            subagent = SubAgent(
                                harness=self.harness,
                                all_tools=all_tools,
                                tool_router=self.tool_router,
                                client=self.client,
                                model=self.model,
                                observability=self.observability,
                            )

                            tool_result = (await subagent.run(request))

                            # Incorporate the sub-agent result
                            # into the parent conversation.
                            current_turn.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps(
                                        {
                                            "success": True,
                                            "result": tool_result,
                                        }
                                    ),
                                }
                            )

                            continue

                        # Determine tool type

                        if tool_name in self.harness.tools:

                            tool_type = "Local"

                        elif any(
                            tool.get(
                                "function",
                                {}
                            ).get(
                                "name"
                            ) == tool_name
                            for tool in self.mcp_tools
                        ):

                            tool_type = "MCP"

                        elif tool_name == "schedule_followup":

                            tool_type = "Scheduler"

                        else:

                            tool_type = "Unknown"

                        # Parse tool argument
                        try:

                            arguments = json.loads(
                                tool_call.function.arguments
                            )

                        except json.JSONDecodeError:

                            tool_result = {
                                "success": False,
                                "error": (
                                    "Invalid JSON arguments."
                                ),
                            }

                        else:

                            # Execute through the SAME Harness

                            tool_result = (
                                await self.harness.execute(
                                    tool_name,
                                    tool_type,
                                    arguments,
                                    run_id=run_id,
                                )
                            )

                        # Add tool result to current context.
                        current_turn.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(
                                    tool_result
                                ),
                            }
                        )

            except Exception:

                # The OpenTelemetry span automatically observes
                # the exception as it leaves the context manager.
                run_status = "error"

                raise

            finally:

                # Agent completion observability

                duration_secs = (
                    time.perf_counter()
                    - start_time
                )

                run_span.set_attribute(
                    "run.status",
                    run_status,
                )

                self.observability.agent_finish(
                    run_id,
                    duration_secs,
                    success=(
                        run_status == "success"
                    ),
                )

    # Scheduler

    async def run_scheduled_tasks(self, max_tasks: int = 5):
        """Execute dependency-aware batches until all tasks are completed."""

        all_completed_tasks = []
        all_failed_tasks = []

        while self.scheduler.has_pending_tasks():

            # 1. Find tasks whose dependencies are completed
            ready_tasks = self.scheduler.get_ready_tasks()

            if not ready_tasks:
                print(
                    "[SCHEDULER] No executable tasks. "
                    "Possible circular or invalid dependency."
                )

                return {
                    "success": False,
                    "error": "No executable tasks. Possible circular dependency.",
                    "completed_tasks": all_completed_tasks,
                    "failed_tasks": all_failed_tasks,
                    "has_pending_tasks": self.scheduler.has_pending_tasks(),
                }

            # 2. Select the current ready batch
            batch = ready_tasks[:max_tasks]

            print(
                f"\n[SCHEDULER] Running "
                f"{len(batch)} ready tasks in parallel"
            )

            async def execute_subagent(task):
                dependency_context = ""

                for dependency_id in task["depends_on"]:
                    dependency = self.scheduler.get_task(dependency_id)

                    if dependency:
                        dependency_context += (
                            f"\n\nPrevious task: {dependency_id}\n"
                            f"Result:\n{dependency['result']}"
                        )

                request = SubAgentRequest(
                    task=task["description"],
                    role="Specialized task solver",
                    instructions=(
                        "Solve only the assigned task. "
                        "Use the supplied dependency results when available. "
                        "Return a concise and accurate result."
                    ),
                    context=dependency_context,
                    max_tool_calls=10,
                )

                subagent = SubAgent(
                    harness=self.harness,
                    all_tools=(
                        TOOLS
                        + [SCHEDULE_FOLLOWUP_TOOL]
                        + self.mcp_tools
                    ),
                    tool_router=self.tool_router,
                    client=self.client,
                    model=self.model,
                    observability=self.observability,
                )

                return await subagent.run(request)

            # 3. Execute this batch concurrently
            results = await asyncio.gather(
                *(execute_subagent(task) for task in batch),
                return_exceptions=True,
            )

            batch_failed = False

            # 4. Store results in the scheduler
            for task, result in zip(batch, results):
                task_id = task["id"]

                if isinstance(result, Exception):
                    self.scheduler.mark_failed(task_id, str(result))

                    all_failed_tasks.append({
                        "task_id": task_id,
                        "error": str(result),
                    })

                    batch_failed = True

                    print(f"[TASK FAILED] {task_id}: {result}")

                else:
                    self.scheduler.mark_completed(task_id, result)

                    all_completed_tasks.append({
                        "task_id": task_id,
                        "result": result,
                    })

                    print(f"\n[TASK COMPLETED] {task_id}")
                    print(f"[RESULT] {result}")

            # Stop if any task in this batch failed
            if batch_failed:
                return {
                    "success": False,
                    "completed_tasks": all_completed_tasks,
                    "failed_tasks": all_failed_tasks,
                    "has_pending_tasks": self.scheduler.has_pending_tasks(),
                }

            # Otherwise, the while-loop executes the next ready batch

        # 5. All scheduled tasks are completed
        print("\n[SCHEDULER] All scheduled tasks completed.")

        return {
            "success": len(all_failed_tasks) == 0,
            "completed_tasks": all_completed_tasks,
            "failed_tasks": all_failed_tasks,
            "has_pending_tasks": self.scheduler.has_pending_tasks(),
        }

    
    # MCP

    async def start(self):
        """Connect to MCP and discover available MCP tools."""

        await self.mcp.connect_all()

        self.mcp_tools = (
            await self.mcp.get_tool_definitions()
        )

        all_tools = (
            TOOLS
            + [SCHEDULE_FOLLOWUP_TOOL]
            + [DELEGATE_TO_SUBAGENT_TOOL]
            + self.mcp_tools
        )

        self.tool_router = ToolRouter(
            all_tools,
            self.mcp.tool_servers,
        )
    async def close(self):
        """Close the MCP connection."""

        await self.mcp.disconnect_all()