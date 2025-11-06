---
id: task-4
title: 'Story 4: Conversational Mode - Basic REPL'
status: To Do
assignee: []
created_date: '2025-11-06 13:25'
updated_date: '2025-11-06 13:26'
labels:
  - phase-2
  - conversational
  - repl
  - session-state
dependencies:
  - task-3
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
This story extends the agent to work in conversational mode with full chart generation capabilities. Users can now have interactive sessions where they make multiple chart requests.

This is the same functionality as Story 3, but in a stateful REPL instead of stateless direct mode.

## User Story
**As a journalist**, I want to start a conversational session where I can create multiple charts interactively, so I can iterate on my visualizations without restarting the command each time.

## Technical Requirements

### Conversational Mode Behavior
- User starts with: `graph-agent` (no arguments)
- Agent enters REPL loop
- User can make multiple chart requests in the same session
- Session maintains context (message history)
- User types `exit` or `quit` to leave

### Session State Management
The conversational mode must maintain state across turns:
```python
# Initialize once at start of session
session_state = {
    "messages": [],
    "interaction_mode": "conversational",
    "chart_request": {"type": None, "style": None, "format": None},
    # ... other fields
}

# Each turn:
# 1. Append user message
# 2. Invoke graph
# 3. Print assistant response
# 4. Loop
```

### Full Functionality
All features from Story 3 should work:
- Data extraction from text
- Chart generation with brand styling
- File output with timestamps

### Example Interaction
```bash
$ graph-agent
Welcome to Graph Agent! I can help you create bar and line charts.
Type 'exit' or 'quit' to leave.

> create a bar chart with: A=10, B=20, C=30. Use FD style, PNG format.

Generating chart...
Chart saved: /home/user/projects/chart-20251106140100.png

> Now make a line chart with: Jan=100, Feb=120, Mar=110. BNR style, SVG.

Generating chart...
Chart saved: /home/user/projects/chart-20251106140130.svg

> exit
Goodbye!
```

## Implementation Notes

### Handling Explicit Parameters in Conversational Mode
Unlike direct mode (which has CLI flags), conversational mode relies on the LLM to extract parameters from natural language:
- Style: "use FD style", "BNR colors", "Financial Daily brand"
- Format: "as PNG", "save as SVG"
- Type: "bar chart", "line graph"

