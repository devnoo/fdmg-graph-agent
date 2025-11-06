---
id: task-3
title: 'Story 3: Direct Mode - Text to Chart (Full Happy Path)'
status: To Do
assignee: []
created_date: '2025-11-06 13:24'
updated_date: '2025-11-06 13:25'
labels:
  - phase-2
  - chart-generation
  - matplotlib
  - data-extraction
dependencies:
  - task-2
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
This story implements the complete end-to-end chart generation flow in direct mode. This is the "happy path" where all parameters are explicitly provided, eliminating any ambiguity.

After this story, users can generate actual charts from text data!

## User Story
**As a journalist**, I want to run a single command with all parameters specified, and receive a chart file back immediately, so I can quickly add visualizations to my articles.

## Technical Requirements

### Input Format
The CLI accepts these parameters:
```bash
graph-agent "create a bar chart with: A=10, B=20, C=30" \
  --style fd \
  --format png \
  --type bar
```

**CLI Options:**
- `--style`: Brand style (`fd` or `bnr`)
- `--format`: Output format (`png` or `svg`)
- `--type`: Chart type (`bar` or `line`)
- Main argument: Natural language prompt containing the data

### Data Extraction
The LLM (Gemini) must extract structured data from the natural language prompt. Examples:
- "A=10, B=20, C=30" → `[("A", 10), ("B", 20), ("C", 30)]`
- "Monday: 4.1, Tuesday: 4.2, Wednesday: 4.0" → `[("Monday", 4.1), ("Tuesday", 4.2), ("Wednesday", 4.0)]`

### Chart Generation
Using **matplotlib**, generate charts with exact brand styling:

**FD Style:**
- Primary color (bars/lines): `#379596`
- Text color: `#191919`
- Background: `#ffeadb`

**BNR Style:**
- Primary color (bars/lines): `#ffd200`
- Text color: `#000`
- Background: `#fff`

**Chart Requirements:**
- Clean, publication-ready design
- No title (journalists add titles in their articles)
- Labeled axes
- Grid lines (subtle)
- Proper spacing and padding

### File Output
- Default filename: `chart-[timestamp].png` (e.g., `chart-20251106131500.png`)
- Timestamp format: `YYYYMMDDHHmmss`
- Save to current working directory
- Return absolute file path to user

## LangGraph Flow Extension
Extend the state machine from Story 2:

**New State Fields:**
```python
class GraphState(TypedDict):
    # ... existing fields ...
    input_data: str | None  # JSON string of extracted data
    chart_request: dict | None  # {"type": "bar", "style": "fd", "format": "png"}
    final_filepath: str | None  # Absolute path to generated chart
```

**New Nodes:**
1. **`extract_data`**: LLM extracts data from prompt, saves to `input_data` as JSON
2. **`generate_chart_tool`**: Calls matplotlib tool to create chart, saves path to `final_filepath`

**Updated Flow:**
```
parse_intent → (if make_chart) → extract_data → generate_chart_tool → END
             → (if off_topic) → reject_task → END
```

## Example Interaction
```bash
$ graph-agent "create a bar chart with quarterly revenue: Q1=120, Q2=150, Q3=140, Q4=180" --style fd --format png --type bar

Generating chart...
Chart saved: /home/user/projects/chart-20251106131500.png
```

## Brand Color Reference
```json
{
  "fd": {
    "primary": "#379596",
    "content": "#191919",
    "background": "#ffeadb"
  },
  "bnr": {
    "primary": "#ffd200",
    "content": "#000",
    "background": "#fff"
  }
}
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Running the command with all explicit parameters generates a chart file without errors
- [ ] #2 The generated chart uses the correct brand colors (FD or BNR)
- [ ] #3 The chart type matches the --type flag (bar or line)
- [ ] #4 The output format matches the --format flag (png or svg)
- [ ] #5 The chart file is saved to the current directory with format 'chart-[timestamp].[ext]'
- [ ] #6 The CLI prints the absolute path to the generated chart
- [ ] #7 Data is correctly extracted from natural language (tested with at least 3 different formats)
- [ ] #8 Charts are publication-ready: no title, labeled axes, clean styling
- [ ] #9 The command works in direct mode and exits after completion
- [ ] #10 Gemini successfully extracts data from various text formats (comma-separated, colon-separated, etc.)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Update CLI to Accept New Flags (`cli.py`)
Add click options for style, format, and type:
```python
@click.command()
@click.argument('prompt', required=False)
@click.option('--style', type=click.Choice(['fd', 'bnr']), help='Brand style')
@click.option('--format', type=click.Choice(['png', 'svg']), help='Output format')
@click.option('--type', type=click.Choice(['bar', 'line']), help='Chart type')
def main(prompt, style, format, type):
    # Pass these to the graph state
