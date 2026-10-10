import pytest

from harness.harness import Harness
from permissions.manager import (
    PermissionManager,
    PermissionMode,
    PermissionsDec,
)
from tools.registry import TOOL_REGISTRY


@pytest.mark.asyncio
async def test_permission_modes_e2e():
    calls = []

    def create_permission_test():
        calls.append("executed")
        return {
            "success": True,
            "result": "test tool executed",
        }

    TOOL_REGISTRY["create_permission_test"] = create_permission_test

    try:
        permission_manager = PermissionManager()

        harness = Harness(
            permission_manager=permission_manager,
            confirmation_callback=lambda tool_name: "n",
        )

        # DEFAULT: write requires confirmation
        permission_manager.set_mode(PermissionMode.DEFAULT)

        result = await harness.execute(
            tool_name="create_permission_test",
            tool_type="Local",
            arguments={},
            run_id="permission-default-test",
        )

        assert result["success"] is False
        assert len(calls) == 0

        # AUTO: write is allowed
        permission_manager.set_mode(PermissionMode.AUTO)

        result = await harness.execute(
            tool_name="create_permission_test",
            tool_type="Local",
            arguments={},
            run_id="permission-auto-test",
        )

        assert result["success"] is True
        assert len(calls) == 1

        # BYPASS: write is allowed
        permission_manager.set_mode(PermissionMode.BYPASS)

        result = await harness.execute(
            tool_name="create_permission_test",
            tool_type="Local",
            arguments={},
            run_id="permission-bypass-test",
        )

        assert result["success"] is True
        assert len(calls) == 2

        # Explicit DENY overrides the mode
        permission_manager.set_policy(
            "create_permission_test",
            PermissionsDec.DENY,
        )

        result = await harness.execute(
            tool_name="create_permission_test",
            tool_type="Local",
            arguments={},
            run_id="permission-deny-test",
        )

        assert result["success"] is False
        assert len(calls) == 2

    finally:
        TOOL_REGISTRY.pop("create_permission_test", None)