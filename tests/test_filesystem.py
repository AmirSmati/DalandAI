"""
Unit tests for sandboxed filesystem operations and security guardrails.
"""

import shutil
import unittest
from pathlib import Path
from tools.filesystem import (
    WORKSPACE,
    safe_path,
    list_files,
    read_file,
    create_file,
    create_folder,
    update_file,
    search_files,
)


class TestFilesystem(unittest.TestCase):

    def setUp(self):
        self.test_dir_rel = "notes/test_fs_unit"
        self.test_file_rel = f"{self.test_dir_rel}/sample.txt"
        self.test_content = "Hello Unit Test\nLine 2 for search testing"
        # Ensure clean state before each test
        test_dir_abs = safe_path(self.test_dir_rel)
        if test_dir_abs.exists():
            shutil.rmtree(test_dir_abs)

    def tearDown(self):
        # Recursively clean up the test directory after each test
        test_dir_abs = safe_path(self.test_dir_rel)
        if test_dir_abs.exists():
            shutil.rmtree(test_dir_abs)

    def test_safe_path_valid(self):
        """Verify that valid relative paths resolve within the workspace."""
        path = safe_path("notes/my_note.txt")
        self.assertTrue(str(path).startswith(str(WORKSPACE)))

    def test_safe_path_traversal_blocked(self):
        """Verify that path traversal attempts (../../) are blocked with PermissionError."""
        with self.assertRaises(PermissionError):
            safe_path("../../outside_secret.txt")

        with self.assertRaises(PermissionError):
            safe_path("../../../Windows/System32")

    def test_create_and_read_file(self):
        """Test creating a new file (including parent directory creation) and reading it."""
        res_create = create_file(self.test_file_rel, self.test_content)
        self.assertTrue(res_create["success"])
        self.assertEqual(res_create["path"], self.test_file_rel)

        res_read = read_file(self.test_file_rel)
        self.assertTrue(res_read["success"])
        self.assertEqual(res_read["content"], self.test_content)

    def test_create_file_already_exists(self):
        """Test that create_file fails gracefully if the file already exists."""
        create_file(self.test_file_rel, self.test_content)
        res = create_file(self.test_file_rel, "New content")
        self.assertFalse(res["success"])
        self.assertIn("already exists", res["error"])

    def test_update_file(self):
        """Test updating an existing file."""
        create_file(self.test_file_rel, self.test_content)
        updated_content = "Updated content line 1\nUpdated line 2"
        res_update = update_file(self.test_file_rel, updated_content)
        self.assertTrue(res_update["success"])

        res_read = read_file(self.test_file_rel)
        self.assertEqual(res_read["content"], updated_content)

    def test_update_nonexistent_file(self):
        """Test that updating a non-existent file returns a clean error."""
        res = update_file("notes/nonexistent_file_123.txt", "content")
        self.assertFalse(res["success"])
        self.assertIn("does not exist", res["error"])

    def test_list_files(self):
        """Test listing directory entries."""
        create_file(self.test_file_rel, self.test_content)
        res = list_files(self.test_dir_rel)
        self.assertTrue(res["success"])
        entry_names = [e["name"] for e in res["entries"]]
        self.assertIn("sample.txt", entry_names)

    def test_search_files(self):
        """Test case-insensitive substring search across workspace files."""
        create_file(self.test_file_rel, self.test_content)
        res = search_files("search testing", path=self.test_dir_rel)
        self.assertTrue(res["success"])
        self.assertGreater(len(res["matches"]), 0)
        self.assertEqual(res["matches"][0]["line_number"], 2)


if __name__ == "__main__":
    unittest.main()
