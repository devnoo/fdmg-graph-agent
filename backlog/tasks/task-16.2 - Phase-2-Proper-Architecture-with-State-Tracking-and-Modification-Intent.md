---
id: task-16.2
title: 'Phase 2: Proper Architecture with State Tracking and Modification Intent'
status: To Do
assignee: []
created_date: '2025-11-11 09:41'
labels:
  - phase-2
  - architecture
  - state-management
dependencies:
  - task-16.1
parent_task_id: task-16
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement proper architectural support for chart modifications with a dedicated `modify_chart` intent, state tracking for last chart parameters, and a new modification node that intelligently merges parameters.

## Goal
Enable true chart modification where users can say "add Q3=150" and the system adds to existing data, or "change style" without repeating all data points.

## Changes Required

### 1. Update `GraphState` in `graph_agent/state.py`

Add new field to track last chart:

```python
class GraphState(TypedDict):
    messages: list[dict[str, str]]
    interaction_mode: str
    intent: str | None
    has_file: bool
    config_change: dict[str, str] | None
    input_data: str | None
    chart_request: dict[str, str | None] | None
    missing_params: list[str] | None
    output_filename: str | None
    final_filepath: str | None
    error_message: str | None
    last_chart_params: dict[str, Any] | None  # NEW: Stores last chart details
```

Structure of `last_chart_params`:
```python
{
    "data": '[{"label": "Q1", "value": 100}, ...]',  # JSON string
    "type": "bar",
    "style": "fd", 
    "format": "png",
    "filepath": "/path/to/chart-123.png"
}
```

### 2. Update `parse_intent()` in `graph_agent/agent.py`

Add detection for new `modify_chart` intent:

```python
system_prompt = """Analyze conversation history to determine intent.

CONVERSATION CONTEXT:
{conversation_history}

Return JSON:
{{
  "intent": "make_chart" or "modify_chart" or "set_config" or "off_topic",
  "modification_type": "style" or "type" or "data" or "format" or null,
  "has_file": true or false,
  ...
}}

Intent should be "modify_chart" if:
- A chart was recently created (look for "Chart saved:" in conversation)
- User wants to MODIFY existing chart:
  * "change the style to BNR" → modification_type: "style"
  * "make it a bar chart" → modification_type: "type"  
  * "add Q3=150" → modification_type: "data"
  * "export as SVG" → modification_type: "format"
- User refers to existing chart: "the chart", "it", "this one"

Intent should be "make_chart" if:
- Creating a NEW chart from scratch
- No reference to previous chart
- Fresh data without "add" or "change" keywords

...
"""
```

### 3. Create `modify_existing_chart()` Node

New node that merges old and new parameters:

```python
def modify_existing_chart(state: GraphState) -> GraphState:
    """
    Modify the last created chart based on user's modification request.
    
    This node:
    1. Retrieves last_chart_params from state
    2. Extracts modification from current user message
    3. Merges old + new parameters intelligently
    4. Routes to generate_chart with merged parameters
    
    Args:
        state: Current graph state with last_chart_params populated
        
    Returns:
        Updated state with merged chart_request and input_data
    """
    last_chart = state.get("last_chart_params")
    
    if not last_chart:
        # No previous chart - treat as new chart request
        logger.warning("modify_existing_chart: No last_chart_params, treating as new chart")
        # Redirect to extract_data
        return extract_data(state)
    
    llm = get_llm()
    user_message = state["messages"][-1]["content"]
    
    # Extract modification details
    modification_prompt = """Extract what the user wants to modify.

Previous chart:
- Data: {data}
- Type: {type}
- Style: {style}
- Format: {format}

User's modification request: {request}

Return JSON:
{{
  "new_type": "bar" or "line" or null (null = keep existing),
  "new_style": "fd" or "bnr" or null,
  "new_format": "png" or "svg" or null,
  "data_operation": "replace" or "add" or "remove" or null,
  "new_data": [{{"label": "X", "value": Y}}, ...] or null
}}

Examples:
- "change style to BNR" → new_style: "bnr", others null
- "add Q3=150" → data_operation: "add", new_data: [{{"label": "Q3", "value": 150}}]
- "make it a bar chart" → new_type: "bar", others null
- "export as SVG" → new_format: "svg", others null
"""
    
    prompt = modification_prompt.format(
        data=last_chart["data"],
        type=last_chart["type"],
        style=last_chart["style"],
        format=last_chart["format"],
        request=user_message
    )
    
    response = llm.invoke(prompt)
    # Parse JSON response...
    modifications = json.loads(clean_response(response.content))
    
    # Merge parameters
    merged_chart_request = {
        "type": modifications.get("new_type") or last_chart["type"],
        "style": modifications.get("new_style") or last_chart["style"],
        "format": modifications.get("new_format") or last_chart["format"]
    }
    
    # Merge data
    if modifications.get("data_operation") == "add":
        old_data = json.loads(last_chart["data"])
        new_data_points = modifications.get("new_data", [])
        merged_data = old_data + new_data_points
        merged_input_data = json.dumps(merged_data)
    elif modifications.get("data_operation") == "replace":
        merged_input_data = json.dumps(modifications.get("new_data", []))
    else:
        # Keep existing data
        merged_input_data = last_chart["data"]
    
    logger.info(f"modify_existing_chart: Merged chart_request={merged_chart_request}")
    
    return GraphState(
        messages=state["messages"],
        interaction_mode=state["interaction_mode"],
        intent="make_chart",  # Convert to make_chart for rest of workflow
        has_file=False,
        config_change=None,
        input_data=merged_input_data,
        chart_request=merged_chart_request,
        missing_params=None,
        output_filename=state.get("output_filename"),
        final_filepath=state.get("final_filepath"),
        error_message=None,
        last_chart_params=state.get("last_chart_params")
    )
```

