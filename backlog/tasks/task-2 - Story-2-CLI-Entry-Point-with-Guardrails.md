---
id: task-2
title: 'Story 2: CLI Entry Point with Guardrails'
status: To Do
assignee: []
created_date: '2025-11-06 13:23'
updated_date: '2025-11-06 13:24'
labels:
  - phase-1
  - cli
  - guardrails
  - langgraph
dependencies:
  - task-1
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
This story establishes the CLI entry point and implements the core guardrail functionality. The goal is to get the agent running as quickly as possible with proper boundaries - it should reject any non-chart-related requests politely.

This is a critical early milestone: after this story, the agent can be invoked and will respond to users, even if it can't generate charts yet.

## User Stories
- **As a journalist**, I want to invoke `graph-agent` and have it start successfully
- **As a journalist**, I want the agent to tell me it can only help with charts when I ask it to do something else
- **As a journalist**, I want this to work in both direct mode (single command) and conversational mode (REPL)

## Technical Architecture
This story implements the following components:

### 1. CLI Interface (`cli.py`)
Built with `click`, supporting two modes:
- **Direct Mode**: `graph-agent "make me a sandwich"` → Agent responds and exits
- **Conversational Mode**: `graph-agent` → Starts a REPL where users can type multiple requests

### 2. LangGraph State Machine (Basic)
A minimal LangGraph flow with two nodes:
- **`parse_intent`**: Uses Gemini to analyze user input and determine if it's chart-related
- **`reject_task`**: Returns a polite rejection message

### 3. State Object (`GraphState`)
```python
class GraphState(TypedDict):
    messages: list  # Chat history
    interaction_mode: str  # 'direct' or 'conversational'
    intent: str  # 'make_chart' or 'off_topic'
```

## Behavior Specification
**For off-topic requests**, the agent responds:
> "I can only help you create charts. Please ask me to make a bar or line chart."

**Chart-related requests** (detected by keywords like "chart", "graph", "bar", "line", "visualize", "plot") currently respond:
> "Chart generation is not yet implemented. Check back soon!"

This allows us to test the intent detection without implementing full chart generation.

## Example Interactions

### Direct Mode
```bash
$ graph-agent "make me a sandwich"
I can only help you create charts. Please ask me to make a bar or line chart.
```

### Conversational Mode
```bash
$ graph-agent
Welcome to Graph Agent! I can help you create bar and line charts.
Type 'exit' or 'quit' to leave.

> make me a sandwich
I can only help you create charts. Please ask me to make a bar or line chart.

> create a bar chart
Chart generation is not yet implemented. Check back soon!

> exit
Goodbye!
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Running 'graph-agent' (no args) starts a conversational REPL that accepts input
- [ ] #2 Running 'graph-agent "some prompt"' executes in direct mode and exits after response
- [ ] #3 Off-topic requests (e.g., 'make me a sandwich') are rejected with the specified message in both modes
- [ ] #4 Chart-related requests (containing 'chart', 'graph', 'bar', 'line') are detected and return 'not yet implemented' message
- [ ] #5 User can type 'exit' or 'quit' in conversational mode to leave the REPL
- [ ] #6 LangGraph state machine has at minimum: GraphState, parse_intent node, reject_task node
- [ ] #7 Gemini LLM is successfully invoked for intent detection
- [ ] #8 All responses are in English (per architecture: English-only output for MVP)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Create Project Structure
Create the following files:
```
graph_agent/
├── __init__.py
├── cli.py          # CLI entry point
├── agent.py        # LangGraph state machine
└── state.py        # GraphState definition
```

### Step 2: Define GraphState (`state.py`)
```python
from typing import TypedDict, Literal

class GraphState(TypedDict):
    messages: list[dict]  # [{"role": "user"/"assistant", "content": str}]
    interaction_mode: Literal["direct", "conversational"]
    intent: Literal["make_chart", "off_topic", "unknown"]
```

### Step 3: Create LangGraph Agent (`agent.py`)
Implement a minimal state machine with:

**Node 1: `parse_intent`**
- Takes user message from `state.messages`
- Calls Gemini with a system prompt: "Analyze if this request is about creating a chart (bar/line graph). Respond with 'make_chart' or 'off_topic'."
- Updates `state.intent` based on LLM response
- Returns updated state

**Node 2: `reject_task`**
- Checks `state.intent`
- If `off_topic`: adds message "I can only help you create charts. Please ask me to make a bar or line chart."
- If `make_chart`: adds message "Chart generation is not yet implemented. Check back soon!"
- Returns updated state

**Graph Construction:**
```python
from langgraph.graph import StateGraph

workflow = StateGraph(GraphState)
workflow.add_node("parse_intent", parse_intent)
workflow.add_node("reject_task", reject_task)
workflow.set_entry_point("parse_intent")
workflow.add_edge("parse_intent", "reject_task")
workflow.set_finish_point("reject_task")

graph = workflow.compile()
```

### Step 4: Build CLI (`cli.py`)
Using `click`, implement:

**Main command:**
```python
@click.command()
@click.argument('prompt', required=False)
def main(prompt):
    if prompt:
        # Direct mode
        run_direct_mode(prompt)
    else:
        # Conversational mode
        run_conversational_mode()
```

**Direct mode function:**
- Create initial state with `interaction_mode='direct'`
- Add user prompt to messages
- Invoke graph
- Print final assistant message
- Exit

**Conversational mode function:**
- Print welcome message
- Loop:
  - Read user input
  - If 'exit' or 'quit': break
  - Create/update state with `interaction_mode='conversational'`
  - Invoke graph
  - Print assistant response
- Print goodbye message

### Step 5: Make CLI Executable
Add to `pyproject.toml`:
```toml
[project.scripts]
graph-agent = "graph_agent.cli:main"
```

Install in editable mode: `uv pip install -e .`

### Step 6: Configure Gemini API
Set up Gemini credentials:
- Require `GOOGLE_API_KEY` environment variable
- Add validation in `agent.py` to check if key is set
- Use `langchain_google_genai.ChatGoogleGenerativeAI` to initialize LLM

### Testing Strategy
**Manual Acceptance Tests:**
1. Test direct mode: `graph-agent "make me a sandwich"` → Should reject
2. Test direct mode: `graph-agent "create a bar chart"` → Should say "not implemented"
3. Test conversational mode: `graph-agent` → Should start REPL
4. In REPL: Try both off-topic and chart requests
5. In REPL: Type `exit` → Should terminate gracefully

**TDD Approach:**
- Start with acceptance test at CLI level
- Write integration test that invokes the graph with sample state
- Write unit tests for `parse_intent` node (mock Gemini responses)
- Write unit tests for `reject_task` node (pure logic)
<!-- SECTION:PLAN:END -->
