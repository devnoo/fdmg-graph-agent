# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- BACKLOG.MD MCP GUIDELINES START -->

<CRITICAL_INSTRUCTION>

## BACKLOG WORKFLOW INSTRUCTIONS

This project uses Backlog.md MCP for all task and project management activities.

**CRITICAL GUIDANCE**

- If your client supports MCP resources, read `backlog://workflow/overview` to understand when and how to use Backlog for this project.
- If your client only supports tools or the above request fails, call `backlog.get_workflow_overview()` tool to load the tool-oriented overview (it lists the matching guide tools).

- **First time working here?** Read the overview resource IMMEDIATELY to learn the workflow
- **Already familiar?** You should have the overview cached ("## Backlog.md Overview (MCP)")
- **When to read it**: BEFORE creating tasks, or when you're unsure whether to track work

These guides cover:
- Decision framework for when to create tasks
- Search-first workflow to avoid duplicates
- Links to detailed guides for task creation, execution, and completion
- MCP tools reference

You MUST read the overview resource to understand the complete workflow. The information is NOT summarized here.

</CRITICAL_INSTRUCTION>

<!-- BACKLOG.MD MCP GUIDELINES END -->

## Project Overview

Graph Agent is an AI-powered CLI tool for journalists at FD (Financieele Dagblad) and BNR (Dutch news outlets) to create brand-compliant charts from natural language or data inputs. It uses Google Gemini LLM for intent detection and data extraction, LangGraph for state machine workflow, and matplotlib for chart generation with precise brand styling.

## Development Environment

