---
id: task-7
title: 'Story 7: Ambiguity Resolution - Conversational Mode'
status: To Do
assignee: []
created_date: '2025-11-06 13:29'
updated_date: '2025-11-06 13:31'
labels:
  - phase-4
  - ambiguity
  - conversational
  - multi-turn
dependencies:
  - task-6
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
This story implements the ambiguity handling logic for conversational mode. When the agent lacks information needed to generate a chart (missing chart type or style), it asks the user clarifying questions.

This is a key UX feature: making the agent feel intelligent and helpful rather than failing with errors.

## User Story
**As a journalist**, when I provide incomplete information in conversational mode, I want the agent to ask me clarifying questions so I can provide the missing details without starting over.

## Ambiguity Scenarios

### Scenario 1: Missing Chart Type (Categorical Data)
```bash
> Create a chart with: Monday=10, Tuesday=15, Wednesday=12

I have your data. What type of chart would you like: bar or line?

> bar chart

Generating chart...
```

### Scenario 2: Missing Style (No Default Set)
```bash
> Create a bar chart with: A=10, B=20, C=30

Which brand style would you like: FD or BNR?

> FD

Generating chart...
```

### Scenario 3: Multiple Missing Parameters
```bash
> Chart with data: Mon=5, Tue=8, Wed=6

I have your data. What type of chart (bar/line) and which style (FD/BNR)?

> line chart, BNR style

Generating chart...
```

## Business Logic (from Requirements)

### Chart Type Resolution
1. If user explicitly requested "bar" or "line" → Use that
2. If data is time-series (dates, months, years) → Default to line chart
3. If data is categorical (days, names, labels) → **Ask user**

### Style Resolution (Priority Order)
1. Explicit in query → Use that
2. Default style set → Use default
3. Last used style → Use last used
4. **No default available → Ask user**

### Format Resolution (Priority Order)
1. Explicit in query → Use that
2. Default format set → Use default
3. Last used format → Use last used
4. **Fallback → PNG** (never ask about format)

## LangGraph Implementation

### New Node: `resolve_ambiguity`
This node runs **after** data is loaded but **before** chart generation:
```python
def resolve_ambiguity(state: GraphState) -> GraphState:
    """Check for missing parameters and determine next action"""
    missing = []
    
    if not state["chart_request"]["type"]:
        if is_categorical_data(state["input_data"]):
            missing.append("type")
    
    if not state["chart_request"]["style"]:
        missing.append("style")
    
    state["missing_params"] = missing
    return state
```

### New Node: `ask_clarification`
Generates a natural question for missing parameters:
```python
def ask_clarification(state: GraphState) -> GraphState:
    """Generate clarification question"""
    missing = state["missing_params"]
    
    if "type" in missing and "style" in missing:
        question = "I have your data. What type of chart (bar/line) and which style (FD/BNR)?"
    elif "type" in missing:
        question = "What type of chart would you like: bar or line?"
    elif "style" in missing:
        question = "Which brand style would you like: FD or BNR?"
    
    state["messages"].append({"role": "assistant", "content": question})
    return state
```

### Conditional Routing
```python
def route_after_resolve(state: GraphState) -> str:
    if state.get("missing_params"):
        if state["interaction_mode"] == "conversational":
            return "ask_clarification"  # Ask questions
        else:
            return "report_error"  # Fail in direct mode
    else:
        return "generate_chart"  # All params available
```

## Multi-Turn Handling
After asking a question, the user's response needs to be processed:
- The REPL adds the user's answer to messages
- The graph is invoked again
- `extract_data` or a new node extracts the answers
- Flow continues to `resolve_ambiguity` → should now have all params → `generate_chart`

## Example Flow
```
User: "chart: Mon=10, Tue=15"
↓
parse_intent (make_chart)
↓
extract_data (gets data, no type/style found)
↓
resolve_ambiguity (missing: type, style)
↓
ask_clarification ("What type and style?")
↓
[Return to REPL, wait for user]
↓
User: "bar chart, FD"
↓
parse_intent (make_chart)
↓
extract_data (extracts type=bar, style=fd)
↓
resolve_ambiguity (all params present!)
↓
generate_chart
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Agent asks for chart type when data is categorical and type not specified
- [ ] #2 Agent asks for style when no default is set and style not specified
- [ ] #3 Agent asks for both type and style in a single question when both are missing
- [ ] #4 Agent never asks about format (always defaults to PNG if not specified)
- [ ] #5 Multi-turn conversation works: user can answer questions and flow continues
- [ ] #6 Time-series data defaults to line chart without asking
- [ ] #7 Explicit parameters in the query are never questioned
- [ ] #8 After asking, user's response is correctly parsed and applied
- [ ] #9 Clarification questions are in English (per architecture)
- [ ] #10 Works only in conversational mode (direct mode will be handled in Story 8)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Create Data Analysis Helper
```python
def is_categorical_data(data_json: str) -> bool:
    """Determine if data is categorical (vs time-series)"""
    import json
    data = json.loads(data_json)
    
    # Check first few labels for time indicators
    time_keywords = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 
                      'sep', 'oct', 'nov', 'dec', 'q1', 'q2', 'q3', 'q4',
                      '2020', '2021', '2022', '2023', '2024', '2025']
    
    for item in data[:3]:  # Check first 3 labels
        label = item['label'].lower()
        if any(keyword in label for keyword in time_keywords):
            return False  # Time-series
    
    return True  # Categorical
