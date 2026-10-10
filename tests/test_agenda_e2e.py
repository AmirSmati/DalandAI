"""
End-to-End Scenario Tests for Google Calendar (Agenda) MCP Feature Integration.

Tests cover:
- Event search
- Event creation
- Event updates
- Task-to-calendar synchronization
- Event deletion
"""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from harness.harness import Harness
from mcp_client.manager import MCPManager
from tools.filesystem import safe_path


class MockCallResult:
    def __init__(self, text: str, is_error: bool = False):
        self.is_error = is_error
        self.content = [
            MagicMock(
                model_dump=lambda: {
                    "type": "text",
                    "text": text,
                }
            )
        ]
        self.structured_content = None


class TestAgendaE2EScenarios(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """Set up a mocked Google Calendar MCP client."""

        self.mock_mcp = MCPManager()
        self.mock_client = AsyncMock()

        # Mock Google Calendar MCP tools
        tool_names = [
            "list_events",
            "create_event",
            "update_event",
            "delete_event",
        ]

        mock_tools = []

        for name in tool_names:
            tool = MagicMock()
            tool.name = name
            tool.description = f"Google Calendar tool: {name}"
            mock_tools.append(tool)

        self.mock_client.list_tools.return_value = MagicMock(
            tools=mock_tools
        )

        # Register mocked Calendar MCP client
        self.mock_mcp.clients = {
            "google_calendar": self.mock_client
        }

        # Automatically approve confirmation-required operations
        self.harness = Harness(
            mcp_manager=self.mock_mcp,
            confirmation_callback=lambda tool_name: "y",
        )

    async def test_scenario_1_calendar_event_search_and_query(self):
        """Test querying upcoming calendar events."""

        self.mock_client.call_tool.return_value = MockCallResult(
            json.dumps([
                {
                    "id": "evt_101",
                    "summary": "AI Engineering Team Sync",
                    "start": "2026-09-10T10:00:00Z",
                    "end": "2026-09-10T11:00:00Z",
                }
            ])
        )

        res = await self.harness.execute(
            "list_events",
            "MCP",
            {
                "calendar_id": "primary",
            },
        )

        self.assertTrue(res["success"])
        self.assertIn("result", res)
        self.assertEqual(
            len(res["result"]["content"]),
            1,
        )
        self.assertIn(
            "AI Engineering Team Sync",
            res["result"]["content"][0]["text"],
        )

    async def test_scenario_2_calendar_event_creation_and_update(self):
        """Test creating and updating a calendar event."""

        # Create event
        self.mock_client.call_tool.return_value = MockCallResult(
            json.dumps({
                "status": "created",
                "id": "evt_102",
                "summary": "Project Evaluation Review",
                "start": "2026-09-11T14:00:00Z",
            })
        )

        create_res = await self.harness.execute(
            "create_event",
            "MCP",
            {
                "calendar_id": "primary",
                "summary": "Project Evaluation Review",
                "start": "2026-09-11T14:00:00Z",
                "end": "2026-09-11T15:00:00Z",
            },
        )

        self.assertTrue(create_res["success"])
        self.assertIn(
            "evt_102",
            create_res["result"]["content"][0]["text"],
        )

        # Update event
        self.mock_client.call_tool.return_value = MockCallResult(
            json.dumps({
                "status": "updated",
                "id": "evt_102",
                "summary": "Project Evaluation Review (Updated)",
                "start": "2026-09-11T15:00:00Z",
            })
        )

        update_res = await self.harness.execute(
            "update_event",
            "MCP",
            {
                "calendar_id": "primary",
                "event_id": "evt_102",
                "summary": "Project Evaluation Review (Updated)",
            },
        )

        self.assertTrue(update_res["success"])
        self.assertIn(
            "Updated",
            update_res["result"]["content"][0]["text"],
        )

    async def test_scenario_3_task_to_calendar_sync_workflow(self):
        """Test synchronizing a workspace task with a calendar event."""

        tasks_path = "organizer/tasks.json"

        # Read workspace tasks
        read_res = await self.harness.execute(
            "read_file",
            "Local",
            {
                "path": tasks_path,
            },
        )

        self.assertTrue(read_res["success"])

        # Create calendar event
        self.mock_client.call_tool.return_value = MockCallResult(
            json.dumps({
                "status": "confirmed",
                "id": "evt_103",
                "summary": "Focus Block: Adding Context to Agent",
            })
        )

        cal_res = await self.harness.execute(
            "create_event",
            "MCP",
            {
                "calendar_id": "primary",
                "summary": "Focus Block: Adding Context to Agent",
                "start": "2026-09-12T09:00:00Z",
                "end": "2026-09-12T11:00:00Z",
            },
        )

        self.assertTrue(cal_res["success"])

        # Create synchronization note
        note_path = "notes/agenda_sync_note.txt"

        try:
            create_note_res = await self.harness.execute(
                "create_file",
                "Local",
                {
                    "path": note_path,
                    "content": (
                        "Calendar Event evt_103 scheduled for task "
                        "'Adding Context to Agent'."
                    ),
                },
            )

            self.assertTrue(create_note_res["success"])

        finally:
            # Clean up created note
            note_file = safe_path(note_path)

            if note_file.exists():
                note_file.unlink()

    async def test_scenario_4_calendar_event_deletion_safeguards(self):
        """Test calendar event deletion with confirmation approval."""

        self.mock_client.call_tool.return_value = MockCallResult(
            json.dumps({
                "status": "deleted",
                "id": "evt_103",
            })
        )

        del_res = await self.harness.execute(
            "delete_event",
            "MCP",
            {
                "calendar_id": "primary",
                "event_id": "evt_103",
            },
        )

        self.assertTrue(del_res["success"])
        self.assertIn(
            "deleted",
            del_res["result"]["content"][0]["text"],
        )


if __name__ == "__main__":
    unittest.main()