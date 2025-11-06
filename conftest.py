"""Pytest configuration - loads .env file for all tests."""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
dotenv_path = Path(__file__).parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"✓ Loaded environment variables from {dotenv_path}")
else:
    print("⚠ No .env file found - integration tests will be skipped")


@pytest.fixture(scope="function", autouse=True)
def change_test_dir(request, monkeypatch):
    """Change to tests/output directory for chart generation during tests.

    This ensures all test-generated chart files are stored in tests/output/
    instead of cluttering the root directory.
    """
    # Get the test output directory
    test_output_dir = Path(__file__).parent / "tests" / "output"
    test_output_dir.mkdir(parents=True, exist_ok=True)

    # Change to the test output directory
    monkeypatch.chdir(test_output_dir)
