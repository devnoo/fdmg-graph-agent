---
id: task-16.3
title: 'Phase 3: Advanced Modification Features'
status: To Do
assignee: []
created_date: '2025-11-11 09:41'
labels:
  - phase-3
  - advanced-features
  - future
dependencies:
  - task-16.2
parent_task_id: task-16
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement advanced features for chart modification including multi-parameter changes, undo/redo support, and side-by-side comparison mode.

## Goal
Provide power users with advanced capabilities for iterative chart refinement and exploration.

## Features to Implement

### 1. Multi-Parameter Modifications

Enable users to change multiple parameters in one request:

**Examples:**
- "Change to bar chart AND use BNR style"
- "Make it SVG format with FD colors"
- "Switch to line graph, BNR style, export as PNG"

**Implementation:**
- Enhance `modify_existing_chart()` to handle multiple changes simultaneously
- Update LLM prompt to extract all modifications in single pass
- Validate that all combinations are valid (no conflicting requests)

**Test cases:**
```python
def test_modify_multiple_params_type_and_style():
    """User: 'change to bar chart with BNR style'"""
    
def test_modify_multiple_params_all_three():
    """User: 'make it a line graph, FD style, as SVG'"""
```

### 2. Undo/Redo Support

Allow users to revert to previous chart versions:

**Examples:**
- "Undo that change"
- "Go back to the previous version"
- "Redo"
- "Show me the version before last"

**Implementation:**

Add chart history to state:
```python
class GraphState(TypedDict):
    # ... existing fields ...
    last_chart_params: dict[str, Any] | None
    chart_history: list[dict[str, Any]] | None  # NEW: Stack of previous charts
```

New node `handle_undo_redo()`:
```python
def handle_undo_redo(state: GraphState) -> GraphState:
    """
    Handle undo/redo operations on chart history.
    
    Maintains a stack of chart_history with max depth (e.g., 5 charts).
    """
    history = state.get("chart_history", [])
    
    if not history:
        # No history to undo
        message = "Geen eerdere versie beschikbaar om terug te gaan."
        # Return state with error message
        
    # Pop last chart from history
    previous_chart = history[-1]
    
    # Regenerate that chart
    # ... restore parameters and call generate_chart ...
```

New intent: `undo_chart` / `redo_chart`

**Limitations:**
- History limited to last 5 charts (memory management)
- Undo/redo only in conversational mode
- Clears on exit from REPL

### 3. Side-by-Side Comparison Mode

Generate multiple chart variations simultaneously:

**Examples:**
- "Show me both FD and BNR versions"
- "Create both bar and line charts"
- "Generate this in PNG and SVG"

**Implementation:**

New intent: `compare_charts`

```python
def generate_comparison_charts(state: GraphState) -> GraphState:
    """
    Generate multiple chart variations based on user request.
    
    Examples:
    - "both FD and BNR" → 2 charts (same data, different styles)
    - "bar and line" → 2 charts (same data, different types)
    - "all formats" → 2 charts (PNG and SVG)
    """
    llm = get_llm()
    user_message = state["messages"][-1]["content"]
    
    # Extract comparison dimensions
    comparison_prompt = """User wants to compare multiple chart variations.

User request: {request}

What should be varied?
{{
  "vary_style": true/false (FD vs BNR),
  "vary_type": true/false (bar vs line),
  "vary_format": true/false (PNG vs SVG)
}}
"""
    
    # Generate all combinations
    # For vary_style=true, vary_type=false, vary_format=false:
    #   → 2 charts (FD bar, BNR bar)
    # For vary_style=true, vary_type=true:
    #   → 4 charts (FD bar, FD line, BNR bar, BNR line)
    
    filepaths = []
    for combination in combinations:
        filepath = matplotlib_chart_generator(
            data=input_data,
            chart_type=combination["type"],
            style=combination["style"],
            format=combination["format"]
        )
        filepaths.append(filepath)
    
    # Return success message with all file paths
    message = f"Gegenereerd {len(filepaths)} vergelijkingsgrafieken:\n"
    for fp in filepaths:
        message += f"  - {fp}\n"
    
    # ... return state ...
```

**UI Considerations:**
- Display all generated file paths clearly
- Consider filename patterns: `chart-comparison-fd-bar-123.png`, `chart-comparison-bnr-bar-123.png`

### 4. Smart Chart Suggestions

Proactively suggest improvements based on data characteristics:

**Examples:**
- Time-series data → "Dit lijkt tijdreeksdata. Wil je een lijngrafiek in plaats van staafdiagram?"
- Single data point → "Je hebt maar één datapunt. Een grafiek is misschien niet zinvol."
- Many data points (>15) → "Je hebt veel datapunten. Overweeg een lijngrafiek voor betere leesbaarheid."

**Implementation:**

New node: `suggest_improvements()`
- Runs after `extract_data` or `modify_existing_chart`
- Analyzes data characteristics
- Generates optional suggestions
- Adds suggestion to messages (non-blocking)

### 5. Named Chart Sessions

Allow users to name and recall chart configurations:

**Examples:**
- "Save this as 'quarterly_revenue'"
- "Load quarterly_revenue"
- "List my saved charts"

**Implementation:**
- Store named configurations in `~/.graph-agent/saved_charts.json`
- New intents: `save_chart_config`, `load_chart_config`, `list_saved_charts`
- Integrate with existing config system

## Priority Order

1. **High Priority:** Multi-parameter modifications (extends Phase 2 naturally)
2. **Medium Priority:** Comparison mode (useful for journalists evaluating options)
3. **Low Priority:** Undo/redo (nice-to-have, adds complexity)
4. **Future:** Smart suggestions, named sessions (requires more design)

## Estimated Effort
- Multi-parameter: 2-3 hours
- Comparison mode: 3-4 hours
- Undo/redo: 4-5 hours
- Smart suggestions: 2-3 hours
- Named sessions: 3-4 hours
- **Total: 14-19 hours** (can be implemented incrementally)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Multi-parameter modifications work ('change to bar AND BNR style')
- [ ] #2 Comparison mode generates multiple chart variations ('show both FD and BNR')
- [ ] #3 Undo/redo functionality implemented with history stack
- [ ] #4 Smart suggestions provided based on data characteristics
- [ ] #5 Named chart sessions can be saved and loaded
- [ ] #6 All advanced features work only in conversational mode
- [ ] #7 Performance remains acceptable with added features
- [ ] #8 Tests cover all advanced scenarios
<!-- AC:END -->
