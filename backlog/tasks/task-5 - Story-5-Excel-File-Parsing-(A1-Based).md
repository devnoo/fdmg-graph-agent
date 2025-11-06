---
id: task-5
title: 'Story 5: Excel File Parsing (A1-Based)'
status: Done
assignee: []
created_date: '2025-11-06 13:26'
updated_date: '2025-11-06 20:00'
labels:
  - phase-3
  - excel
  - pandas
  - data-parsing
dependencies:
  - task-4
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
This story adds Excel file support to the agent. Users can provide an Excel file path instead of typing data directly. The agent will extract data from the file using a simple "A1-Based" approach.

Per the architecture, this is a simplified MVP approach: look for data starting at cell A1 in the first sheet that contains valid data.

## User Story
**As a journalist**, I want to provide an Excel file path so the agent can read my data directly, saving me from manually typing it into the prompt.

## Technical Requirements

### Supported File Formats
- `.xlsx` (modern Excel format)
- `.xls` (legacy Excel format)

### File Path Support
Both relative and absolute paths:
- Relative: `graph-agent "chart from data.xlsx" --style fd --type bar`
- Absolute: `graph-agent "chart from /Users/me/docs/sales.xlsx" --style bnr --type line`

### A1-Based Parsing Logic
**Simplified approach for MVP:**

1. **Single Sheet Files**: If the Excel file has only one sheet, use that sheet
2. **Multiple Sheet Files**: Scan sheets in order, use the first sheet that contains data starting at A1
3. **Data Block Format**: Expect 2-column format at A1:
   - Column 1 (A): Labels (text)
   - Column 2 (B): Values (numbers)
   - Row 1: Optional headers (will be skipped if detected)

**Example Excel Data:**
```
| A      | B    |
|--------|------|
| Label  | Value| ← Headers (row 1)
| Q1     | 120  |
| Q2     | 150  |
| Q3     | 140  |
| Q4     | 180  |
```

### Implementation Tool: `parse_excel_a1`
Create in `tools.py`:
```python
def parse_excel_a1(file_path: str) -> str:
    """
    Parse Excel file using A1-based logic.
    Returns: JSON string of data: '[{"label": "...", "value": ...}, ...]'
    Raises: ValueError if file not found or no valid data
    """
```

### LangGraph Integration
Add new node `call_data_tool` that:
1. Checks if user mentioned a file path
2. Extracts file path from the message
3. Calls `parse_excel_a1(file_path)`
4. Saves result to `state.input_data`

### Updated Flow
```
parse_intent → (if file path present) → call_data_tool → generate_chart
             → (if no file, has inline data) → extract_data → generate_chart
             → (if off_topic) → reject_task
```

## Example Interactions

### Direct Mode
```bash
$ graph-agent "create chart from sales.xlsx" --style fd --format png --type bar

Parsing Excel file...
Chart saved: /home/user/projects/chart-20251106141500.png
```

### Conversational Mode
```bash
$ graph-agent

> Make a bar chart from quarterly_revenue.xlsx. Use BNR style, PNG format.

Parsing Excel file...
Chart saved: /home/user/projects/chart-20251106141530.png
```

## Error Handling
The tool should raise clear errors for:
- File not found: "Error: Could not find file 'data.xlsx'"
- Invalid format: "Error: File must be .xlsx or .xls format"
- No data at A1: "Error: No valid data found at cell A1 in any sheet"
- Invalid data structure: "Error: Expected 2-column format (Label, Value)"

## Out of Scope (Future Backlog)
Per architecture v1.3, these are explicitly deferred:
- Flexible data location (finding data blocks not at A1)
- Multi-sheet ambiguity handling (asking user which sheet)
- Complex data formats (more than 2 columns)
- Smart header detection beyond simple heuristics
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 User can provide Excel file path in prompt (both direct and conversational modes)
- [ ] #2 Agent successfully parses .xlsx files using pandas + openpyxl
- [ ] #3 Agent successfully parses .xls files using pandas + xlrd
- [ ] #4 Data starting at A1 is correctly extracted from single-sheet files
- [ ] #5 For multi-sheet files, the first sheet with data at A1 is used
- [ ] #6 Relative and absolute file paths both work correctly
- [ ] #7 Headers in row 1 are detected and skipped
- [ ] #8 Extracted data is saved to state.input_data in same JSON format as text extraction
- [ ] #9 Charts generated from Excel data match the specified style and type
- [ ] #10 Clear error messages for file not found, invalid format, or no data at A1
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Add Excel Parsing Dependencies
Ensure these are in `pyproject.toml`:
- `pandas>=2.1.0` (already added in Story 1)
- `openpyxl>=3.1.0` (already added in Story 1)
- Optional: `xlrd>=2.0.1` for legacy .xls support