### 4. Update `generate_chart_tool()` to Store Last Chart

After generating chart, store parameters in state:

```python
def generate_chart_tool(state: GraphState) -> GraphState:
    """Generate chart and store parameters for future modifications."""
    # ... existing chart generation code ...
    
    # Store chart parameters for future modifications
    last_chart_params = {
        "data": input_data,
        "type": chart_request["type"],
        "style": chart_request["style"],
        "format": chart_request["format"],
        "filepath": filepath
    }
    
    return GraphState(
        messages=updated_messages,
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        has_file=state.get("has_file", False),
        config_change=state.get("config_change"),
        input_data=state["input_data"],
        chart_request=state["chart_request"],
        missing_params=state.get("missing_params"),
        output_filename=state.get("output_filename"),
        final_filepath=filepath,
        error_message=state.get("error_message"),
        last_chart_params=last_chart_params  # NEW
    )
```

### 5. Update `route_after_intent()` Routing

Add routing for `modify_chart` intent:

```python
def route_after_intent(state: GraphState) -> str:
    """Route based on intent."""
    intent = state["intent"]
    has_file = state.get("has_file", False)
    
    if intent == "off_topic":
        return "report_error"
    elif intent == "set_config":
        return "handle_config"
    elif intent == "modify_chart":  # NEW
        return "modify_existing_chart"
    elif intent == "make_chart":
        if has_file:
            return "call_data_tool"
        else:
            return "extract_data"
    else:
        return "report_error"
```

### 6. Update `create_graph()` Workflow

Add new node and routing:

```python
def create_graph() -> Any:
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("parse_intent", parse_intent)
    workflow.add_node("modify_existing_chart", modify_existing_chart)  # NEW
    # ... other nodes ...
    
    # Routing after parse_intent
    workflow.add_conditional_edges(
        "parse_intent",
        route_after_intent,
        {
            "report_error": "report_error",
            "handle_config": "handle_config",
            "modify_existing_chart": "modify_existing_chart",  # NEW
            "call_data_tool": "call_data_tool",
            "extract_data": "extract_data",
        },
    )
    
    # Route modify_existing_chart directly to resolve_ambiguity
    workflow.add_edge("modify_existing_chart", "resolve_ambiguity")
    
    # ... rest of workflow ...
```

### 7. Testing

Add comprehensive tests for modification scenarios:

```python
def test_modify_chart_change_style():
    """Test modifying chart style keeps data and type."""
    
def test_modify_chart_add_data():
    """Test adding data points to existing chart."""
    
def test_modify_chart_change_type():
    """Test changing bar to line keeps data and style."""
    
def test_modify_chart_no_previous():
    """Test modification request with no previous chart falls back gracefully."""
    
def test_modify_chart_multiple_changes():
    """Test changing multiple parameters at once."""
```

## Estimated Effort
- Implementation: 4-5 hours
- Testing: 2-3 hours
- **Total: 6-8 hours**
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 GraphState includes last_chart_params field
- [ ] #2 parse_intent() detects 'modify_chart' intent correctly
- [ ] #3 New node modify_existing_chart() created and integrated
- [ ] #4 User can say 'add Q3=150' and system adds to existing data
- [ ] #5 User can say 'change style to BNR' without repeating data
- [ ] #6 User can say 'make it a bar chart' and only type changes
- [ ] #7 generate_chart_tool() stores last chart parameters
- [ ] #8 route_after_intent() handles modify_chart routing
- [ ] #9 Tests cover all modification scenarios (style, type, data, format)
- [ ] #10 Graceful fallback if no previous chart exists
<!-- AC:END -->
