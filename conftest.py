"""Pytest configuration - loads .env file for all tests."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
dotenv_path = Path(__file__).parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"✓ Loaded environment variables from {dotenv_path}")
else:
    print("⚠ No .env file found - integration tests will be skipped")