### Step 2: Create `parse_excel_a1` Tool (`tools.py`)
```python
import pandas as pd
from pathlib import Path
import json

def parse_excel_a1(file_path: str) -> str:
    """
    Parse Excel file using A1-based logic.
    Returns JSON string: '[{"label": "...", "value": ...}, ...]'
    """
    # Validate file exists
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"Error: Could not find file '{file_path}'")
    
    # Validate file extension
    if path.suffix.lower() not in ['.xlsx', '.xls']:
        raise ValueError(f"Error: File must be .xlsx or .xls format")
    
    # Read Excel file
    excel_file = pd.ExcelFile(file_path)
    
    # Iterate through sheets to find data at A1
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=0,  # Assume first row is header
            usecols=[0, 1],  # Only read first 2 columns
            nrows=100  # Limit rows for performance
        )
        
        # Check if valid data exists
        if df.shape[0] > 0 and df.shape[1] == 2:
            # Convert to JSON format
            data = []
            for _, row in df.iterrows():
                label = str(row.iloc[0])
                value = float(row.iloc[1])
                data.append({"label": label, "value": value})
            
            return json.dumps(data)
    
    raise ValueError("Error: No valid data found at cell A1 in any sheet")
```

### Step 3: Create `call_data_tool` Node (`agent.py`)
```python
def call_data_tool(state: GraphState) -> GraphState:
    """Extract file path and call parse_excel_a1"""
    from .tools import parse_excel_a1
    
    user_message = state["messages"][-1]["content"]
    
    # Use LLM to extract file path
    # Prompt: "Extract the file path from this message. Return just the path or 'NONE'."
    result = llm.invoke(file_extraction_prompt)
    
    if result.strip().upper() != "NONE":
        file_path = result.strip()
        try:
            data_json = parse_excel_a1(file_path)
            state["input_data"] = data_json
            state["messages"].append({
                "role": "assistant",
                "content": "Parsing Excel file..."
            })
        except ValueError as e:
            # Handle errors by adding error message
            state["messages"].append({
                "role": "assistant",
                "content": str(e)
            })
            state["intent"] = "error"
    
    return state
```

### Step 4: Update `parse_intent` Node to Detect Files
Modify the intent parsing to check for file references:
```python
def parse_intent(state: GraphState) -> GraphState:
    """Detect intent AND whether a file is mentioned"""
    user_message = state["messages"][-1]["content"]
    
    # Enhanced prompt:
    # "Analyze this request. Return JSON:
    #  {
    #    'intent': 'make_chart' or 'off_topic',
    #    'has_file': true or false
    #  }"
    
    result = llm.invoke(enhanced_prompt)
    parsed = json.loads(result)
    
    state["intent"] = parsed["intent"]
    state["has_file"] = parsed.get("has_file", False)
    
    return state
```

### Step 5: Update Graph Flow with Conditional Routing
```python
def route_after_intent(state: GraphState) -> str:
    if state["intent"] == "off_topic":
        return "reject_task"
    elif state.get("has_file"):
        return "call_data_tool"
    else:
        return "extract_data"

workflow = StateGraph(GraphState)
workflow.add_node("parse_intent", parse_intent)
workflow.add_node("reject_task", reject_task)
workflow.add_node("extract_data", extract_data)
workflow.add_node("call_data_tool", call_data_tool)  # NEW
workflow.add_node("generate_chart", generate_chart_tool)

workflow.set_entry_point("parse_intent")
workflow.add_conditional_edges("parse_intent", route_after_intent)
workflow.add_edge("extract_data", "generate_chart")
workflow.add_edge("call_data_tool", "generate_chart")  # NEW
workflow.set_finish_point("reject_task")
workflow.set_finish_point("generate_chart")
```

### Step 6: Update GraphState to Track File Presence
```python
class GraphState(TypedDict):
    messages: list[dict]
    interaction_mode: Literal["direct", "conversational"]
    intent: Literal["make_chart", "off_topic", "error", "unknown"]
    has_file: bool  # NEW
    input_data: str | None
    chart_request: dict | None
    final_filepath: str | None
```

### Step 7: Handle File Path Resolution
Support both relative and absolute paths:
```python
# In parse_excel_a1
from pathlib import Path
import os

def parse_excel_a1(file_path: str) -> str:
    # Resolve relative paths from current working directory
    path = Path(file_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    
    if not path.exists():
        raise ValueError(f"Error: Could not find file '{file_path}'")
    # ... rest of implementation
```

### Testing Strategy

**Unit Tests:**
1. Test `parse_excel_a1`:
   - Create test Excel files with known data
   - Test single-sheet extraction
   - Test multi-sheet extraction (first valid sheet)
   - Test header detection
   - Test error cases: file not found, invalid format, no data

2. Test `call_data_tool`:
   - Mock LLM file path extraction
   - Verify correct tool invocation
   - Verify state updates

**Integration Tests:**
1. Create sample Excel files in test fixtures:
   - `simple.xlsx`: Single sheet with data at A1
   - `multi_sheet.xlsx`: Multiple sheets, data in second sheet
   - `with_headers.xlsx`: Data with header row

2. Test full flow: prompt → parse intent → call data tool → generate chart

**Acceptance Tests (Manual):**
1. Create test file `test_data.xlsx` with sample data
2. Run: `graph-agent "chart from test_data.xlsx" --style fd --type bar`
   - Verify chart created with data from Excel
3. Run conversational: "make a chart from test_data.xlsx, BNR style"
   - Verify chart created
4. Test error: `graph-agent "chart from nonexistent.xlsx" --style fd --type bar`
   - Verify clear error message
<!-- SECTION:PLAN:END -->
