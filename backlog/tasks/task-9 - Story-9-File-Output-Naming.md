---
id: task-9
title: 'Story 9: File Output Naming'
status: To Do
assignee: []
created_date: '2025-11-06 13:36'
updated_date: '2025-11-06 13:36'
labels:
  - phase-5
  - file-naming
  - cli-options
  - ux
dependencies:
  - task-8
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
This story implements the enhanced file naming logic per the architecture. Currently (from Story 3), charts are saved as `chart-[timestamp].[ext]`. This story adds support for custom filenames via CLI flag and in-query detection.

## User Story
**As a journalist**, I want to specify custom filenames for my charts so they're easier to identify and organize in my file system.

## Naming Priority (from Architecture)
The agent follows this priority order:

1. **CLI Flag (`--output-file`)**: Highest priority
2. **In-Query Detection**: "save as filename.png", "call it revenue_chart.svg"
3. **Fallback**: `chart-[timestamp].[ext]`

## Technical Requirements

### CLI Flag Support
Add `--output-file` option:
```bash
graph-agent "chart: A=10, B=20" --style fd --type bar --output-file my_chart.png
```

### In-Query Detection
Detect filename requests in natural language:
- "Save as quarterly_results.png"
- "Call it revenue_chart.svg"
- "Name the file sales_2024.png"

### File Extension Handling
The agent must ensure the correct extension:
- If user specifies extension, validate it matches format
- If user specifies no extension, add the correct one
- Examples:
  - `--output-file chart.png` + `--format svg` → ERROR: Extension mismatch
  - `--output-file chart` + `--format svg` → Saves as `chart.svg`
  - Query: "save as chart.png" + format is svg → Use svg, save as `chart.svg` (format overrides extension in query)

### Path Handling
- Support relative paths: `./charts/my_chart.png` → Saves in `charts/` subdirectory
- Support absolute paths: `/home/user/docs/chart.png`
- Create parent directories if they don't exist

### Timestamp Fallback
When no filename specified:
```python
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
filename = f"chart-{timestamp}.{format}"
```

## LangGraph Integration

### Update GraphState
```python
class GraphState(TypedDict):
    # ... existing fields ...
    output_filename: str | None  # NEW: User-specified filename
```

### Update `parse_intent` or `extract_data`
Check the user's message for "save as" patterns:
```python
# LLM prompt:
# "Check if the user specified a filename. 
#  Look for patterns like 'save as X', 'call it X', 'name it X'.
#  Return filename or null."
```

### Update `matplotlib_chart_generator` Tool
```python
def matplotlib_chart_generator(
    data: str,
    chart_type: str,
    style: str,
    format: str,
    output_filename: Optional[str] = None  # NEW parameter
) -> str:
    """Generate chart with custom or default filename"""
    
    if output_filename:
        # Use custom filename
        path = Path(output_filename)
        
        # Ensure correct extension
        expected_ext = f".{format}"
        if path.suffix and path.suffix != expected_ext:
            # Replace with correct extension
            path = path.with_suffix(expected_ext)
        elif not path.suffix:
            # Add extension
            path = path.with_suffix(expected_ext)
        
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Fallback to timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        path = Path(f"chart-{timestamp}.{format}")
    
    # Generate and save chart
    fig.savefig(path)
    return str(path.absolute())
```

## Example Interactions

### CLI Flag (Highest Priority)
```bash
$ graph-agent "chart: A=10, B=20, C=30" --style fd --type bar --output-file results.png
Chart saved: /home/user/results.png
```

### In-Query Detection
```bash
$ graph-agent

> Create a bar chart with A=10, B=20. FD style. Save as quarterly_revenue.png

Chart saved: /home/user/quarterly_revenue.png
```

### Priority: CLI Flag Overrides In-Query
```bash
$ graph-agent "chart: A=10, B=20. Save as ignored.png" --style fd --type bar --output-file actual.png
Chart saved: /home/user/actual.png
```

### Fallback When No Filename Specified
```bash
$ graph-agent "chart: A=10, B=20" --style fd --type bar
Chart saved: /home/user/chart-20251106143500.png
```

## Error Handling
Handle edge cases gracefully:
- Invalid characters in filename → sanitize or error
- Extension mismatch → use format's extension, warn user
- Directory doesn't exist → create it
- File already exists → overwrite (or add warning)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CLI --output-file flag sets custom filename
- [ ] #2 Agent detects 'save as' patterns in conversational queries
- [ ] #3 CLI flag takes priority over in-query filename
- [ ] #4 File extension is validated and corrected if needed
- [ ] #5 Missing extension is added based on format
- [ ] #6 Relative paths work correctly (saves in subdirectories)
- [ ] #7 Absolute paths work correctly
- [ ] #8 Parent directories are created if they don't exist
- [ ] #9 Fallback to chart-[timestamp].[ext] when no filename specified
- [ ] #10 Timestamp format is YYYYMMDDHHmmss (14 digits)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Add CLI Flag
Update `cli.py` to accept `--output-file`:
```python
@click.command()
@click.argument('prompt', required=False)
@click.option('--style', type=click.Choice(['fd', 'bnr']), help='Brand style')
@click.option('--format', type=click.Choice(['png', 'svg']), help='Output format')
@click.option('--type', type=click.Choice(['bar', 'line']), help='Chart type')
@click.option('--output-file', type=str, help='Output filename')  # NEW
def main(prompt, style, format, type, output_file):
    # Pass output_file to graph state
```

