from tools.registry import TOOL_REGISTRY
from mcp_client.manager import MCPManager
from agent.task_scheduler import TaskScheduler

# Observability
from Observability.hooks import ObservabilityHooks
from Observability.metrics import TOOL_CALLS_TOTAL
from Observability.tracing import traced_span
import time

# Permission
from permissions.manager import PermissionsDec, PermissionManager


class Harness:
    """
    Responsible for validating and executing agent actions.
    """

    def __init__(
        self,
        mcp_manager: MCPManager | None = None,
        scheduler: TaskScheduler | None = None,
        permission_manager: PermissionManager | None = None,
        confirmation_callback=None,
    ):
        self.tools = TOOL_REGISTRY
        self.mcp_manager = mcp_manager
        self.scheduler = scheduler

        self.observability = ObservabilityHooks()

        self.permission_manager = (
            permission_manager
            if permission_manager is not None
            else PermissionManager()
        )
        self.confirmation_callback = confirmation_callback

    async def execute(
        self,
        tool_name: str,
        tool_type: str,
        arguments: dict,
        run_id: str | None = None,
    ) -> dict:

        print(f"\n[HARNESS] Tool: {tool_name}")
        # print(f"[HARNESS] Arguments: {arguments}")

        # ============================================================
        # Permission
        # ============================================================

        tool_definition = None

        if tool_type == "MCP" and self.mcp_manager is not None:
            mcp_tools = await self.mcp_manager.get_tool_definitions()

            for tool in mcp_tools:
                if tool.get("function", {}).get("name") == tool_name:
                    tool_definition = tool
                    break

        # Measure permission-check duration
        permission_start = time.perf_counter()

        # Classify the action for tracing
        permission_action = self.permission_manager.classify_tool(
            tool_name,
            tool_type,
            tool_definition,
        )

        # Perses / tracing span
        with traced_span(
            "permission.check",
            attributes={
                "permission.resource": tool_name,
                "permission.action": permission_action,
                "tool.type": tool_type,
            },
        ) as permission_span:

            permission = self.permission_manager.check(
                tool_name,
                tool_type,
                tool_definition,
            )

            permission_span.set_attribute(
                "permission.decision",
                permission.value,
            )

        permission_duration = time.perf_counter() - permission_start

        print(
            f"[PERMISSION] {tool_name} -> {permission.value}"
        )

        if run_id is not None:
            self.observability.permission_decision(
                run_id,
                tool_name,
                tool_type,
                permission.value,
                duration_secs=permission_duration,
            )

        # Permission denied
        if permission == PermissionsDec.DENY:
            return {
                "success": False,
                "error": f"Permission denied for tool: {tool_name}",
            }

        # Permission requires confirmation
        if permission == PermissionsDec.COONFIRM:

            if self.confirmation_callback is not None:
                confirmation = self.confirmation_callback(tool_name)

            else:
                confirmation = input(
                    f"[PERMISSION] Tool '{tool_name}' requires confirmation. "
                    f"Allow execution? [y/N]: "
                )

            if confirmation.strip().lower() not in {"y", "yes"}:
                return {
                    "success": False,
                    "error": f"User denied execution of tool: {tool_name}",
                }

            print(
                f"[PERMISSION] User confirmed execution of {tool_name}"
            )

            if confirmation.strip().lower() not in {"y", "yes"}:
                return {
                    "success": False,
                    "error": f"User denied execution of tool: {tool_name}",
                }

            print(
                f"[PERMISSION] User confirmed execution of {tool_name}"
            )

        # Tool Observability

        tool_start = time.perf_counter()
        success = False

        if run_id is not None:
            self.observability.Tool_start(
                run_id,
                tool_name,
                tool_type,
            )

        try:

            # ========================================================
            # 1. Follow-up / Scheduler
            # ========================================================

            if tool_name == "schedule_followup":

                task = arguments.get("task")

                if self.scheduler is None:
                    return {
                        "success": False,
                        "error": "Task scheduler is not configured.",
                    }
                if not isinstance(task, dict):
                    return {
                        "success": False,
                        "error": (
                            "Invalid task format. Expected a task dictionary, "
                            f"but received {type(task).__name__}: {task}"
                        ),
                    }

                result = self.scheduler.add_task(task)

                success = result.get("success", False)

                print(
                    f"[SCHEDULER] Queue size: {self.scheduler.size()}"
                )

                return result

            # ========================================================
            # 2. Local / Built-in Tool
            # ========================================================

            if tool_name in self.tools:

                tool = self.tools[tool_name]

                # Perses tracing span for built-in tool
                with traced_span(
                    "tool.call",
                    attributes={
                        "tool.name": tool_name,
                        "tool.type": "builtin",
                    },
                ) as tool_span:

                    try:

                        result = tool(**arguments)

                        success = result.get(
                            "success",
                            False,
                        )

                        #print(f"[HARNESS] Result: {result}")

                        tool_span.set_attribute(
                            "tool.status",
                            "success" if success else "error",
                        )

                        return result

                    except Exception as exc:

                        print(
                            f"[HARNESS] Error: {exc}"
                        )

                        tool_span.set_attribute(
                            "tool.status",
                            "error",
                        )

                        tool_span.record_exception(exc)

                        return {
                            "success": False,
                            "error": str(exc),
                        }

            # ========================================================
            # 3. MCP Tool
            # ========================================================

            if self.mcp_manager is not None:

                mcp_server = self.mcp_manager.tool_servers.get(
                    tool_name
                )

                # Perses tracing span for MCP tool
                with traced_span(
                    "mcp.tool.call",
                    attributes={
                        "tool.name": tool_name,
                        "tool.type": "mcp",
                        "mcp.server": mcp_server,
                    },
                ) as tool_span:

                    try:

                        result = await self.mcp_manager.call_tool(
                            tool_name,
                            arguments,
                        )

                        #print(f"[HARNESS] MCP Result: {result}")

                        success = not result.is_error

                        tool_span.set_attribute(
                            "tool.status",
                            "success" if success else "error",
                        )

                        return {
                            "success": success,
                            "result": {
                                "content": [
                                    item.model_dump()
                                    for item in result.content
                                ],
                                "structured_content":
                                    result.structured_content,
                            },
                        }

                    except Exception as exc:

                        print(
                            f"[HARNESS] MCP Error: {exc}"
                        )

                        tool_span.set_attribute(
                            "tool.status",
                            "error",
                        )

                        tool_span.record_exception(exc)

                        return {
                            "success": False,
                            "error": str(exc),
                        }

            # ========================================================
            # 4. Unknown Tool
            # ========================================================

            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }

        finally:

            if run_id is not None:

                duration_secs = (
                    time.perf_counter() - tool_start
                )

                self.observability.Tool_finish(
                    run_id,
                    tool_name,
                    tool_type,
                    duration_secs,
                    success,
                )