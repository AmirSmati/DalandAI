from unittest.mock import Mock

from agent.memory import MemoryManager
from CntxMgmt.budget import count_request_tokens,count_tool_tokens,get_message_token_budget,MAX_INPUT_TOKENS

def test_compaction_reduces_context_below_token_budget(monkeypatch):
    monkeypatch.setattr(MemoryManager, "MAX_CONTEXT_TOKENS", 100)

    client = Mock()
    memory = MemoryManager(
        client=client,
        model="test-model",
    )

    client.chat.completions.create.return_value = Mock(
        choices=[
            Mock(
                message=Mock(
                    content="## Goals & Intent\nKeep the conversation context."
                )
            )
        ]
    )

    memory.conversation_turns = [
        [{"role": "user", "content": "word " * 80}],
        [{"role": "assistant", "content": "word " * 80}],
        [{"role": "user", "content": "word " * 80}],
        [{"role": "assistant", "content": "word " * 80}],
        [{"role": "user", "content": "word " * 80}],
    ]

    memory.compact(memory.context_token_budget)

    remaining_tokens = memory._count_conversation_tokens()

    print(f"\nRemaining conversation tokens: {remaining_tokens}")

    assert remaining_tokens <= memory.context_token_budget


    # .40% test
def test_summary_budget_is_40_percent():
    client = Mock()

    memory = MemoryManager(
        client=client,
        model="test-model",
    )

    turns = [
        [{"role": "user", "content": "word " * 250}],
    ]

    memory.conversation_turns = turns
    
    old_tokens = memory._count_conversation_tokens()

    summary_budget = memory._calculate_summary_budget(turns)

    assert summary_budget == int(
        old_tokens * memory.SUMMARY_COMPRESSION_RATIO
    )


def test_summary_generation_uses_reserved_budget():
    client = Mock()

    memory = MemoryManager(
        client=client,
        model="test-model",
    )

    turns = [
        [{"role": "user", "content": "word " * 250}],
    ]

    summary_budget = memory._calculate_summary_budget(turns)

    client.chat.completions.create.return_value = Mock(
        choices=[
            Mock(
                message=Mock(
                    content="## Goals & Intent\nKeep the conversation context."
                )
            )
        ]
    )

    memory._summarize_turns(turns, summary_budget)

    call_kwargs = client.chat.completions.create.call_args.kwargs

    assert call_kwargs["max_tokens"] == summary_budget


# Saved sspace test
def test_recent_turns_leave_room_for_summary(monkeypatch):
    monkeypatch.setattr(MemoryManager, "MAX_CONTEXT_TOKENS", 100)

    client = Mock()
    memory = MemoryManager(
        client=client,
        model="test-model",
    )

    client.chat.completions.create.return_value = Mock(
        choices=[
            Mock(
                message=Mock(
                    content="## Goals & Intent\nKeep the conversation context."
                )
            )
        ]
    )

    # Each turn is roughly 30 tokens.
    # Five turns exceed the 100-token context budget.
    memory.conversation_turns = [
        [{"role": "user", "content": "word " * 29}],
        [{"role": "assistant", "content": "word " * 29}],
        [{"role": "user", "content": "word " * 29}],
        [{"role": "assistant", "content": "word " * 29}],
        [{"role": "user", "content": "word " * 29}],
    ]

    older_turns = memory.conversation_turns[:-memory.MAX_RECENT_TURNS]

    summary_budget = memory._calculate_summary_budget(
        older_turns
    )

    memory.compact(memory.context_token_budget)

    remaining_tokens = memory._count_conversation_tokens()

    available_for_recent_turns = (
        memory.context_token_budget - summary_budget
    )

    print(f"\nSummary budget: {summary_budget}")
    print(f"Remaining turn tokens: {remaining_tokens}")
    print(
        f"Available for recent turns: "
        f"{available_for_recent_turns}"
    )

    assert remaining_tokens <= available_for_recent_turns


def test_count_request_tokens_includes_tools():
    messages = [
        {
            "role": "system",
            "content": "You are a workspace assistant.",
        },
        {
            "role": "user",
            "content": "Explain this task.",
        },
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Search files in the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                        }
                    },
                    "required": ["query"],
                },
            },
        }
    ]

    messages_only = count_request_tokens(messages)
    request_with_tools = count_request_tokens(
        messages,
        tools,
    )

    assert request_with_tools > messages_only



def test_count_tool_tokens():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Search files in the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                        }
                    },
                    "required": ["query"],
                },
            },
        }
    ]

    tokens = count_tool_tokens(tools)

    assert tokens > 0


def test_message_budget_reserves_tool_tokens():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Search files.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        }
    ]

    tool_tokens = count_tool_tokens(tools)
    message_budget = get_message_token_budget(tools)

    assert message_budget == MAX_INPUT_TOKENS - tool_tokens

# getting tools dynamically
def test_memory_manager_accepts_dynamic_context_budget():
    client = Mock()

    memory = MemoryManager(
        client=client,
        model="test-model",
    )

    memory.set_context_token_budget(500)

    assert memory.context_token_budget == 500