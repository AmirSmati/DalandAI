from agent.agent import Agent
from prometheus_client import generate_latest
from Observability.metrics import (
    AGENT_RUNS_TOTAL,
    AGENT_ACTIVE_RUNS,
    TOOL_CALLS_TOTAL,
    TOOL_SUCCESS_TOTAL,
    TOOL_FAILURE_TOTAL,
    TOOL_CALL_DURATION,
)


def get_metric_value(metric):
    return metric._value.get()


async def main():
    runs_before = get_metric_value(AGENT_RUNS_TOTAL)
    active_before = get_metric_value(AGENT_ACTIVE_RUNS)

    print("Before:")
    print("Runs:", runs_before)
    print("Active runs:", active_before)

    agent = Agent()
    await agent.start()

    try:
        await agent.run("check my google calendar for team meetings", allow_decomposition=False)
    finally:
        await agent.close()

    runs_after = get_metric_value(AGENT_RUNS_TOTAL)
    active_after = get_metric_value(AGENT_ACTIVE_RUNS)

    print("\nAfter:")
    print("Runs:", runs_after)
    print("Active runs:", active_after)

    print("\nTool metrics:")
    print(
    "Tool calls:",
    TOOL_CALLS_TOTAL.labels(
        tool_name="find_events",
        tool_type="MCP"
        )._value.get()
    )

    print(
        "Tool successes:",
        TOOL_SUCCESS_TOTAL.labels(
            tool_name="find_events",
            tool_type="MCP"
        )._value.get()
    )

    print(
        "Tool failures:",
        TOOL_FAILURE_TOTAL.labels(
            tool_name="find_events",
            tool_type="MCP"
        )._value.get()
    )

    print("\n=== TOOL METRICS ===")

    metrics_output = generate_latest().decode("utf-8")

    for line in metrics_output.splitlines():
        if line.startswith("tool_calls_total"):
            print(line)
    #print("Tool duration:", TOOL_CALL_DURATION.collect())
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())