```

### Step 2: Extend GraphState (`state.py`)
Add new fields:
```python
class GraphState(TypedDict):
    messages: list[dict]
    interaction_mode: Literal["direct", "conversational"]
    intent: Literal["make_chart", "off_topic", "unknown"]
    # New fields:
    input_data: str | None  # JSON: [{"label": "A", "value": 10}, ...]
    chart_request: dict | None  # {"type": "bar", "style": "fd", "format": "png"}
    final_filepath: str | None
```

### Step 3: Create Data Extraction Node (`agent.py`)
Implement `extract_data` node:
```python
def extract_data(state: GraphState) -> GraphState:
    """Extract structured data from user's natural language prompt"""
    # Get user message from state.messages
    # Call Gemini with prompt:
    # "Extract label-value pairs from this text. Return as JSON array: 
    #  [{"label": "...", "value": ...}, ...]"
    # Parse LLM response into JSON string
    # Save to state.input_data
    return state
```

### Step 4: Create Chart Tool (`tools.py`)
Create new file with matplotlib chart generator:
```python
def matplotlib_chart_generator(
    data: str,  # JSON string
    chart_type: str,  # "bar" or "line"
    style: str,  # "fd" or "bnr"
    format: str,  # "png" or "svg"
) -> str:
    """Generate chart and return absolute filepath"""
    # Parse JSON data
    # Set up matplotlib with brand colors
    # Create figure with correct styling
    # Generate filename: chart-{timestamp}.{format}
    # Save file
    # Return absolute path
```

**Brand styling code:**
```python
BRAND_COLORS = {
    "fd": {"primary": "#379596", "content": "#191919", "background": "#ffeadb"},
    "bnr": {"primary": "#ffd200", "content": "#000", "background": "#fff"}
}

def apply_brand_style(fig, ax, style):
    colors = BRAND_COLORS[style]
    fig.patch.set_facecolor(colors["background"])
    ax.set_facecolor(colors["background"])
    ax.tick_params(colors=colors["content"])
    ax.spines['bottom'].set_color(colors["content"])
    ax.spines['left'].set_color(colors["content"])
    # ... more styling
```

### Step 5: Create Chart Generation Node (`agent.py`)
```python
def generate_chart_tool(state: GraphState) -> GraphState:
    """Call matplotlib tool to generate chart"""
    from .tools import matplotlib_chart_generator
    
    filepath = matplotlib_chart_generator(
        data=state["input_data"],
        chart_type=state["chart_request"]["type"],
        style=state["chart_request"]["style"],
        format=state["chart_request"]["format"]
    )
    
    state["final_filepath"] = filepath
    state["messages"].append({
        "role": "assistant",
        "content": f"Chart saved: {filepath}"
    })
    return state
```

### Step 6: Update Graph Flow (`agent.py`)
Add conditional routing:
```python
def route_after_intent(state: GraphState) -> str:
    if state["intent"] == "off_topic":
        return "reject_task"
    else:
        return "extract_data"

workflow = StateGraph(GraphState)
workflow.add_node("parse_intent", parse_intent)
workflow.add_node("reject_task", reject_task)
workflow.add_node("extract_data", extract_data)  # NEW
workflow.add_node("generate_chart", generate_chart_tool)  # NEW

workflow.set_entry_point("parse_intent")
workflow.add_conditional_edges("parse_intent", route_after_intent)
workflow.add_edge("extract_data", "generate_chart")
workflow.set_finish_point("reject_task")
workflow.set_finish_point("generate_chart")
```

### Step 7: Update Direct Mode Handler (`cli.py`)
Pass CLI flags to graph state:
```python
def run_direct_mode(prompt, style, format, type):
    initial_state = {
        "messages": [{"role": "user", "content": prompt}],
        "interaction_mode": "direct",
        "chart_request": {"type": type, "style": style, "format": format},
        # ... other fields as None
    }
    result = graph.invoke(initial_state)
    print(result["messages"][-1]["content"])
```

### Testing Strategy

**Unit Tests:**
1. Test `extract_data`: Mock Gemini, verify JSON parsing
2. Test `matplotlib_chart_generator`: 
   - Test FD colors applied correctly
   - Test BNR colors applied correctly
   - Test bar vs line rendering
   - Test PNG vs SVG output
3. Test `generate_chart_tool`: Verify state updates correctly

**Integration Tests:**
1. Full flow test: Invoke graph with sample state, verify chart file created
2. Test data extraction with various formats:
   - "A=10, B=20, C=30"
   - "Monday: 4.1, Tuesday: 4.2"
   - "Q1: 120, Q2: 150, Q3: 140, Q4: 180"

**Acceptance Tests (Manual):**
1. Run: `graph-agent "A=10, B=20, C=30" --style fd --format png --type bar`
   - Verify PNG file created
   - Open file, verify FD colors
   - Verify bar chart
2. Run: `graph-agent "Jan: 100, Feb: 120, Mar: 110" --style bnr --format svg --type line`
   - Verify SVG file created
   - Open file, verify BNR colors
   - Verify line chart
3. Test file naming: Verify timestamp format correct
<!-- SECTION:PLAN:END -->
