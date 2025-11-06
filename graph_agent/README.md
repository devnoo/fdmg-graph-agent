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

```bash
graph-agent "create a bar chart"
# Output: Chart generation is not yet implemented. Check back soon!

graph-agent "make me a sandwich"
# Output: I can only help you create charts. Please ask me to make a bar or line chart.
```

## Architecture

The CLI consists of three main components:

1. **GraphState** (`state.py`): Type-safe state object for the LangGraph workflow
2. **Agent** (`agent.py`): LangGraph state machine with intent detection and response generation
3. **CLI** (`cli.py`): Click-based command-line interface supporting both direct and conversational modes

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
