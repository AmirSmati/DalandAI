"""
Test Runner for Local File Agent & Execution Harness.
Discovers and executes the automated test suite using pytest.
"""

import sys
from pathlib import Path
import pytest

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_all_tests():
    print("=" * 70)
    print("       LOCAL FILE AGENT — TEST SUITE EXECUTION")
    print("=" * 70)
    print(f"Root: {PROJECT_ROOT}\n")

    exit_code = pytest.main([
        str(PROJECT_ROOT / "tests"),
        "-v",
    ])

    print("\n" + "=" * 70)
    print("       TEST SUITE FINISHED")
    print("=" * 70)

    if exit_code == 0:
        print("ALL TESTS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("SOME TESTS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())