For this story, **all parameters must be explicit** in the user's message. We're not handling ambiguity yet (that's Story 7).

### Session Memory vs Persistent Memory
- **Session memory**: Message history within current REPL session (Story 4)
- **Persistent memory**: User preferences saved to disk (Story 6)

Story 4 only implements session memory.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Running 'graph-agent' (no args) starts conversational REPL
- [ ] #2 User can make multiple chart requests in one session
- [ ] #3 Each chart request generates a new file with unique timestamp
- [ ] #4 The REPL maintains message history across turns
- [ ] #5 User can type 'exit' or 'quit' to terminate the session
- [ ] #6 Charts are generated with correct styling when style is specified in text
- [ ] #7 All chart generation features from Story 3 work in conversational mode
- [ ] #8 Session state is maintained but not persisted (restarting clears history)
- [ ] #9 LLM successfully extracts parameters (type, style, format) from natural language
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Update `extract_data` Node to Handle NL Parameters
Extend the `extract_data` node from Story 3 to also extract chart parameters from natural language:

```python
def extract_data(state: GraphState) -> GraphState:
    """Extract data AND parameters from natural language"""
    user_message = state["messages"][-1]["content"]
    
    # Call Gemini with enhanced prompt:
    # "Extract data AND chart parameters from this text.
    #  Return JSON: {
    #    'data': [{'label': '...', 'value': ...}, ...],
    #    'type': 'bar' or 'line' or null,
    #    'style': 'fd' or 'bnr' or null,
    #    'format': 'png' or 'svg' or null
    #  }"
    
    result = llm.invoke(prompt)
    parsed = json.loads(result)
    
    state["input_data"] = json.dumps(parsed["data"])
    
    # Merge extracted params with existing chart_request
    if parsed["type"]:
        state["chart_request"]["type"] = parsed["type"]
    if parsed["style"]:
        state["chart_request"]["style"] = parsed["style"]
    if parsed["format"]:
        state["chart_request"]["format"] = parsed["format"]
    
    return state
```

### Step 2: Update `run_conversational_mode` in CLI
Modify the conversational loop to maintain state across turns:

```python
def run_conversational_mode():
    print("Welcome to Graph Agent! I can help you create bar and line charts.")
    print("Type 'exit' or 'quit' to leave.\n")
    
    # Initialize session state ONCE
    session_state = {
        "messages": [],
        "interaction_mode": "conversational",
        "intent": "unknown",
        "input_data": None,
        "chart_request": {"type": None, "style": None, "format": None},
        "final_filepath": None
    }
    
    while True:
        user_input = input("> ").strip()
        
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break
        
        # Append user message
        session_state["messages"].append({
            "role": "user",
            "content": user_input
        })
        
        # Invoke graph with current state
        session_state = graph.invoke(session_state)
        
        # Print assistant's last message
        last_message = session_state["messages"][-1]
        if last_message["role"] == "assistant":
            print(f"\n{last_message['content']}\n")
```

### Step 3: Ensure State Persistence Across Graph Invocations
The key difference from direct mode: **the state object is reused** across multiple graph invocations.

Each graph invocation:
1. Receives the current session_state
2. Appends messages to the history
3. Returns updated session_state
4. CLI uses this updated state for the next turn

### Step 4: Update Parameter Extraction Logic
Since conversational mode doesn't have CLI flags, all parameters come from natural language:

**Example prompts the LLM should handle:**
- "Create a bar chart with A=10, B=20. FD style, PNG." → All params extracted
- "Make a line graph: Jan=100, Feb=120. BNR style, SVG format." → All params extracted
- "Bar chart: Q1=50, Q2=60, Q3=70. FD colors." → type + style extracted, format defaults

### Step 5: Test Conversational Flow
Key test scenarios:
1. **Single chart request**: Start session, make one chart, exit
2. **Multiple charts**: Make 3 charts in one session, verify unique files
3. **Message history**: Verify state.messages grows across turns
4. **Exit handling**: Test both 'exit' and 'quit' commands

### Testing Strategy

**Integration Tests:**
1. Test conversational loop with mock graph:
   - Verify state is maintained across iterations
   - Verify user can exit cleanly

2. Test parameter extraction from natural language:
   - "bar chart with A=10, B=20, FD style, PNG" → All params
   - "line graph: Jan=100, Feb=120, BNR, SVG" → All params

**Acceptance Tests (Manual):**
1. Start `graph-agent` (no args)
2. Create first chart: "bar chart: A=10, B=20, C=30. FD style, PNG."
   - Verify chart created
3. Create second chart: "line graph: X=1, Y=2, Z=3. BNR style, SVG."
   - Verify second chart created with different timestamp
4. Type `exit`
   - Verify clean exit
5. Restart `graph-agent`
   - Verify message history is cleared (no persistence yet)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
### Handling Explicit Parameters in Conversational Mode
Unlike direct mode (which has CLI flags), conversational mode relies on the LLM to extract parameters from natural language:
- Style: "use FD style", "BNR colors", "Financial Daily brand"
- Format: "as PNG", "save as SVG"
- Type: "bar chart", "line graph"

For this story, **all parameters must be explicit** in the user's message. We're not handling ambiguity yet (that's Story 7).

### Session Memory vs Persistent Memory
- **Session memory**: Message history within current REPL session (Story 4)
- **Persistent memory**: User preferences saved to disk (Story 6)

Story 4 only implements session memory.
<!-- SECTION:DESCRIPTION:END -->
<!-- SECTION:NOTES:END -->
