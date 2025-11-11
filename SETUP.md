# Graph Agent - Quick Setup Guide

## 1. Get your Google AI API Key

Visit https://aistudio.google.com/app/apikey to get your free API key.

## 2. Configure your environment

Copy the example file and add your key:

```bash
cp .env.example .env
```

Then edit `.env` and replace with your actual key:
```
GOOGLE_API_KEY=your-actual-api-key-here
```

## 3. Install dependencies

```bash
uv sync
```

## 4. Try it out!

```bash
# Simple data
uv run graph-agent "A=10, B=20, C=30"

# Multi-line Dutch example
uv run graph-agent "Geef me een grafiek met checkins:
Maandag = 4.1
Dinsdag = 4.2
Woensdag = 4.4"

# With custom styling
uv run graph-agent "Q1=120, Q2=150, Q3=140" --style bnr --type line --format svg
```

## 5. Run tests

```bash
# All tests
uv run python -m pytest tests/ -v

# With real LLM (requires API key in .env)
uv run python -m pytest tests/ -v --run-integration
```

## Tips

- The `.env` file is automatically loaded by both the CLI and pytest
- Charts are saved as `chart-[timestamp].[format]` in the current directory
- Default settings: `--style fd --format png --type bar`
- Works with Dutch, English, or any language for data input