### Step 2: Update GraphState
```python
class GraphState(TypedDict):
    messages: list[dict]
    interaction_mode: Literal["direct", "conversational"]
    intent: Literal["make_chart", "off_topic", "set_config", "error", "unknown"]
    has_file: bool
    config_change: dict | None
    input_data: str | None
    chart_request: dict | None
    missing_params: list[str]
    output_filename: str | None  # NEW
    final_filepath: str | None
```

### Step 3: Detect In-Query Filenames
Update `extract_data` or create helper to detect filename in user message:
```python
def extract_filename_from_query(message: str, llm) -> Optional[str]:
    """Use LLM to detect 'save as' patterns"""
    prompt = f"""
    Check if the user specified a filename in this message:
    "{message}"
    
    Look for patterns like:
    - "save as X"
    - "call it X"
    - "name it X"
    - "output file X"
    
    Return just the filename, or return "NONE" if no filename found.
    """
    
    result = llm.invoke(prompt)
    filename = result.strip()
    return None if filename == "NONE" else filename
```

### Step 4: Apply Priority Logic
In `extract_data` or a new node, set output_filename with priority:
```python
def apply_filename_priority(state: GraphState, cli_filename: Optional[str]) -> GraphState:
    """Apply priority: CLI flag > in-query > None"""
    
    if cli_filename:
        # Priority 1: CLI flag (already in state from CLI)
        state["output_filename"] = cli_filename
    else:
        # Priority 2: Check query for filename
        user_message = state["messages"][-1]["content"]
        query_filename = extract_filename_from_query(user_message, llm)
        state["output_filename"] = query_filename
    
    # Priority 3: None (fallback handled in tool)
    return state
```

### Step 5: Update matplotlib_chart_generator Tool
```python
from pathlib import Path
from datetime import datetime

def matplotlib_chart_generator(
    data: str,
    chart_type: str,
    style: str,
    format: str,
    output_filename: Optional[str] = None
) -> str:
    """Generate chart with smart filename handling"""
    
    if output_filename:
        path = Path(output_filename)
        
        # Handle extension
        expected_ext = f".{format}"
        if path.suffix:
            # User provided extension
            if path.suffix != expected_ext:
                # Extension mismatch: format takes priority
                path = path.with_suffix(expected_ext)
        else:
            # No extension: add correct one
            path = path.with_suffix(expected_ext)
        
        # Make absolute if relative
        if not path.is_absolute():
            path = Path.cwd() / path
        
        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Fallback: timestamp-based
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        path = Path.cwd() / f"chart-{timestamp}.{format}"
    
    # Generate chart
    fig, ax = create_chart(data, chart_type, style)
    fig.savefig(path, format=format)
    
    return str(path.absolute())
```

### Step 6: Pass Filename Through Pipeline
Update CLI handlers to pass output_filename into state:
```python
def run_direct_mode(prompt, style, format, type, output_file):
    initial_state = {
        "messages": [{"role": "user", "content": prompt}],
        "interaction_mode": "direct",
        "chart_request": {"type": type, "style": style, "format": format},
        "output_filename": output_file,  # NEW
        # ... other fields
    }
    result = graph.invoke(initial_state)
    # ...

def run_conversational_mode():
    session_state = {
        # ...
        "output_filename": None,  # Reset per request
    }
    # In the loop, filename extracted from query each turn
```

### Step 7: Extension Validation
Add helper function:
```python
def validate_and_fix_extension(filename: str, format: str) -> str:
    """Ensure filename has correct extension"""
    path = Path(filename)
    expected_ext = f".{format}"
    
    if path.suffix and path.suffix != expected_ext:
        # Mismatch: replace extension
        path = path.with_suffix(expected_ext)
    elif not path.suffix:
        # Missing: add extension
        path = path.with_suffix(expected_ext)
    
    return str(path)
```

### Testing Strategy

**Unit Tests:**
1. Test `extract_filename_from_query`:
   - "save as test.png" → "test.png"
   - "call it chart.svg" → "chart.svg"
   - "create a chart" → None

2. Test `validate_and_fix_extension`:
   - ("chart.png", "png") → "chart.png"
   - ("chart.png", "svg") → "chart.svg"
   - ("chart", "png") → "chart.png"

3. Test priority logic:
   - CLI flag present → use CLI flag
   - No CLI flag, query has filename → use query filename
   - Neither → None (fallback to timestamp)

**Integration Tests:**
1. Full flow with CLI flag:
   - Command with --output-file → verify custom name used

2. Full flow with in-query:
   - Conversational "save as X" → verify X used

3. Priority test:
   - Both CLI flag and in-query → verify CLI flag wins

**Acceptance Tests (Manual):**
1. Test CLI flag:
   ```bash
   graph-agent "chart: A=10, B=20" --style fd --type bar --output-file my_chart.png
   # Verify: my_chart.png created
   ```

2. Test in-query:
   ```bash
   graph-agent
   > Create bar chart: A=10, B=20. FD style. Save as quarterly.png
   # Verify: quarterly.png created
   ```

3. Test priority:
   ```bash
   graph-agent "chart: A=10. Save as ignored.png" --style fd --type bar --output-file wins.png
   # Verify: wins.png created (not ignored.png)
   ```

4. Test extension handling:
   ```bash
   graph-agent "chart: A=10" --style fd --type bar --format svg --output-file test.png
   # Verify: test.svg created (extension corrected)
   ```

5. Test subdirectory:
   ```bash
   graph-agent "chart: A=10" --style fd --type bar --output-file charts/output.png
   # Verify: charts/ directory created, charts/output.png exists
   ```

6. Test fallback:
   ```bash
   graph-agent "chart: A=10, B=20" --style fd --type bar
   # Verify: chart-20251106143500.png (timestamp format)
   ```
<!-- SECTION:PLAN:END -->
