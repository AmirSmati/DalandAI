"""
Unit tests for Persistent Long-Term Memory (LTM) operations.
"""

import unittest

from tools.memory import (
    save_memory,
    get_memories,
    delete_memory,
    load_all_memories_formatted,
)


class TestMemory(unittest.TestCase):

    def setUp(self):
        # Save baseline memories for testing.
        save_memory(
            "preferences",
            "unit_test_currency",
            "EUR",
            tags=["test", "finance"],
        )

        save_memory(
            "user_profile",
            "unit_test_name",
            "Tester Alex",
            tags=["test", "identity"],
        )

    def tearDown(self):
        # Direct tool-level cleanup.
        # Permission checks are tested separately through the Harness.
        delete_memory("preferences", "unit_test_currency")
        delete_memory("user_profile", "unit_test_name")

    def test_save_and_get_memory(self):
        """Test saving and retrieving a memory."""

        res_save = save_memory(
            "project_context",
            "current_sprint",
            "Sprint 4",
            tags=["agile"],
        )

        self.assertTrue(res_save["success"])
        self.assertEqual(res_save["entry"]["value"], "Sprint 4")

        res_get = get_memories(category="project_context")

        self.assertTrue(res_get["success"])
        self.assertIn(
            "current_sprint",
            res_get["memories"].get("project_context", {}),
        )

        delete_memory("project_context", "current_sprint")

    def test_get_memories_with_query_search(self):
        """Test searching memories by keyword across categories and tags."""

        res = get_memories(query="finance")

        self.assertTrue(res["success"])
        self.assertIn("preferences", res["memories"])
        self.assertIn(
            "unit_test_currency",
            res["memories"]["preferences"],
        )

    def test_load_all_memories_formatted(self):
        """Test formatted memory output for system-prompt injection."""

        formatted = load_all_memories_formatted()

        self.assertIn("Tester Alex", formatted)
        self.assertIn("EUR", formatted)

    def test_delete_memory(self):
        """Test that the memory tool itself can delete an entry."""

        save_memory(
            "learned_facts",
            "temp_fact",
            "Temporary note to delete",
        )

        res_del = delete_memory(
            "learned_facts",
            "temp_fact",
        )

        self.assertTrue(res_del["success"])

        res_get = get_memories(category="learned_facts")

        self.assertNotIn(
            "temp_fact",
            res_get["memories"].get("learned_facts", {}),
        )


if __name__ == "__main__":
    unittest.main()