# Graph Agent - CLI Usage

## Prerequisites

Before using the Graph Agent CLI, you must set the `GOOGLE_API_KEY` environment variable:

```bash
export GOOGLE_API_KEY="your-google-ai-api-key"
```

## Installation

Install the package in editable mode:

```bash
uv pip install -e .
```

## Usage

### Conversational Mode (REPL)

Start the interactive mode by running `graph-agent` without arguments:

```bash
graph-agent
```

Example session:
```
Welcome to Graph Agent! I can help you create bar and line charts.
Type 'exit' or 'quit' to leave.

> create a bar chart
Chart generation is not yet implemented. Check back soon!

> make me a sandwich
I can only help you create charts. Please ask me to make a bar or line chart.

> exit
Goodbye!
```

### Direct Mode

Execute a single command and exit:

**Simple chart generation (uses defaults: FD style, PNG format, bar chart):**
```bash
graph-agent "Maandag=4.1, Dinsdag=4.2, Woensdag=4.4"
# Output: Chart saved: /home/user/chart-20251106143000.png
```

**Multi-line data (in Dutch or any language):**
```bash
graph-agent "Geef me een grafiek met het aantal checkins per dag bij het OV:
 Maandag = 4.1
 Dinsdag = 4.2
 Woensdag = 4.4
 Donderdag = 4.7
 Vrijdag = 4.2
 Zaterdag = 2.3
 Zondag = 1.7
 De getallen zijn in miljoenen check-ins."
# Output: Chart saved: /home/user/chart-20251106143005.png
```

**With explicit parameters:**
```bash
# FD-branded bar chart in PNG
graph-agent "Q1=120, Q2=150, Q3=140, Q4=180" --style fd --format png --type bar

# BNR-branded line chart in SVG
graph-agent "Jan: 100, Feb: 120, Mar: 110" --style bnr --format svg --type line
```

**Available options:**
- `--style` (default: fd): Brand style - `fd` or `bnr`
- `--format` (default: png): Output format - `png` or `svg`
- `--type` (default: bar): Chart type - `bar` or `line`

**Off-topic requests are rejected:**
```bash
graph-agent "make me a sandwich"
# Output: I can only help you create charts. Please ask me to make a bar or line chart.
```

## Architecture

The CLI consists of five main components:

1. **GraphState** (`state.py`): Type-safe state object for the LangGraph workflow with chart generation fields
2. **Agent** (`agent.py`): LangGraph state machine with:
   - Intent detection (chart-related vs off-topic)
   - Data extraction from natural language using Gemini LLM
   - Conditional routing to chart generation or rejection
3. **Tools** (`tools.py`): Chart generation using matplotlib with brand-specific styling (FD/BNR)
4. **CLI** (`cli.py`): Click-based command-line interface supporting both direct and conversational modes
5. **Tests** (`tests/`): Comprehensive test suite with 42 passing tests

### LangGraph Flow

```
User Input → parse_intent → [make_chart?]
                               ├─ Yes → extract_data → generate_chart → Chart File
                               └─ No  → reject_task → Rejection Message
```

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Run with linting:

```bash
flake8 graph_agent/ tests/ --max-line-length=120 --extend-ignore=E203
black graph_agent/ tests/ --check
```
