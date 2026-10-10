"""
End-to-End scenario tests verifying multi-step assistant workflows.
"""

import json
import unittest

from harness.harness import Harness
from tools.filesystem import safe_path


class TestEndToEndScenarios(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Automatically approve confirmation requests.
        def approve_confirmation(tool_name):
            print(f"[TEST] Automatically approving: {tool_name}")
            return "y"

        self.harness = Harness(
            confirmation_callback=approve_confirmation
        )

    async def test_scenario_1_task_management_workflow(self):
        """
        Scenario 1: Personal Assistant Task & Notes Lifecycle.
        """

        tasks_path = "organizer/tasks.json"
        note_path = "notes/e2e_scenario_note.txt"

        # Read tasks
        read_res = await self.harness.execute(
            "read_file",
            "Local",
            {"path": tasks_path},
        )

        self.assertTrue(read_res["success"])

        tasks = json.loads(read_res["content"])
        self.assertIsInstance(tasks, list)

        # Add task
        new_task = {
            "id": 9999,
            "title": "E2E Automated Scenario Task",
            "due_date": "10-09-2026",
            "status": "pending",
        }

        tasks.append(new_task)

        # Update tasks
        update_res = await self.harness.execute(
            "update_file",
            "Local",
            {
                "path": tasks_path,
                "content": json.dumps(tasks, indent=2),
            },
        )

        self.assertTrue(update_res["success"])

        try:
            # Create note
            create_res = await self.harness.execute(
                "create_file",
                "Local",
                {
                    "path": note_path,
                    "content": (
                        "Meeting notes for task 9999: "
                        "finalize evaluation rubric."
                    ),
                },
            )

            self.assertTrue(create_res["success"])

            # Search note
            search_res = await self.harness.execute(
                "search_files",
                "Local",
                {"query": "task 9999"},
            )

            self.assertTrue(search_res["success"])
            self.assertGreater(len(search_res["matches"]), 0)

        finally:
            # Restore original tasks
            tasks = [
                task
                for task in tasks
                if task.get("id") != 9999
            ]

            await self.harness.execute(
                "update_file",
                "Local",
                {
                    "path": tasks_path,
                    "content": json.dumps(tasks, indent=2),
                },
            )

            # Remove test note
            note_file = safe_path(note_path)

            if note_file.exists():
                note_file.unlink()

    async def test_scenario_2_long_term_memory_lifecycle(self):
        """
        Scenario 2: Persistent Long-Term Memory Lifecycle.
        """

        # Save preference
        res1 = await self.harness.execute(
            "save_memory",
            "Local",
            {
                "category": "preferences",
                "key": "e2e_currency",
                "value": "CHF",
                "tags": ["finance", "e2e"],
            },
        )

        self.assertTrue(res1["success"])

        # Save project context
        res2 = await self.harness.execute(
            "save_memory",
            "Local",
            {
                "category": "project_context",
                "key": "e2e_goal",
                "value": "Build autonomous workspace assistant",
                "tags": ["e2e", "ai"],
            },
        )

        self.assertTrue(res2["success"])

        # Query memories
        query_res = await self.harness.execute(
            "get_memories",
            "Local",
            {"query": "autonomous"},
        )

        self.assertTrue(query_res["success"])
        self.assertIn(
            "project_context",
            query_res["memories"],
        )

        # -----------------------------------------------------
        # Delete requires confirmation.
        # Simulate the user rejecting the operation.
        # -----------------------------------------------------

        original_callback = self.harness.confirmation_callback

        def reject_confirmation(tool_name):
            print(f"[TEST] Automatically rejecting: {tool_name}")
            return "n"

        self.harness.confirmation_callback = reject_confirmation

        try:
            delete_res = await self.harness.execute(
                "delete_memory",
                "Local",
                {
                    "category": "preferences",
                    "key": "e2e_currency",
                },
            )

            self.assertFalse(delete_res["success"])
            self.assertIn(
                "denied",
                delete_res["error"].lower(),
            )

        finally:
            # Restore automatic approval behavior.
            self.harness.confirmation_callback = original_callback

        # -----------------------------------------------------
        # Cleanup: delete the test memory after the security test.
        # -----------------------------------------------------

        cleanup_res = await self.harness.execute(
            "delete_memory",
            "Local",
            {
                "category": "preferences",
                "key": "e2e_currency",
            },
        )

        self.assertTrue(cleanup_res["success"])
    async def test_scenario_3_security_path_traversal_defense(self):
        """
        Scenario 3: Security & Sandboxing Defense.
        """

        traversal_attempts = [
            "../../secret.env",
            "../agent/agent.py",
            "..\\..\\Windows\\System32\\cmd.exe",
        ]

        for path in traversal_attempts:

            res_read = await self.harness.execute(
                "read_file",
                "Local",
                {"path": path},
            )

            self.assertFalse(res_read["success"])

            self.assertIn(
                "denied",
                res_read["error"].lower(),
            )


if __name__ == "__main__":
    unittest.main()