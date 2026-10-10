import asyncio

from harness.harness import Harness
from permissions.manager import PermissionManager, PermissionsDec


async def main():

    # Create permission manager
    permissions = PermissionManager(
        default_decision=PermissionsDec.DENY
    )


    # Explicitly deny this tool
    permissions.set_policy(
        "find_events",
        PermissionsDec.DENY
    )

    #Conifrm 
    permissions.set_policy(
        "get_memories",
        PermissionsDec.COONFIRM
    )

    # Give permissions to the Harness
    harness = Harness(
        permission_manager=permissions
    )

    # Test ALLOW
    print("\n--- Coonfirm TEST ---")

    result = await harness.execute(
        tool_name="get_memories",
        tool_type="Local",
        arguments={
            "query": "AI Agent project"
        }
    )

    print(result)

    # Test DENY
    print("\n--- DENY TEST ---")

    result = await harness.execute(
        tool_name="find_events",
        tool_type="MCP",
        arguments={
            "query": "meetings"
        },
        run_id="permission-test-001",
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())