```

### Step 2: Create `resolve_ambiguity` Node
```python
def resolve_ambiguity(state: GraphState) -> GraphState:
    """Check for missing params after applying priority logic"""
    from .config import load_user_preferences
    
    prefs = load_user_preferences()
    chart_req = state["chart_request"]
    missing = []
    
    # Check chart type
    if not chart_req.get("type"):
        # If data is categorical, we need to ask
        if is_categorical_data(state["input_data"]):
            missing.append("type")
        else:
            # Time-series: default to line
            chart_req["type"] = "line"
    
    # Check style (apply priority logic from Story 6)
    if not chart_req.get("style"):
        chart_req["style"] = (
            prefs.get("default_style") or
            prefs.get("last_used_style") or
            None
        )
        if not chart_req["style"]:
            missing.append("style")
    
    # Format always has fallback, never missing
    if not chart_req.get("format"):
        chart_req["format"] = (
            prefs.get("default_format") or
            prefs.get("last_used_format") or
            "png"
        )
    
    state["chart_request"] = chart_req
    state["missing_params"] = missing
    return state
```

### Step 3: Create `ask_clarification` Node
```python
def ask_clarification(state: GraphState) -> GraphState:
    """Generate English clarification question"""
    missing = state.get("missing_params", [])
    
    if not missing:
        return state
    
    if "type" in missing and "style" in missing:
        question = "I have your data. What type of chart (bar/line) and which style (FD/BNR)?"
    elif "type" in missing:
        question = "What type of chart would you like: bar or line?"
    elif "style" in missing:
        question = "Which brand style would you like: FD or BNR?"
    else:
        question = "I need more information to create your chart."
    
    state["messages"].append({
        "role": "assistant",
        "content": question
    })
    
    return state
```

### Step 4: Update Graph Flow
```python
def route_after_data_extraction(state: GraphState) -> str:
    """Route to ambiguity resolution after data is extracted"""
    return "resolve_ambiguity"

def route_after_resolve(state: GraphState) -> str:
    """Route based on missing params and mode"""
    missing = state.get("missing_params", [])
    
    if missing:
        if state["interaction_mode"] == "conversational":
            return "ask_clarification"
        else:
            return "report_error"  # Story 8
    else:
        return "generate_chart"

# Update workflow
workflow.add_node("resolve_ambiguity", resolve_ambiguity)
workflow.add_node("ask_clarification", ask_clarification)

# Reroute: extract_data → resolve_ambiguity
workflow.add_edge("extract_data", "resolve_ambiguity")
workflow.add_edge("call_data_tool", "resolve_ambiguity")

# Add conditional from resolve_ambiguity
workflow.add_conditional_edges("resolve_ambiguity", route_after_resolve)

# ask_clarification finishes (returns to REPL for user response)
workflow.set_finish_point("ask_clarification")
```

### Step 5: Handle Multi-Turn Flow
The key insight: When the agent asks a question and returns to REPL:
1. User answers
2. REPL invokes graph again with the answer
3. `parse_intent` still detects "make_chart"
4. `extract_data` now extracts the missing params from the answer
5. `resolve_ambiguity` checks again → all params present → generate

No special handling needed! The existing nodes just work.

### Step 6: Update GraphState
```python
class GraphState(TypedDict):
    messages: list[dict]
    interaction_mode: Literal["direct", "conversational"]
    intent: Literal["make_chart", "off_topic", "set_config", "error", "unknown"]
    has_file: bool
    config_change: dict | None
    input_data: str | None
    chart_request: dict | None
    missing_params: list[str]  # NEW: ["type", "style"]
    final_filepath: str | None
```

### Testing Strategy

**Unit Tests:**
1. Test `is_categorical_data`:
   - Time-series labels → False
   - Categorical labels → True

2. Test `resolve_ambiguity`:
   - Mock config with no defaults
   - Test categorical data, no type → missing=["type", "style"]
   - Test time-series data, no type → type defaults to "line", missing=["style"]

3. Test `ask_clarification`:
   - missing=["type", "style"] → combined question
   - missing=["type"] → type question only
   - missing=["style"] → style question only

**Integration Tests:**
1. Full multi-turn flow:
   - Initial: "chart: Mon=10, Tue=15" (no type/style)
   - Agent asks
   - Response: "bar, FD"
   - Verify chart generated

**Acceptance Tests (Manual):**
1. Start conversational mode with no defaults set
2. Request: "chart: A=10, B=20"
   - Verify agent asks for type and style
3. Answer: "bar chart, FD style"
   - Verify chart generated with FD bar chart
4. Request: "chart: Jan 2024=100, Feb 2024=120"
   - Verify agent only asks for style (time-series → line default)
5. Answer: "BNR"
   - Verify BNR line chart generated
<!-- SECTION:PLAN:END -->
