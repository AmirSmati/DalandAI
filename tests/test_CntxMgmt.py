import pytest
from unittest.mock import MagicMock, Mock

from agent.agent import Agent
from agent.memory import MemoryManager
from CntxMgmt.budget import (
    count_request_tokens,
    get_message_token_budget,
)
from tools.definitions import DELEGATE_TO_SUBAGENT_TOOL


@pytest.mark.asyncio
async def test_agent_sets_tool_aware_context_budget(monkeypatch):
    agent = Agent()

    selected_tools = [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files",
                "parameters": {},
            },
        }
    ]

    final_tools = selected_tools + [DELEGATE_TO_SUBAGENT_TOOL]
    expected_budget = get_message_token_budget(final_tools)

    monkeypatch.setattr(
        agent.tool_router,
        "select_tools",
        lambda _: selected_tools,
    )

    set_budget = MagicMock(
        wraps=agent.memory.set_context_token_budget
    )

    monkeypatch.setattr(
        agent.memory,
        "set_context_token_budget",
        set_budget,
    )

    monkeypatch.setattr(
        agent.memory,
        "build_context",
        lambda **kwargs: [
            {"role": "user", "content": "test"}
        ],
    )

    response = MagicMock()
    response.choices[0].message.content = "Test response"
    response.choices[0].message.tool_calls = None
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 5
    response.usage.total_tokens = 15

    monkeypatch.setattr(
        agent.client.chat.completions,
        "create",
        MagicMock(return_value=response),
    )

    await agent.run("Test prompt")

    set_budget.assert_called_once_with(expected_budget)


def test_history_budget_accounts_for_fixed_messages():
    memory = MemoryManager(
        client=Mock(),
        model="test-model",
    )

    fixed_messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        }
    ]

    memory.set_context_token_budget(1000)

    expected = max(
        0,
        1000 - count_request_tokens(fixed_messages),
    )

    actual = memory._calculate_history_budget(
        fixed_messages,
        [],
    )

    assert actual == expected


def test_build_context_calculates_history_budget():
    memory = MemoryManager(
        client=Mock(),
        model="test-model",
    )

    memory_system_prompt = "You are a helpful assistant."

    current_turn = [
        {
            "role": "user",
            "content": "This is the current request.",
        }
    ]

    memory.set_context_token_budget(1000)

    memory.build_context(
        system_prompt=memory_system_prompt,
        current_turn=current_turn,
        tools=[],
    )

    fixed_messages = [
        {
            "role": "system",
            "content": memory_system_prompt,
        },
        *current_turn,
    ]

    expected = memory._calculate_history_budget(
        fixed_messages,
        [],
    )

    assert memory.history_token_budget == expected


def test_build_context_only_keeps_history_that_fits():
    memory = MemoryManager(
        client=Mock(),
        model="test-model",
    )

    memory.get_relevant_memory = lambda *args, **kwargs: ""

    current_turn = [
        {
            "role": "user",
            "content": "Current request.",
        }
    ]

    old_turn = [
        {
            "role": "user",
            "content": "Old conversation turn.",
        },
        {
            "role": "assistant",
            "content": "Old assistant response.",
        },
    ]

    newest_turn = [
        {
            "role": "user",
            "content": "Newest conversation turn.",
        },
        {
            "role": "assistant",
            "content": "Newest assistant response.",
        },
    ]

    memory.conversation_turns = [
        old_turn,
        newest_turn,
    ]

    newest_tokens = sum(
        count_request_tokens([message])
        for message in newest_turn
    )

    memory.set_context_token_budget(newest_tokens)

    messages = memory.build_context(
        system_prompt="System prompt.",
        current_turn=current_turn,
        tools=[],
    )

    contents = [
        message.get("content", "")
        for message in messages
    ]

    assert "Current request." in contents
    assert "Newest conversation turn." in contents
    assert "Newest assistant response." in contents
    assert "Old conversation turn." not in contents
    assert "Old assistant response." not in contents


def test_build_context_triggers_request_level_compaction(monkeypatch):
    memory = MemoryManager(
        client=Mock(),
        model="test-model",
    )

    memory.get_relevant_memory = lambda *args, **kwargs: ""

    memory.conversation_turns = [
        [{"role": "user", "content": "word " * 50}],
        [{"role": "assistant", "content": "word " * 50}],
        [{"role": "user", "content": "word " * 50}],
        [{"role": "assistant", "content": "word " * 50}],
        [{"role": "user", "content": "word " * 50}],
    ]

    memory.set_context_token_budget(100)

    monkeypatch.setattr(
        memory,
        "_summarize_turns",
        lambda turns, summary_budget: "Compacted summary",
    )

    messages = memory.build_context(
        system_prompt="System prompt.",
        current_turn=[
            {
                "role": "user",
                "content": "Current request.",
            }
        ],
        tools=[],
    )

    contents = [
        message.get("content", "")
        for message in messages
    ]

    assert memory.summary == "Compacted summary"
    assert "Compacted summary" in "\n".join(contents)


def test_agent_rejects_oversized_final_context(monkeypatch):
    import agent.agent as agent_module

    monkeypatch.setattr(
        agent_module,
        "MAX_INPUT_TOKENS",
        10,
    )

    agent = Agent()

    monkeypatch.setattr(
        agent.planner,
        "create_plan",
        lambda *args, **kwargs: "NONE",
    )

    monkeypatch.setattr(
        agent.memory,
        "build_context",
        lambda **kwargs: [
            {
                "role": "system",
                "content": "This message is deliberately oversized.",
            }
        ],
    )

    def fail_if_llm_called(*args, **kwargs):
        raise AssertionError(
            "LLM should not be called for an oversized request"
        )

    monkeypatch.setattr(
        agent.client.chat.completions,
        "create",
        fail_if_llm_called,
    )

    result = pytest.run if False else None