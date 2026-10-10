"""
Unit tests for the Execution Harness and tool dispatching.
"""

import unittest

from harness.harness import Harness
from tools.registry import TOOL_REGISTRY


class TestHarness(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.harness = Harness(
            confirmation_callback=lambda tool_name: "y"
        )

    def test_tool_registry_complete(self):
        """Verify that all required tools are registered."""

        expected_tools = {
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

        self.assertEqual(set(TOOL_REGISTRY.keys()), expected_tools)

    async def test_execute_known_tool(self):
        """Test executing a registered local tool."""

        res = await self.harness.execute(
            "list_files",
            "Local",
            {"path": "."},
        )

        self.assertTrue(res["success"])
        self.assertIn("entries", res)

    async def test_execute_unknown_tool(self):
        """Test that unknown tools fail safely."""

        res = await self.harness.execute(
            "non_existent_fake_tool",
            "Local",
            {},
        )

        self.assertFalse(res["success"])
        self.assertIn("Unknown tool", res["error"])

    async def test_execute_with_invalid_arguments(self):
        """Test handling invalid tool arguments."""

        res = await self.harness.execute(
            "read_file",
            "Local",
            {"wrong_arg_name": "val"},
        )

        self.assertFalse(res["success"])
        self.assertIn("error", res)


if __name__ == "__main__":
    unittest.main()