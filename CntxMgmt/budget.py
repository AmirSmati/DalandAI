"""
This file takes care of the space maangment of the context 
"""

from transformers import AutoTokenizer
import json

TOKENIZER_NAME = "Qwen/Qwen-AgentWorld-35B-A3B"

# Max allowed User req sidze
MAX_USER_PROMPT_TOKENS = 64_000

# Model context window.
MODEL_CONTEXT_TOKENS = 262_144

# Expected response space
RESERVED_OUTPUT_TOKENS = 8_192

# Max input tokns
MAX_INPUT_TOKENS = MODEL_CONTEXT_TOKENS - RESERVED_OUTPUT_TOKENS

# Summary Saved Frac .4 of each turn
SUMMARY_COMPRESSION_RATIO = 0.40


_tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)


def count_tokens(text: str) -> int:
    """Return the number of Qwen tokenizer tokens in a text string."""
    return len(
        _tokenizer.encode(
            text,
            add_special_tokens=False,
        )
    )

def count_request_tokens(messages: list, tools: list | None = None) -> int:
    """Estimate tokens for the complete LLM request payload."""
    payload = {
        "messages": messages,
        "tools": tools or [],
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return count_tokens(serialized)

# Size of Tools passed in Tkns
def count_tool_tokens(tools: list | None) -> int:
    """Count tokens used by serialized tool schemas."""
    if not tools:
        return 0

    serialized = json.dumps(
        tools,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return count_tokens(serialized)

# Left Space after saving up for tools
def get_message_token_budget(tools: list | None) -> int:
    """Return the input-token budget remaining after reserving tool schemas."""
    tool_tokens = count_tool_tokens(tools)

    return max(
        0,
        MAX_INPUT_TOKENS - tool_tokens,
    )

