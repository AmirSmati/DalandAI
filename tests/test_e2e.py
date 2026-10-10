import asyncio
import uuid

import pytest

from agent.agent import Agent
from mcp_client.server_process import MCPServerProcess
from permissions.manager import PermissionMode


def assert_success(result, action):
    """
    Assert that a tool execution succeeded and provide the returned payload
    when it did not.
    """
    assert isinstance(result, dict), (
        f"{action} returned a non-dict result: {result!r}"
    )

    assert result.get("success") is True, (
        f"{action} failed: {result}"
    )


async def _run_full_agent_e2e():
    """
    Full live end-to-end system test.

    The test intentionally exercises the real application stack rather than
    mocking the Agent, Harness, Planner, Scheduler, MCP layer, or filesystem
    tools.

    Covered runtime paths:

        Agent
          ↓
        MCPManager
          ↓
        Dynamic MCP discovery
          ↓
        ToolRouter
          ↓
        Planner
          ↓
        ReAct
          ↓
        Harness
          ↓
        PermissionManager
          ↓
        Local tools / MCP tools
          ↓
        Memory
          ↓
        Scheduler
          ↓
        Sub-Agents
          ↓
        Final result
          ↓
        Cleanup
    """

    unique_id = uuid.uuid4().hex[:10]

    workspace_root = f"e2e_full_{unique_id}"
    docs_dir = f"{workspace_root}/docs"
    nested_dir = f"{docs_dir}/nested"

    main_file = f"{workspace_root}/main_test.txt"
    invoice_file = f"{docs_dir}/invoice.txt"
    nested_file = f"{nested_dir}/nested_notes.txt"

    single_csv = f"{workspace_root}/single_classification.csv"
    single_xlsx = f"{workspace_root}/single_classification.xlsx"

    folder_csv = f"{workspace_root}/folder_classification.csv"
    folder_xlsx = f"{workspace_root}/folder_classification.xlsx"

    re_act_file = f"{workspace_root}/react_result.txt"

    memory_key = f"e2e_memory_{unique_id}"

    # ------------------------------------------------------------------
    # START REAL MCP SERVER + REAL AGENT
    # ------------------------------------------------------------------

    email_server = MCPServerProcess()
    email_server.start()

    agent = Agent()

    # Make the E2E fully automated.
    # State-changing tools still go through the real permission system,
    # but confirmation is supplied programmatically instead of requiring
    # interactive stdin.
    def approve_confirmation(tool_name):
        print(f"[E2E] Automatically approving: {tool_name}")
        return "y"

    agent.harness.confirmation_callback = approve_confirmation

    try:
        # ==============================================================
        # 1. AGENT INITIALIZATION
        # ==============================================================

        assert agent.client is not None
        assert agent.model
        assert agent.scheduler is not None
        assert agent.mcp is not None
        assert agent.harness is not None
        assert agent.planner is not None
        assert agent.memory is not None
        assert agent.tool_router is not None

        # ==============================================================
        # 2. PERMISSION MODE API
        # ==============================================================

        original_permission_mode = agent.get_permission_mode()

        agent.set_permission_mode(PermissionMode.DEFAULT)
        assert agent.get_permission_mode() == PermissionMode.DEFAULT

        agent.set_permission_mode(PermissionMode.AUTO)
        assert agent.get_permission_mode() == PermissionMode.AUTO

        agent.set_permission_mode(PermissionMode.BYPASS)
        assert agent.get_permission_mode() == PermissionMode.BYPASS

        # Restore the normal mode before actual permission tests.
        agent.set_permission_mode(original_permission_mode)

        # ==============================================================
        # 3. MCP STARTUP + DISCOVERY
        # ==============================================================

        await agent.start()

        assert agent.mcp is not None
        assert agent.mcp_tools is not None
        assert isinstance(agent.mcp_tools, list)
        assert len(agent.mcp_tools) > 0

        assert agent.tool_router is not None

        discovered_mcp_names = {
            tool.get("function", {}).get("name")
            for tool in agent.mcp_tools
            if isinstance(tool, dict)
        }

        discovered_mcp_names.discard(None)

        assert discovered_mcp_names, (
            "MCP startup completed but no MCP tools were discovered."
        )

        print(
            "\n[E2E] Discovered MCP tools:",
            sorted(discovered_mcp_names),
        )

        # ==============================================================
        # 4. LOCAL TOOL REGISTRY
        # ==============================================================

        local_tools = agent.harness.tools

        expected_local_tools = {
            "list_files",
            "read_file",
            "create_folder",
            "create_file",
            "update_file",
            "search_files",
            "extract_and_classify_document",
            "extract_and_classify_folder",
            "save_memory",
            "get_memories",
            "delete_memory",
        }

        missing_tools = expected_local_tools.difference(local_tools.keys())

        assert not missing_tools, (
            f"Missing expected local tools: {sorted(missing_tools)}"
        )

        # There is intentionally no file deletion tool.
        assert "delete_file" not in local_tools
        assert "delete_folder" not in local_tools

        # ==============================================================
        # 5. REAL MCP TOOL EXECUTION
        # ==============================================================

        # Exa is the MCP search service already used by the system's
        # research workflow.
        if "web_search_exa" not in discovered_mcp_names:
            pytest.fail(
                "Expected the dynamically discovered MCP tool "
                "'web_search_exa' but it was not available."
            )

        mcp_result = await agent.harness.execute(
            "web_search_exa",
            "MCP",
            {
                "query": "Model Context Protocol MCP architecture",
            },
            run_id=f"e2e-mcp-{unique_id}",
        )

        assert_success(
            mcp_result,
            "web_search_exa",
        )

        # ==============================================================
        # 6. DEFAULT PERMISSION MODE — REJECTION
        # ==============================================================

        agent.set_permission_mode(PermissionMode.DEFAULT)

        original_callback = agent.harness.confirmation_callback

        def reject_confirmation(tool_name):
            print(f"[E2E] Automatically rejecting: {tool_name}")
            return "n"

        agent.harness.confirmation_callback = reject_confirmation

        rejected_folder = f"{workspace_root}/rejected"

        rejected_result = await agent.harness.execute(
            "create_folder",
            "Local",
            {
                "path": rejected_folder,
            },
            run_id=f"e2e-permission-reject-{unique_id}",
        )

        assert rejected_result.get("success") is False
        assert "denied" in rejected_result.get(
            "error",
            "",
        ).lower()

        # Restore approval.
        agent.harness.confirmation_callback = original_callback

        # ==============================================================
        # 7. DEFAULT PERMISSION MODE — APPROVAL
        # ==============================================================

        agent.set_permission_mode(PermissionMode.DEFAULT)

        create_root_result = await agent.harness.execute(
            "create_folder",
            "Local",
            {
                "path": workspace_root,
            },
            run_id=f"e2e-create-root-{unique_id}",
        )

        assert_success(
            create_root_result,
            "create_folder(workspace root)",
        )

        create_docs_result = await agent.harness.execute(
            "create_folder",
            "Local",
            {
                "path": docs_dir,
            },
            run_id=f"e2e-create-docs-{unique_id}",
        )

        assert_success(
            create_docs_result,
            "create_folder(docs)",
        )

        create_nested_result = await agent.harness.execute(
            "create_folder",
            "Local",
            {
                "path": nested_dir,
            },
            run_id=f"e2e-create-nested-{unique_id}",
        )

        assert_success(
            create_nested_result,
            "create_folder(nested)",
        )

        # ==============================================================
        # 8. CREATE FILE
        # ==============================================================

        original_content = (
            f"Full E2E integration test {unique_id}\n"
            "Harness filesystem workflow.\n"
        )

        create_file_result = await agent.harness.execute(
            "create_file",
            "Local",
            {
                "path": main_file,
                "content": original_content,
            },
            run_id=f"e2e-create-file-{unique_id}",
        )

        assert_success(
            create_file_result,
            "create_file",
        )

        # ==============================================================
        # 9. READ FILE
        # ==============================================================

        read_file_result = await agent.harness.execute(
            "read_file",
            "Local",
            {
                "path": main_file,
            },
            run_id=f"e2e-read-file-{unique_id}",
        )

        assert_success(
            read_file_result,
            "read_file",
        )

        assert (
            read_file_result.get("content")
            == original_content
        )

        # ==============================================================
        # 10. UPDATE FILE
        # ==============================================================

        updated_content = (
            f"UPDATED E2E CONTENT {unique_id}\n"
            "The update_file operation was executed successfully.\n"
        )

        update_file_result = await agent.harness.execute(
            "update_file",
            "Local",
            {
                "path": main_file,
                "content": updated_content,
            },
            run_id=f"e2e-update-file-{unique_id}",
        )

        assert_success(
            update_file_result,
            "update_file",
        )

        verify_update_result = await agent.harness.execute(
            "read_file",
            "Local",
            {
                "path": main_file,
            },
            run_id=f"e2e-verify-update-{unique_id}",
        )

        assert_success(
            verify_update_result,
            "read_file(after update)",
        )

        assert (
            verify_update_result.get("content")
            == updated_content
        )

        # ==============================================================
        # 11. SEARCH FILES
        # ==============================================================

        search_token = f"UNIQUE_E2E_TOKEN_{unique_id}"

        search_update = await agent.harness.execute(
            "update_file",
            "Local",
            {
                "path": main_file,
                "content": (
                    f"{updated_content}"
                    f"{search_token}\n"
                ),
            },
            run_id=f"e2e-search-setup-{unique_id}",
        )

        assert_success(
            search_update,
            "update_file(search token)",
        )

        search_result = await agent.harness.execute(
            "search_files",
            "Local",
            {
                "query": search_token,
                "path": workspace_root,
            },
            run_id=f"e2e-search-{unique_id}",
        )

        assert_success(
            search_result,
            "search_files",
        )

        assert search_token.lower() in str(
            search_result
        ).lower()

        # ==============================================================
        # 12. LIST FILES
        # ==============================================================

        root_listing = await agent.harness.execute(
            "list_files",
            "Local",
            {
                "path": workspace_root,
            },
            run_id=f"e2e-list-root-{unique_id}",
        )

        assert_success(
            root_listing,
            "list_files(root)",
        )

        root_entries = root_listing.get(
            "entries",
            [],
        )

        root_names = {
            entry.get("name")
            for entry in root_entries
            if isinstance(entry, dict)
        }

        assert "main_test.txt" in root_names
        assert "docs" in root_names

        docs_listing = await agent.harness.execute(
            "list_files",
            "Local",
            {
                "path": docs_dir,
            },
            run_id=f"e2e-list-docs-{unique_id}",
        )

        assert_success(
            docs_listing,
            "list_files(docs)",
        )

        # ==============================================================
        # 13. CREATE DOCUMENTS FOR CLASSIFICATION
        # ==============================================================

        invoice_content = (
            "INVOICE\n"
            "Customer: E2E Test\n"
            "Invoice number: 12345\n"
            "Total: 250 EUR\n"
        )

        nested_content = (
            "PROJECT NOTES\n"
            "This document belongs to the AI agent E2E test.\n"
        )

        invoice_create = await agent.harness.execute(
            "create_file",
            "Local",
            {
                "path": invoice_file,
                "content": invoice_content,
            },
            run_id=f"e2e-create-invoice-{unique_id}",
        )

        assert_success(
            invoice_create,
            "create_file(invoice)",
        )

        nested_create = await agent.harness.execute(
            "create_file",
            "Local",
            {
                "path": nested_file,
                "content": nested_content,
            },
            run_id=f"e2e-create-nested-file-{unique_id}",
        )

        assert_success(
            nested_create,
            "create_file(nested document)",
        )

        # ==============================================================
        # 14. SINGLE DOCUMENT CLASSIFICATION
        # ==============================================================

        document_classification = await agent.harness.execute(
            "extract_and_classify_document",
            "Local",
            {
                "source_path": invoice_file,
                "csv_output_path": single_csv,
                "xlsx_output_path": single_xlsx,
                "classification_rules": {
                    "invoice": [
                        "invoice",
                        "total",
                    ],
                    "project": [
                        "project",
                        "agent",
                    ],
                },
                "default_category": "unclassified",
            },
            run_id=f"e2e-classify-document-{unique_id}",
        )

        assert_success(
            document_classification,
            "extract_and_classify_document",
        )

        # Verify generated outputs through the real filesystem tool.
        classification_listing = await agent.harness.execute(
            "list_files",
            "Local",
            {
                "path": workspace_root,
            },
            run_id=f"e2e-list-classification-{unique_id}",
        )

        assert_success(
            classification_listing,
            "list_files(classification outputs)",
        )

        classification_names = {
            entry.get("name")
            for entry in classification_listing.get(
                "entries",
                [],
            )
            if isinstance(entry, dict)
        }

        assert "single_classification.csv" in classification_names
        assert "single_classification.xlsx" in classification_names

        # ==============================================================
        # 15. FOLDER CLASSIFICATION
        # ==============================================================

        folder_classification = await agent.harness.execute(
            "extract_and_classify_folder",
            "Local",
            {
                "source_directory": docs_dir,
                "csv_output_path": folder_csv,
                "xlsx_output_path": folder_xlsx,
                "classification_rules": {
                    "invoice": [
                        "invoice",
                        "total",
                    ],
                    "project": [
                        "project",
                        "agent",
                    ],
                },
                "default_category": "unclassified",
                "recursive": True,
                "max_files": 10,
            },
            run_id=f"e2e-classify-folder-{unique_id}",
        )

        assert_success(
            folder_classification,
            "extract_and_classify_folder",
        )

        folder_output_listing = await agent.harness.execute(
            "list_files",
            "Local",
            {
                "path": workspace_root,
            },
            run_id=f"e2e-list-folder-classification-{unique_id}",
        )

        assert_success(
            folder_output_listing,
            "list_files(folder classification outputs)",
        )

        folder_output_names = {
            entry.get("name")
            for entry in folder_output_listing.get(
                "entries",
                [],
            )
            if isinstance(entry, dict)
        }

        assert "folder_classification.csv" in folder_output_names
        assert "folder_classification.xlsx" in folder_output_names

        # ==============================================================
        # 16. MEMORY LIFECYCLE
        # ==============================================================

        memory_value = (
            f"Full E2E semantic memory value {unique_id}"
        )

        save_memory_result = await agent.harness.execute(
            "save_memory",
            "Local",
            {
                "category": "e2e",
                "key": memory_key,
                "value": memory_value,
                "tags": [
                    "e2e",
                    "integration",
                    unique_id,
                ],
            },
            run_id=f"e2e-save-memory-{unique_id}",
        )

        assert_success(
            save_memory_result,
            "save_memory",
        )

        get_memory_result = await agent.harness.execute(
            "get_memories",
            "Local",
            {
                "category": "e2e",
            },
            run_id=f"e2e-get-memory-{unique_id}",
        )

        assert_success(
            get_memory_result,
            "get_memories(category)",
        )

        assert memory_key in str(
            get_memory_result.get("memories", {})
        )

        query_memory_result = await agent.harness.execute(
            "get_memories",
            "Local",
            {
                "query": unique_id,
            },
            run_id=f"e2e-query-memory-{unique_id}",
        )

        assert_success(
            query_memory_result,
            "get_memories(query)",
        )

        assert memory_key in str(
            query_memory_result.get("memories", {})
        )

        # Exercise the MemoryManager semantic retrieval layer itself.
        relevant_memory = agent.memory.get_relevant_memory(
            f"semantic memory integration {unique_id}"
        )

        assert memory_key in relevant_memory
        assert memory_value in relevant_memory

        # ==============================================================
        # 17. SHORT-TERM MEMORY / CONTEXT BUILDING
        # ==============================================================

        agent.memory.add_turn(
            [
                {
                    "role": "user",
                    "content": (
                        f"Short-term E2E context {unique_id}"
                    ),
                },
                {
                    "role": "assistant",
                    "content": "Context acknowledged.",
                },
            ]
        )

        assert len(agent.memory.conversation_turns) >= 1

        built_context = agent.memory.build_context(
            system_prompt="E2E system prompt.",
            current_turn=[
                {
                    "role": "user",
                    "content": "Current E2E turn.",
                }
            ],
            memory_query=None,
        )

        assert isinstance(built_context, list)
        assert built_context
        assert built_context[0]["role"] == "system"

        # Reset short-term context.
        agent.reset_context()

        assert agent.memory.conversation_turns == []
        assert agent.memory.summary == ""

        # ==============================================================
        # 18. MEMORY DELETE — CONFIRMATION PATH
        # ==============================================================

        delete_memory_result = await agent.harness.execute(
            "delete_memory",
            "Local",
            {
                "category": "e2e",
                "key": memory_key,
            },
            run_id=f"e2e-delete-memory-{unique_id}",
        )

        assert_success(
            delete_memory_result,
            "delete_memory",
        )

        verify_deleted_memory = await agent.harness.execute(
            "get_memories",
            "Local",
            {
                "category": "e2e",
                "query": unique_id,
            },
            run_id=f"e2e-verify-memory-delete-{unique_id}",
        )

        assert_success(
            verify_deleted_memory,
            "get_memories(after delete)",
        )

        assert memory_key not in str(
            verify_deleted_memory.get("memories", {})
        )

        # ==============================================================
        # 19. UNKNOWN TOOL ERROR HANDLING
        # ==============================================================

        unknown_tool_result = await agent.harness.execute(
            "this_tool_does_not_exist",
            "Local",
            {},
            run_id=f"e2e-unknown-tool-{unique_id}",
        )

        assert unknown_tool_result.get("success") is False
        assert "error" in unknown_tool_result

        # ==============================================================
        # 20. PATH TRAVERSAL PROTECTION
        # ==============================================================

        traversal_result = await agent.harness.execute(
            "read_file",
            "Local",
            {
                "path": "../outside_workspace.txt",
            },
            run_id=f"e2e-traversal-{unique_id}",
        )

        assert traversal_result.get("success") is False
        assert "error" in traversal_result

        # ==============================================================
        # 21. SCHEDULER FAILURE + CLEAR PATH
        # ==============================================================

        agent.scheduler.clear()

        failed_task = {
            "id": f"e2e_failed_task_{unique_id}",
            "description": "Intentional scheduler failure test.",
            "depends_on": [],
        }

        agent.scheduler.add_task(failed_task)

        ready_tasks = agent.scheduler.get_ready_tasks()

        assert any(
            task.get("id") == failed_task["id"]
            for task in ready_tasks
        )

        agent.scheduler.mark_failed(
            failed_task["id"],
            "Intentional E2E failure.",
        )

        failed_task_state = agent.scheduler.get_task(
            failed_task["id"]
        )

        assert failed_task_state is not None
        assert failed_task_state["status"] == "failed"

        agent.scheduler.clear()

        assert agent.scheduler.has_pending_tasks() is False

        # ==============================================================
        # 22. REAL REACT → HARNESS → PERMISSION → FILESYSTEM
        # ==============================================================

        agent.set_permission_mode(PermissionMode.DEFAULT)

        agent.harness.confirmation_callback = approve_confirmation

        react_task = f"""
        Create a file named {re_act_file} inside the workspace.
        Put exactly this text in the file:

        REACT_E2E_SUCCESS_{unique_id}

        Do not perform any other actions.
        """

        react_result = await agent.run(
            user_task=react_task,
            allow_decomposition=False,
        )

        assert react_result is not None
        assert str(react_result).strip()

        react_verify_result = await agent.harness.execute(
            "read_file",
            "Local",
            {
                "path": re_act_file,
            },
            run_id=f"e2e-react-verify-{unique_id}",
        )

        assert_success(
            react_verify_result,
            "read_file(ReAct result)",
        )

        assert (
            react_verify_result.get("content", "").strip()
            == f"REACT_E2E_SUCCESS_{unique_id}"
        )

        # ==============================================================
        # 23. AUTO MODE
        # ==============================================================

        agent.set_permission_mode(PermissionMode.AUTO)

        auto_file = f"{workspace_root}/auto_mode.txt"

        # Deliberately reject confirmations. AUTO mode should not need one
        # for write operations.
        agent.harness.confirmation_callback = reject_confirmation

        auto_result = await agent.harness.execute(
            "create_file",
            "Local",
            {
                "path": auto_file,
                "content": f"AUTO_MODE_{unique_id}",
            },
            run_id=f"e2e-auto-mode-{unique_id}",
        )

        assert_success(
            auto_result,
            "create_file(AUTO mode)",
        )

        agent.harness.confirmation_callback = approve_confirmation
        agent.set_permission_mode(PermissionMode.DEFAULT)

        # ==============================================================
        # 24. BYPASS MODE
        # ==============================================================

        agent.set_permission_mode(PermissionMode.BYPASS)

        bypass_file = f"{workspace_root}/bypass_mode.txt"

        agent.harness.confirmation_callback = reject_confirmation

        bypass_result = await agent.harness.execute(
            "create_file",
            "Local",
            {
                "path": bypass_file,
                "content": f"BYPASS_MODE_{unique_id}",
            },
            run_id=f"e2e-bypass-mode-{unique_id}",
        )

        assert_success(
            bypass_result,
            "create_file(BYPASS mode)",
        )

        agent.harness.confirmation_callback = approve_confirmation
        agent.set_permission_mode(PermissionMode.DEFAULT)

        # ==============================================================
        # 25. FULL PLANNER + DAG SCHEDULER + SUB-AGENT WORKFLOW
        # ==============================================================

        agent.reset_context()
        agent.scheduler.clear()

        complex_task = """
        Perform two independent research tasks using the web search tools.

        Task 1:
        Research the Model Context Protocol (MCP) and summarize its purpose,
        architecture, and role in AI agent systems.

        Task 2:
        Research long-term memory in AI agents and summarize common approaches
        and why memory is useful for agent systems.

        After both independent research tasks are complete, compare their
        findings and produce a concise structured summary.

        Do not create, modify, or delete workspace files.
        """

        scheduled_result = await agent.run(
            user_task=complex_task,
            allow_decomposition=True,
        )

        assert scheduled_result is not None
        assert str(scheduled_result).strip()

        # The complex request is intended to create:
        #
        #   task_1 ─┐
        #           ├──> task_3
        #   task_2 ─┘
        #
        # The planner used in the project numbers generated tasks this way.

        task_1 = agent.scheduler.get_task("task_1")
        task_2 = agent.scheduler.get_task("task_2")
        task_3 = agent.scheduler.get_task("task_3")

        assert task_1 is not None
        assert task_2 is not None
        assert task_3 is not None

        assert task_1["status"] == "completed"
        assert task_2["status"] == "completed"
        assert task_3["status"] == "completed"

        assert set(task_3.get("depends_on", [])) >= {
            "task_1",
            "task_2",
        }

        assert agent.scheduler.has_pending_tasks() is False
        assert agent.scheduler.get_ready_tasks() == []

        # ==============================================================
        # 26. FINAL STATE CHECKS
        # ==============================================================

        assert agent.get_permission_mode() == PermissionMode.DEFAULT
        assert agent.scheduler.has_pending_tasks() is False

        assert agent.mcp is not None
        assert agent.mcp_tools is not None
        assert len(agent.mcp_tools) > 0

        print(
            "\n============================================================"
        )
        print("[FULL E2E] ALL INTEGRATED WORKFLOWS COMPLETED SUCCESSFULLY")
        print(
            "============================================================"
        )
        print(f"[FULL E2E] Test ID: {unique_id}")
        print(f"[FULL E2E] Workspace: {workspace_root}")

    finally:
        # ==============================================================
        # ALWAYS CLOSE MCP CONNECTIONS
        # ==============================================================

        agent.set_permission_mode(PermissionMode.DEFAULT)
        agent.harness.confirmation_callback = approve_confirmation

        await agent.close()


@pytest.mark.asyncio
async def test_full_agent_e2e():
    """
    Pytest entry point.

    pytest-asyncio executes the async test function, while the actual E2E
    implementation remains in _run_full_agent_e2e() so the same workflow can
    also be executed directly with asyncio.run().
    """
    await _run_full_agent_e2e()


def main():
    asyncio.run(_run_full_agent_e2e())


if __name__ == "__main__":
    main()