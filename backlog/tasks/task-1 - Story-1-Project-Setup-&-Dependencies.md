---
id: task-1
title: 'Story 1: Project Setup & Dependencies'
status: To Do
assignee: []
created_date: '2025-11-06 13:22'
updated_date: '2025-11-06 13:23'
labels:
  - phase-1
  - setup
  - dependencies
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
This is the foundation task to prepare the Python environment for the Graph Agent MVP. The project uses `uv` (already installed) as the package manager and requires several key dependencies to be installed.

## Technology Stack
- **Python**: 3.x (specified in .python-version)
- **Package Manager**: uv (fast, modern Python package/virtualenv manager)
- **Core Dependencies**:
  - `langgraph`: State machine orchestration framework
  - `langchain-google-genai`: Google Gemini LLM integration
  - `click`: CLI framework for both direct and conversational modes
  - `matplotlib`: Chart generation with brand styling support
  - `pandas`: Excel file parsing and data manipulation
  - `openpyxl`: Excel file format support for pandas

## Goal
Set up a working Python environment with all necessary dependencies installed and verified, ready for development of the CLI agent.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All dependencies are listed in pyproject.toml with appropriate version constraints
- [ ] #2 Running 'uv sync' successfully installs all dependencies without errors
- [ ] #3 Python virtual environment is created and activated via uv
- [ ] #4 All imports can be verified: 'python -c "import langgraph, click, matplotlib, pandas, langchain_google_genai"' succeeds
- [ ] #5 pyproject.toml includes project metadata (name: graph-agent, description, python version requirement)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Update pyproject.toml
Add all required dependencies to the `[project.dependencies]` section:
```toml
[project]
name = "graph-agent"
version = "0.1.0"
description = "AI-powered CLI tool for creating brand-compliant charts from data"
requires-python = ">=3.10"

dependencies = [
    "langgraph>=0.2.0",
    "langchain-google-genai>=2.0.0",
    "click>=8.1.0",
    "matplotlib>=3.8.0",
    "pandas>=2.1.0",
    "openpyxl>=3.1.0",
]
```

### Step 2: Install Dependencies
Run `uv sync` to install all dependencies and create/update the virtual environment.

### Step 3: Verify Installation
Test that all imports work correctly by running:
```bash
uv run python -c "import langgraph, click, matplotlib, pandas, langchain_google_genai; print('All imports successful')"
```

### Step 4: Document Environment Setup
Ensure the setup is reproducible by verifying:
- `.python-version` file exists with correct Python version
- `pyproject.toml` is complete and well-formatted
- Virtual environment is created in `.venv/` (or uv's default location)

### Testing Strategy
- Manual verification: Run the import test command
- Check `uv.lock` is generated (lockfile for reproducible builds)
- Verify no dependency conflicts reported by uv
<!-- SECTION:PLAN:END -->
