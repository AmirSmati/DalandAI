from enum import Enum

# Config Permissiosn.json path
import json
from pathlib import Path

class PermissionsDec(Enum):
    ALLOW = "Allow"
    DENY = "Deny"
    COONFIRM = "Require_user_confirmation"


class PermissionMode(Enum):
    """
    Runtime permission mode, switched by the human operator (never the LLM)
    via the /mode CLI command. Changes the fallback decision for tools
    without an explicit per-tool policy override; explicit overrides always
    win regardless of mode.
    """
    DEFAULT = "default"
    AUTO = "auto"
    BYPASS = "bypass"


# Fallback decision per (mode, action), for actions without an explicit
# per-tool policy override. The "unknown" action is intentionally absent
# from every row and always falls back to PermissionManager.default_decision,
# regardless of mode.
MODE_DECISIONS: dict[PermissionMode, dict[str, PermissionsDec]] = {
    PermissionMode.DEFAULT: {
        "read": PermissionsDec.ALLOW,
        "write": PermissionsDec.COONFIRM,
        "delete": PermissionsDec.COONFIRM,
    },
    PermissionMode.AUTO: {
        "read": PermissionsDec.ALLOW,
        "write": PermissionsDec.ALLOW,
        "delete": PermissionsDec.COONFIRM,
    },
    PermissionMode.BYPASS: {
        "read": PermissionsDec.ALLOW,
        "write": PermissionsDec.ALLOW,
        "delete": PermissionsDec.ALLOW,
    },
}

MODE_DESCRIPTIONS: dict[PermissionMode, str] = {
    PermissionMode.DEFAULT: "Reads allowed; writes and deletes require confirmation.",
    PermissionMode.AUTO: "Reads and writes allowed automatically; deletes still require confirmation.",
    PermissionMode.BYPASS: "Full autonomy: reads, writes, and deletes all allowed without prompts.",
}


class PermissionManager:
    """
    Central permission manager for built-in and MCP tools.
    """

    def __init__(
        self,
        config_path: str = "config/permissions.json",
        default_decision: PermissionsDec = PermissionsDec.COONFIRM,
    ):
        self.default_decision = default_decision
        self.policies = {}
        self.mode = PermissionMode.DEFAULT

        self.load_config(config_path)

    def load_config(self, config_path: str) -> None:
        path = Path(config_path)

        if not path.exists():
            print(
                f"[PERMISSION] Config file not found: {config_path}. "
                "Using default policy."
            )
            return

        with path.open("r", encoding="utf-8") as file:
            config = json.load(file)

        # Load default decision
        default_value = config.get("default")

        if default_value is not None:
            self.default_decision = PermissionsDec(default_value)

        # Load tool policies
        tools = config.get("tools", {})

        for tool_name, decision_value in tools.items():
            self.policies[tool_name] = PermissionsDec(decision_value)

    def set_policy(
        self,
        tool_name: str,
        decision: PermissionsDec,
    ) -> None:
        self.policies[tool_name] = decision

    def check(
        self,
        tool_name: str,
        tool_type: str,
        tool_definition: str | None = None,
    ) -> PermissionsDec:
        """
        Set the permission for a tool

        Explicit tool policies override automatic action-based permissions.
        """

        # explicit policy > all
        if tool_name in self.policies:
            return self.policies[tool_name]

        # set the tool permission
        action = self.classify_tool(
            tool_name,
            tool_type,
            tool_definition
        )

        return self.decision_for_action(action)

    def remove_policy(
        self,
        tool_name: str,
    ) -> None:
        self.policies.pop(tool_name, None)

    def set_mode(self, mode: PermissionMode) -> None:
        self.mode = mode

    def get_mode(self) -> PermissionMode:
        return self.mode

    def classify_tool(self, tool_name: str, tool_type: str, tool_definition=None) -> str:
        """
        Classify a tool by the kind of action it performs.

        Returns:
            "read"   -> does not modify external state
            "write"  -> creates, updates, sends, or otherwise modifies state
            "delete" -> destructive / irreversible action
        """

        # Built-in/local tools
        if tool_type == "Local":
            if tool_name.startswith("delete_"):
                return "delete"

            if tool_name.startswith(("create_", "update_", "save_")):
                return "write"

            return "read"

        # Scheduler changes state by creating scheduled work
        if tool_type == "Scheduler":
            return "write"

        # MCP tools are classified using their definition
        if tool_type == "MCP":
            if not tool_definition:
                return "unknown"

            name = tool_definition.get("function", {}).get("name", "").lower()

            # Destructive actions
            if any(word in name for word in [
                "delete",
                "remove",
                "destroy",
            ]):
                return "delete"

            # State-changing actions
            if any(word in name for word in [
                "create",
                "update",
                "modify",
                "edit",
                "write",
                "send",
                "invite",
                "book",
                "move",
                "reschedule",
                "upload",
                "set",
                "add",
                "respond",
            ]):
                return "write"

            # Everything else is treated as read-only
            return "read"
        return "read"        

    def decision_for_action(self, action: str) -> PermissionsDec:
        """
        Convert an action classification into a permission decision,
        according to the current permission mode.
        """

        mode_table = MODE_DECISIONS[self.mode]

        if action in mode_table:
            return mode_table[action]

        return self.default_decision