### Prerequisites
- Python 3.10+
- `uv` package manager (already installed)
- Google AI API key (get from https://aistudio.google.com/app/apikey)

### Setup
```bash
# Install dependencies
uv sync

# Configure API key (required for development)
cp .env.example .env
# Edit .env and add: GOOGLE_API_KEY=your-key-here

# Verify setup
uv run python -c "import langgraph, click, matplotlib, pandas, langchain_google_genai"
```

### Running the CLI
```bash
# Direct mode (single command)
uv run graph-agent "A=10, B=20, C=30"
uv run graph-agent "Q1=120, Q2=150" --style bnr --type line --format svg

# Conversational mode (REPL)
uv run graph-agent

# Development (after making changes)
uv sync  # Re-sync if dependencies changed
```

### Common Commands

**Testing:**
```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run specific test file
uv run python -m pytest tests/test_agent.py -v

# Run single test
uv run python -m pytest tests/test_agent.py::test_parse_intent_node_with_chart_request -v

# Run with short traceback
uv run python -m pytest tests/ -v --tb=short

# Integration tests (requires GOOGLE_API_KEY in .env)
uv run python -m pytest tests/test_integration.py -v

# Visual regression tests
uv run python -m pytest tests/test_visual_regression.py -v

# Update visual regression snapshots (after intentional styling changes)
uv run python -m pytest tests/test_visual_regression.py --image-snapshot-update

# Save diff images when visual tests fail (for debugging)
uv run python -m pytest tests/test_visual_regression.py --image-snapshot-save-diff
```

**Linting and Formatting:**
```bash
# Check code style with flake8
uv run flake8 graph_agent/ tests/ --max-line-length=120 --extend-ignore=E203

# Check formatting with black
uv run black graph_agent/ tests/ --check

# Auto-format code with black
uv run black graph_agent/ tests/
```

**Running the Application:**
```bash
# Install as editable package
uv pip install -e .

# Run CLI directly (after install)
graph-agent "A=10, B=20, C=30"

# Or use uv run (no install needed)
uv run graph-agent "A=10, B=20, C=30"
```

**Dependency Management:**
```bash
# Install/sync dependencies
uv sync

# Add a new dependency
uv pip install package-name
# Then add to pyproject.toml manually

# Update dependencies
uv sync --upgrade
```

**Note**: Tests automatically load `.env` via `conftest.py`. Integration tests requiring LLM calls are skipped if `GOOGLE_API_KEY` is not set.

## Architecture

### High-Level Structure

Graph Agent uses a **LangGraph state machine** to process user requests through a series of nodes:

```
User Input
    ↓
parse_intent (Gemini classifies: make_chart vs off_topic)
    ↓
[Conditional Routing]
    ├─ make_chart → extract_data (Gemini extracts label-value pairs)
    │                    ↓
    │               generate_chart_tool (matplotlib creates chart)
    │                    ↓
    │               Chart file saved (chart-YYYYMMDDHHMMSS.{png|svg})
    │
    └─ off_topic → reject_task (polite rejection message)
```

### Core Components

**1. State Management (`graph_agent/state.py`)**
- `GraphState` (TypedDict): Immutable state passed between nodes
- Fields:
  - `messages`: Conversation history
  - `interaction_mode`: "direct" or "conversational"
  - `intent`: "make_chart", "off_topic", or "unknown"
  - `input_data`: JSON string of extracted data `[{"label": "A", "value": 10}, ...]`
  - `chart_request`: Chart parameters `{"type": "bar", "style": "fd", "format": "png"}`
  - `final_filepath`: Absolute path to generated chart

**2. LangGraph Agent (`graph_agent/agent.py`)**
- **Nodes** (functions that transform state):
  - `parse_intent()`: Uses Gemini to detect if request is chart-related
    - Includes pattern-based fallback with regex: `r"[A-Za-z0-9]+\s*[=:]\s*[0-9,.]+"`
    - Recognizes Dutch keywords: "grafiek", "diagram", etc.
  - `extract_data()`: Uses Gemini to extract label-value pairs as JSON
    - Cleans markdown code blocks from LLM response
    - Validates JSON format
  - `generate_chart_tool()`: Calls matplotlib tool to create chart
  - `reject_task()`: Returns rejection message based on intent

- **Routing**:
  - `route_after_intent()`: Conditional routing based on detected intent

- **Graph Construction**:
  - `create_graph()`: Builds and compiles the LangGraph workflow
  - Entry point: `parse_intent`
  - Conditional edges after intent detection
  - Terminal nodes: `reject_task`, `generate_chart`

**3. Chart Generation Tool (`graph_agent/tools.py`)**
- `matplotlib_chart_generator()`: Main chart generation function
  - Accepts: JSON data string, chart_type ("bar"|"line"), style ("fd"|"bnr"), format ("png"|"svg")
  - Returns: Absolute filepath to generated chart

- **Brand Styling**:
  ```python
  BRAND_COLORS = {
      "fd": {"primary": "#379596", "content": "#191919", "background": "#ffeadb"},
      "bnr": {"primary": "#ffd200", "content": "#000", "background": "#fff"}
  }
  ```
  - `apply_brand_style()`: Applies colors, removes top/right spines, adds subtle grid
  - Charts are publication-ready: no title, clean axes, proper spacing

**4. CLI Interface (`graph_agent/cli.py`)**
- Built with Click framework
- Loads `.env` automatically on startup via `load_dotenv()`
- Two modes:
  - **Direct mode**: Single command with prompt argument
  - **Conversational mode**: REPL loop (no arguments)

- **Options**:
  - `--style` (default: "fd"): Brand style
  - `--format` (default: "png"): Output format
  - `--type` (default: "bar"): Chart type

- Entry point defined in `pyproject.toml`: `graph-agent = "graph_agent.cli:main"`

### Key Design Patterns

**1. Intent Detection with Fallback**
The agent uses a two-stage approach:
- Primary: Gemini LLM classification
- Fallback: Regex pattern matching for data patterns like "A=10, B=20"

This ensures robust detection even when users provide raw data without explicit chart keywords.

**2. LLM Response Cleanup**
Gemini sometimes wraps JSON in markdown code blocks:
```python
if extracted_json.startswith("```"):
    lines = extracted_json.split("\n")
    extracted_json = "\n".join(lines[1:-1]) if len(lines) > 2 else extracted_json
    extracted_json = extracted_json.replace("```json", "").replace("```", "").strip()
```

**3. Environment Variable Management**
- `.env` file for local development (gitignored)
- `.env.example` for documentation
- `conftest.py` auto-loads `.env` for pytest
- `cli.py` auto-loads `.env` on startup

**4. State Machine Immutability**
Each node returns a new `GraphState` object. Never mutate state in-place:
```python
# Good
return GraphState(
    messages=state["messages"] + [new_message],
    # ... other fields
)

# Bad
state["messages"].append(new_message)  # Don't mutate!
```

## Testing Strategy

The project uses **Test-Driven Development (TDD)** methodology:

1. **Unit Tests** (`tests/test_*.py`):
   - `test_state.py`: State structure validation
   - `test_agent.py`: Individual node functions and routing logic
   - `test_tools.py`: Chart generation and brand styling
   - `test_cli.py`: CLI command handling (mocked LLM)

2. **Integration Tests** (`tests/test_integration.py`):
   - Require real `GOOGLE_API_KEY` in `.env`
   - Test full workflow with actual Gemini LLM
   - Skipped automatically if API key not present

3. **Test Fixtures** (`conftest.py`):
   - Auto-loads `.env` for all tests
   - Provides consistent test environment

4. **Visual Regression Tests** (`tests/test_visual_regression.py`):
   - Uses `pytest-image-snapshot` to detect visual changes
   - Tests all 4 chart combinations: FD/BNR × bar/line
   - Edge cases: single point, large datasets, decimals, zero values
   - Baseline snapshots stored in `tests/snapshots/`
   - Run independently: `pytest tests/test_visual_regression.py`

### Test File Naming Convention
- Test files: `test_*.py`
- Test classes: `TestClassName` or `Test*`
- Test functions: `test_*`

### Visual Regression Testing

Visual regression tests ensure chart styling, brand colors, and layout remain consistent across changes:

**How it works:**
1. First run generates baseline snapshot images
2. Subsequent runs compare generated charts against snapshots
3. Tests fail if visual differences exceed threshold (0.1 = 10%)
4. Diff images saved for debugging when `--image-snapshot-save-diff` is used

**Updating snapshots after intentional changes:**
```bash
# After modifying brand colors or styling
uv run python -m pytest tests/test_visual_regression.py --image-snapshot-update
```

**Debugging visual test failures:**
```bash
# Save diff images to see what changed
uv run python -m pytest tests/test_visual_regression.py --image-snapshot-save-diff
# Check tests/snapshots/ for *-diff.png files
```

**Coverage:**
- **Standard charts**: FD bar, FD line, BNR bar, BNR line
- **Edge cases**: Single data point, large datasets (12 points), decimal values, very small/large values, zero values, mixed ranges
- **Total**: 11 visual regression tests

**Important notes:**
- Snapshots are committed to git as the baseline
- Visual tests catch unintended changes from matplotlib updates
- Threshold of 0.1 allows for minor rendering variations
- Diff images are gitignored (tests/snapshots/*-diff.png)

## Common Development Tasks

### Adding a New Node to the Graph
1. Define node function in `agent.py`:
   ```python
   def my_new_node(state: GraphState) -> GraphState:
       # Transform state
       return GraphState(...)
   ```
2. Add node to workflow in `create_graph()`:
   ```python
   workflow.add_node("my_new_node", my_new_node)
   workflow.add_edge("previous_node", "my_new_node")
   ```
3. Write tests in `test_agent.py`:
   ```python
   def test_my_new_node():
       state = GraphState(...)
       result = my_new_node(state)
       assert result["field"] == expected_value
   ```

### Extending GraphState
1. Update `GraphState` TypedDict in `state.py`
2. Update all node functions to handle new field
3. Update tests to include new field in state construction
4. Update `test_state.py` with validation tests for new field

### Modifying Brand Colors
Edit `BRAND_COLORS` constant in `tools.py`:
```python
BRAND_COLORS = {
    "new_brand": {
        "primary": "#hexcolor",
        "content": "#hexcolor",
        "background": "#hexcolor"
    }
}
```

### Debugging LLM Responses
Add temporary print statements in node functions:
```python
def extract_data(state: GraphState) -> GraphState:
    response = llm.invoke(prompt)
    print(f"LLM response: {response.content}")  # Debug
    extracted_json = response.content.strip()
    # ... rest of function
```

## File Organization

```
graph_agent/
├── __init__.py           # Empty (package marker)
├── state.py              # GraphState TypedDict definition
├── agent.py              # LangGraph nodes, routing, graph creation
├── tools.py              # matplotlib chart generation and brand styling
└── cli.py                # Click CLI with direct/conversational modes

tests/
├── conftest.py           # pytest fixtures and .env loading
├── test_state.py         # State structure validation
├── test_agent.py         # Node and routing tests
├── test_tools.py         # Chart generation tests
├── test_cli.py           # CLI tests (mocked)
└── test_integration.py   # End-to-end tests with real LLM

backlog/
└── tasks/                # Story definitions and task tracking
    └── task-*.md         # Individual story files with acceptance criteria

.env.example              # Template for API key configuration
.env                      # Local API key (gitignored)
pyproject.toml            # Project metadata and dependencies
uv.lock                   # Locked dependency versions
