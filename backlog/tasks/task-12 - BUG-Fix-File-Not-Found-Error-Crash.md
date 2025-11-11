---
id: task-12
title: 'BUG: Fix File Not Found Error Crash'
status: Done
assignee: []
created_date: '2025-11-07 07:07'
updated_date: '2025-11-07 11:11'
labels:
  - bug
  - error-handling
  - critical
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

When a user requests a chart from a non-existent Excel file, the system crashes with a `TypeError` instead of providing a graceful error message.

**Scenario:**
```bash
uv run graph-agent "Maak een grafiek van nonexistent.xlsx" --style fd --type bar
```

**Expected Behavior:**
Graceful error message like: "Error: Could not find file 'nonexistent.xlsx'. Please check the file path and try again."

**Actual Behavior:**
System crash with stack trace:
```
TypeError: the JSON object must be str, bytes or bytearray, not NoneType
```

## Root Cause

**Location:** `graph_agent/agent.py` - `call_data_tool` node

The `call_data_tool` node catches the `ValueError` raised by `parse_excel_a1()` when the file is not found, but then continues execution with `None` data instead of routing to the error reporting node.

**Flow:**
1. `parse_excel_a1()` raises `ValueError("Error: Could not find file...")`
2. `call_data_tool` catches exception and logs error
3. BUT continues to `resolve_ambiguity` and `generate_chart` with `input_data=None`
4. `matplotlib_chart_generator()` calls `json.loads(None)` → TypeError crash

## Fix Required

When `parse_excel_a1()` raises a `ValueError`, the agent should:
1. Store the error message in state
2. Route to `report_error` node instead of continuing to chart generation
3. Return user-friendly error message

## Test Cases

- [ ] Non-existent file with Dutch prompt returns Dutch error message
- [ ] Non-existent file with English prompt returns English error message  
- [ ] Invalid file path (e.g., directory instead of file) handled gracefully
- [ ] File exists but is not .xlsx/.xls format returns appropriate error

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 System does not crash when Excel file is not found
- [x] #2 User receives clear error message in the same language as their query
- [x] #3 Error message includes the specific filename that was not found
- [x] #4 Agent handles error gracefully in both direct and conversational modes
<!-- SECTION:DESCRIPTION:END -->

- [x] #5 All test cases pass (non-existent file, invalid path, wrong file format)
<!-- AC:END -->
