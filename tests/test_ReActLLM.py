from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.agent import Agent
from tools.definitions import TOOLS, DELEGATE_TO_SUBAGENT_TOOL

from CntxMgmt.budget import count_request_tokens,count_request_tokens
@pytest.mark.asyncio
async def test_react_rebuilds_context_after_tool_result(monkeypatch):
    agent = Agent()

    # Avoid planner/scheduler work.
    monkeypatch.setattr(
        agent.planner,
        "create_plan",
        lambda *args, **kwargs: "NONE",
    )

    monkeypatch.setattr(
        agent.planner,
        "create_task_plan",
        lambda *args, **kwargs: [],
    )

    # Give the router one normal tool.
    selected_tool = next(
        tool for tool in TOOLS
        if tool["function"]["name"] == "list_files"
    )

    monkeypatch.setattr(
        agent.tool_router,
        "select_tools",
        lambda _: [selected_tool],
    )

    # Fake tool execution.
    monkeypatch.setattr(
        agent.harness,
        "execute",
        AsyncMock(
            return_value={
                "success": True,
                "entries": ["file1.txt", "file2.txt"],
            }
        ),
    )

    # First LLM response -> asks for a tool.
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(
            name="list_files",
            arguments='{"path":"."}',
        ),
    )

    first_message = SimpleNamespace(
        content=None,
        tool_calls=[tool_call],
        model_dump=lambda exclude_none=True: {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "list_files",
                        "arguments": '{"path":"."}',
                    },
                }
            ],
        },
    )

    # Second LLM response -> final answer.
    second_message = SimpleNamespace(
        content="Done.",
        tool_calls=None,
        model_dump=lambda exclude_none=True: {
            "role": "assistant",
            "content": "Done.",
        },
    )

    first_response = SimpleNamespace(
        choices=[SimpleNamespace(message=first_message)],
        usage=SimpleNamespace(
            prompt_tokens=20,
            completion_tokens=5,
            total_tokens=25,
        ),
    )

    second_response = SimpleNamespace(
        choices=[SimpleNamespace(message=second_message)],
        usage=SimpleNamespace(
            prompt_tokens=30,
            completion_tokens=5,
            total_tokens=35,
        ),
    )

    responses = iter([first_response, second_response])

    mock_llm = MagicMock(
        side_effect=lambda *args, **kwargs: next(responses)
    )

    monkeypatch.setattr(
        agent.client.chat.completions,
        "create",
        mock_llm,
    )

    # Capture every context built by the ReAct loop.
    build_context_calls = []

    original_build_context = agent.memory.build_context

    def tracked_build_context(**kwargs):
        messages = original_build_context(**kwargs)
        build_context_calls.append(messages)
        return messages

    monkeypatch.setattr(
        agent.memory,
        "build_context",
        tracked_build_context,
    )

    result = await agent.run(
        "List the files in the current directory.",
        allow_decomposition=False,
    )

    assert result == "Done."

    # Two LLM iterations -> context must be rebuilt twice.
    assert len(build_context_calls) == 2

    first_context = build_context_calls[0]
    second_context = build_context_calls[1]

    first_tokens = count_request_tokens(
        first_context,
        [selected_tool, DELEGATE_TO_SUBAGENT_TOOL],
    )

    second_tokens = count_request_tokens(
        second_context,
        [selected_tool, DELEGATE_TO_SUBAGENT_TOOL],
    )

    assert second_tokens > first_tokens

    # The second context must contain the tool result from the first iteration.
    second_contents = [
        message.get("content", "")
        for message in second_context
    ]

    assert any(
        "file1.txt" in str(content)
        for content in second_contents
    )

    # The second request should not be smaller than the first
    # because the tool result was added to current_turn.
    assert second_tokens > first_tokens