---
id: task-8
title: 'Story 8: Ambiguity Handling - Direct Mode'
status: Done
assignee: []
created_date: '2025-11-06 13:31'
updated_date: '2025-11-06 22:27'
labels:
  - phase-4
  - ambiguity
  - direct-mode
  - error-handling
dependencies:
  - task-7
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
This story implements error handling for ambiguous requests in direct mode. Unlike conversational mode (Story 7) where the agent asks questions, direct mode must fail fast with clear error messages.

Direct mode is stateless and non-interactive, so users need informative errors to fix their command.

## User Story
**As a journalist**, when I use direct mode with incomplete information, I want clear error messages that tell me exactly what's missing, so I can fix my command and try again.

## Behavior

### Direct Mode Cannot Ask Questions
Direct mode is:
- Single-shot: runs once and exits
- Non-interactive: no way to get user input after starting
- Used in scripts: errors should be machine-readable

When parameters are missing, the agent must:
1. **Fail immediately** (don't generate a chart)
2. **Print a clear, actionable error message**
3. **Exit with non-zero status code**

## Error Messages

### Missing Chart Type
```bash
$ graph-agent "chart: Mon=10, Tue=15" --style fd
Error: Chart type is ambiguous. Please specify using --type bar or --type line
```

### Missing Style
```bash
$ graph-agent "chart: A=10, B=20" --type bar
Error: Brand style not specified. Please use --style fd or --style bnr, or set a default style.
```

### Multiple Missing
```bash
$ graph-agent "chart: Mon=10, Tue=15"
Error: Missing required parameters:
  - Chart type: use --type bar or --type line
  - Brand style: use --style fd or --style bnr
```

## Implementation

### New Node: `report_error`
Already exists from Story 2 (off-topic rejection). Extend for ambiguity:
```python
def report_error(state: GraphState) -> GraphState:
    """Generate error message for direct mode"""
    missing = state.get("missing_params", [])
    
    if not missing:
        # Existing off-topic logic
        message = "I can only help you create charts. Please ask me to make a bar or line chart."
    elif len(missing) == 1:
        if missing[0] == "type":
            message = "Error: Chart type is ambiguous. Please specify using --type bar or --type line"
        elif missing[0] == "style":
            message = "Error: Brand style not specified. Please use --style fd or --style bnr, or set a default style."
    else:
        # Multiple missing
        message = "Error: Missing required parameters:\\n"
        if "type" in missing:
            message += "  - Chart type: use --type bar or --type line\\n"
        if "style" in missing:
            message += "  - Brand style: use --style fd or --style bnr"
    
    state["messages"].append({
        "role": "assistant",
        "content": message
    })
    
    return state
```

### Routing Logic (from Story 7)
The `route_after_resolve` function already handles this:
```python
def route_after_resolve(state: GraphState) -> str:
    missing = state.get("missing_params", [])
    
    if missing:
        if state["interaction_mode"] == "conversational":
            return "ask_clarification"  # Story 7
        else:
            return "report_error"  # Story 8
    else:
        return "generate_chart"
```

### Exit Code
Update CLI to exit with error code when ambiguity errors occur:
```python
def run_direct_mode(prompt, style, format, type):
    result = graph.invoke(initial_state)
    final_message = result["messages"][-1]["content"]
    
    if final_message.startswith("Error:"):
        print(final_message, file=sys.stderr)
        sys.exit(1)  # Non-zero exit code
    else:
        print(final_message)
        sys.exit(0)
```

## Example Interactions

### Happy Path (All Params Provided)
```bash
$ graph-agent "chart: A=10, B=20" --style fd --type bar --format png
Chart saved: /home/user/chart-20251106143000.png
$ echo $?
0
```

### Error Path (Missing Type)
```bash
$ graph-agent "chart: Mon=10, Tue=15" --style fd
Error: Chart type is ambiguous. Please specify using --type bar or --type line
$ echo $?
1
```

### Using Defaults (No Error)
```bash
# After setting defaults in Story 6
$ graph-agent "chart: A=10, B=20" --type bar
# Uses default style, default format
Chart saved: /home/user/chart-20251106143030.png
$ echo $?
0
```

## Testing Edge Cases

1. **Time-series auto-detection**: "chart: Jan 2024=100" → line chart automatically, no error
2. **Default style set**: No style needed if user has default
3. **Format always has fallback**: Never an error for missing format
4. **Off-topic**: Still handled by existing reject logic
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Direct mode fails with error when chart type is missing (categorical data)
- [x] #2 Direct mode fails with error when style is missing and no default set
- [x] #3 Error messages clearly state what's missing and how to fix it
- [x] #4 Multiple missing params are listed in a single error message
- [x] #5 Exit code is 1 when command fails due to ambiguity
- [x] #6 Exit code is 0 when command succeeds
- [x] #7 Time-series data defaults to line chart without error in direct mode
- [x] #8 When defaults are set, direct mode uses them without error
- [x] #9 Format never causes ambiguity error (always defaults to PNG)
- [x] #10 Error output goes to stderr, not stdout
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Extend `report_error` Node
Update the existing node from Story 2 to handle ambiguity errors:
```python
def report_error(state: GraphState) -> GraphState:
    """Generate error message based on error type"""
    intent = state.get("intent")
    missing = state.get("missing_params", [])
    
    # Off-topic (existing from Story 2)
    if intent == "off_topic":
        message = "I can only help you create charts. Please ask me to make a bar or line chart."
    
    # Ambiguity errors (new for Story 8)
    elif missing:
        if len(missing) == 1:
            if missing[0] == "type":
                message = "Error: Chart type is ambiguous. Please specify using --type bar or --type line"
            elif missing[0] == "style":
                message = "Error: Brand style not specified. Please use --style fd or --style bnr, or set a default style."
        else:
            # Multiple missing parameters
            message = "Error: Missing required parameters:\n"
            if "type" in missing:
                message += "  - Chart type: use --type bar or --type line\n"
            if "style" in missing:
                message += "  - Brand style: use --style fd or --style bnr"
    else:
        message = "Error: Unable to process request."
    
    state["messages"].append({
        "role": "assistant",
        "content": message
    })
    
    return state
```

### Step 2: Update Direct Mode CLI Handler
Modify `run_direct_mode` to handle errors properly:
```python
import sys

def run_direct_mode(prompt, style, format, type):
    initial_state = {
        "messages": [{"role": "user", "content": prompt}],
        "interaction_mode": "direct",
        "chart_request": {"type": type, "style": style, "format": format},
        # ... other fields
    }
    
    result = graph.invoke(initial_state)
    final_message = result["messages"][-1]["content"]
    
    # Check if this is an error
    if final_message.startswith("Error:") or final_message.startswith("I can only"):
        # Print to stderr
        print(final_message, file=sys.stderr)
        sys.exit(1)  # Non-zero exit code for errors
    else:
        # Success: print to stdout
        print(final_message)
        sys.exit(0)
```

### Step 3: Verify Routing Logic Works
The routing from Story 7 already handles this correctly:
```python
def route_after_resolve(state: GraphState) -> str:
    missing = state.get("missing_params", [])
    
    if missing:
        if state["interaction_mode"] == "conversational":
            return "ask_clarification"
        else:
            return "report_error"  # ← Routes here for direct mode
    else:
        return "generate_chart"
```

No changes needed! The logic from Story 7 already routes direct mode to `report_error`.

### Step 4: Test Exit Codes
Ensure shell integration works:
```bash
# Test success
graph-agent "chart: A=10" --type bar --style fd && echo "SUCCESS"

# Test failure
graph-agent "chart: A=10" || echo "FAILED"
```

### Testing Strategy

**Unit Tests:**
1. Test `report_error` with different missing params:
   - missing=["type"] → type error message
   - missing=["style"] → style error message
   - missing=["type", "style"] → combined error message

2. Test exit code logic:
   - Error message → exit(1)
   - Success message → exit(0)

**Integration Tests:**
1. Test full error flow:
   - Direct mode with missing type
   - Verify routes through: parse_intent → extract_data → resolve_ambiguity → report_error
   - Verify state.missing_params is set correctly

**Acceptance Tests (Manual):**
1. Test missing type:
   ```bash
   graph-agent "chart: Mon=10, Tue=15" --style fd
   # Should print error to stderr and exit 1
   ```

2. Test missing style (no defaults):
   ```bash
   graph-agent "chart: A=10, B=20" --type bar
   # Should print error to stderr and exit 1
   ```

3. Test both missing:
   ```bash
   graph-agent "chart: Mon=10, Tue=15"
   # Should print multi-line error and exit 1
   ```

4. Test success:
   ```bash
   graph-agent "chart: A=10, B=20" --style fd --type bar
   # Should print success to stdout and exit 0
   ```

5. Test with defaults set:
   ```bash
   # First set defaults
   graph-agent
   > Set default style to FD
   > exit
   
   # Then test without --style
   graph-agent "chart: A=10, B=20" --type bar
   # Should succeed using default FD style
   ```
<!-- SECTION:PLAN:END -->
