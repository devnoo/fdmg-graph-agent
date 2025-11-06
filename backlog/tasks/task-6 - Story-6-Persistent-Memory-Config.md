---
id: task-6
title: 'Story 6: Persistent Memory/Config'
status: To Do
assignee: []
created_date: '2025-11-06 13:27'
updated_date: '2025-11-06 13:28'
labels:
  - phase-3
  - config
  - persistence
  - user-preferences
dependencies:
  - task-5
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
This story implements persistent user preferences that survive across sessions. Users can set their default brand style and output format, which will be remembered between CLI invocations.

This is separate from session memory (Story 4), which only lasts for the current REPL session.

## User Stories
- **As a journalist**, I want to set my default brand style (FD or BNR) so I don't have to specify it every time
- **As a journalist**, I want to set my default output format (PNG or SVG) so charts are consistently saved in my preferred format
- **As a journalist**, I want these preferences to persist across sessions so I only need to set them once

## Technical Requirements

### Configuration File
Store preferences in `~/.config/graph-agent/settings.json`:
```json
{
  "default_style": "fd",
  "default_format": "png",
  "last_used_style": "bnr",
  "last_used_format": "svg"
}
```

### Priority Logic
Per requirements, the agent follows this priority order:

**For Style:**
1. **Explicit in query/CLI**: "FD style" or `--style fd`
2. **Default style**: User's saved default
3. **Last used style**: Most recent style from any session
4. **Ask or fail**: No default available

**For Format:**
1. **Explicit in query/CLI**: "as PNG" or `--format png`
2. **Default format**: User's saved default
3. **Last used format**: Most recent format
4. **Fallback to PNG**: Always default to PNG if nothing else set

### Setting Defaults
Users can set defaults via natural language in conversational mode:
- "Set my default style to FD"
- "Make BNR my default style"
- "Set default format to SVG"
- "Change my default output format to PNG"

### Config Module (`config.py`)
```python
def load_user_preferences() -> dict:
    """Load settings from ~/.config/graph-agent/settings.json"""
    
def save_user_preferences(style=None, format=None) -> None:
    """Update settings file with new defaults"""
    
def update_last_used(style=None, format=None) -> None:
    """Update last_used_* fields in settings"""
```

### LangGraph Integration
Add node `handle_config` that:
- Detects "set default" intents
- Updates config file
- Responds with confirmation

Update `resolve_ambiguity` node (future story) to:
- Load config at start
- Apply priority logic
- Save last_used values after chart generation

## Example Interactions

### Setting Defaults
```bash
$ graph-agent

> Set my default style to FD
Your default style is now set to FD.

> Set my default format to SVG
Your default format is now set to SVG.

> exit
```

### Using Defaults
```bash
$ graph-agent "chart: A=10, B=20, C=30" --type bar
# No style specified → uses default FD
# No format specified → uses default SVG
Chart saved: /home/user/chart-20251106142000.svg
```

### Priority Example
```bash
$ graph-agent "chart: A=10, B=20. BNR style" --type bar
# Explicit "BNR style" in query overrides default FD
# Uses default SVG format
# Updates last_used_style to "bnr"
Chart saved: /home/user/chart-20251106142030.svg
```

## File Location
- Primary: `~/.config/graph-agent/settings.json`
- Create directory if it doesn't exist
- Create file with defaults if it doesn't exist
- Use JSON for easy reading/editing by users

## Default Values
If no config file exists, initialize with:
```json
{
  "default_style": null,
  "default_format": null,
  "last_used_style": null,
  "last_used_format": null
}
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Config file is created at ~/.config/graph-agent/settings.json on first use
- [ ] #2 User can set default style via natural language in conversational mode
- [ ] #3 User can set default format via natural language in conversational mode
- [ ] #4 Default style is applied when no style specified in query or CLI
- [ ] #5 Default format is applied when no format specified in query or CLI
- [ ] #6 Explicit style in query/CLI overrides default
- [ ] #7 Explicit format in query/CLI overrides default
- [ ] #8 Last used style/format is updated after each successful chart generation
- [ ] #9 Priority logic works: Explicit > Default > Last Used > Ask/Fail (for style) or PNG (for format)
- [ ] #10 Settings persist across CLI invocations (direct and conversational modes)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Step 1: Create Config Module (`config.py`)
```python
import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "graph-agent"
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "default_style": None,
    "default_format": None,
    "last_used_style": None,
    "last_used_format": None
}

def ensure_config_exists():
    """Create config directory and file if they don't exist"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)

def load_user_preferences() -> dict:
    """Load settings from config file"""
    ensure_config_exists()
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_user_preferences(default_style=None, default_format=None):
    """Update default_* fields"""
    ensure_config_exists()
    settings = load_user_preferences()
    
    if default_style is not None:
        settings["default_style"] = default_style
    if default_format is not None:
        settings["default_format"] = default_format
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def update_last_used(style=None, format=None):
    """Update last_used_* fields"""
    ensure_config_exists()
    settings = load_user_preferences()
    
    if style is not None:
        settings["last_used_style"] = style
    if format is not None:
        settings["last_used_format"] = format
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
```

### Step 2: Add Config Detection to `parse_intent`
Update to detect "set default" requests:
```python
def parse_intent(state: GraphState) -> GraphState:
    """Detect intent including config changes"""
    user_message = state["messages"][-1]["content"]
    
    # Enhanced prompt:
    # "Analyze this request. Return JSON:
    #  {
    #    'intent': 'make_chart' or 'set_config' or 'off_topic',
    #    'has_file': true or false,
    #    'config_type': 'style' or 'format' or null,
    #    'config_value': 'fd' or 'bnr' or 'png' or 'svg' or null
    #  }"
    
    result = llm.invoke(enhanced_prompt)
    parsed = json.loads(result)
    
    state["intent"] = parsed["intent"]
    state["has_file"] = parsed.get("has_file", False)
    state["config_change"] = {
        "type": parsed.get("config_type"),
        "value": parsed.get("config_value")
    } if parsed["intent"] == "set_config" else None
    
    return state
```

### Step 3: Create `handle_config` Node
```python
def handle_config(state: GraphState) -> GraphState:
    """Handle config change requests"""
    from .config import save_user_preferences
    
    config_change = state.get("config_change")
    if not config_change:
        return state
    
    config_type = config_change["type"]
    config_value = config_change["value"]
    
    if config_type == "style":
        save_user_preferences(default_style=config_value)
        message = f"Your default style is now set to {config_value.upper()}."
    elif config_type == "format":
        save_user_preferences(default_format=config_value)
        message = f"Your default format is now set to {config_value.upper()}."
    else:
        message = "I couldn't understand that configuration change."
    
    state["messages"].append({
        "role": "assistant",
        "content": message
    })
    
    return state
```

### Step 4: Add Priority Resolution Logic
Create `resolve_parameters` node (or extend `extract_data`):
```python
def resolve_parameters(state: GraphState) -> GraphState:
    """Apply priority logic to resolve style and format"""
    from .config import load_user_preferences
    
    prefs = load_user_preferences()
    chart_req = state["chart_request"]
    
    # Resolve style (Priority: Explicit > Default > Last Used > None)
    if not chart_req.get("style"):
        chart_req["style"] = (
            prefs.get("default_style") or
            prefs.get("last_used_style") or
            None
        )
    
    # Resolve format (Priority: Explicit > Default > Last Used > PNG)
    if not chart_req.get("format"):
        chart_req["format"] = (
            prefs.get("default_format") or
            prefs.get("last_used_format") or
            "png"  # Fallback
        )
    
    state["chart_request"] = chart_req
    return state
```

### Step 5: Update Last Used After Chart Generation
Modify `generate_chart_tool` to update last_used:
```python
def generate_chart_tool(state: GraphState) -> GraphState:
    """Generate chart and update last used preferences"""
    from .tools import matplotlib_chart_generator
    from .config import update_last_used
    
    # Generate chart
    filepath = matplotlib_chart_generator(...)
    
    # Update last used
    style = state["chart_request"]["style"]
    format = state["chart_request"]["format"]
    update_last_used(style=style, format=format)
    
    # ... rest of node
    return state
```

### Step 6: Update Graph Flow
```python
def route_after_intent(state: GraphState) -> str:
    if state["intent"] == "off_topic":
        return "reject_task"
    elif state["intent"] == "set_config":
        return "handle_config"
    elif state.get("has_file"):
        return "call_data_tool"
    else:
        return "extract_data"

workflow.add_node("handle_config", handle_config)  # NEW
workflow.add_conditional_edges("parse_intent", route_after_intent)
workflow.set_finish_point("handle_config")  # NEW finish point
```

### Step 7: Update GraphState
```python
class GraphState(TypedDict):
    messages: list[dict]
    interaction_mode: Literal["direct", "conversational"]
    intent: Literal["make_chart", "off_topic", "set_config", "error", "unknown"]
    has_file: bool
    config_change: dict | None  # NEW: {"type": "style", "value": "fd"}
    input_data: str | None
    chart_request: dict | None
    final_filepath: str | None
```

### Testing Strategy

**Unit Tests:**
1. Test `config.py` functions:
   - Test file creation
   - Test load/save cycle
   - Test update_last_used
   - Test default values

2. Test priority logic:
   - Explicit overrides all
   - Default used when no explicit
   - Last used as fallback
   - PNG fallback for format

**Integration Tests:**
1. Test config change flow:
   - Parse "set default style to FD" → handle_config → verify file updated
2. Test priority application:
   - Set default style=FD
   - Request chart with no style
   - Verify FD used

**Acceptance Tests (Manual):**
1. Start fresh (delete config file)
2. Run: `graph-agent`
   > Set default style to FD
   - Verify confirmation message
   - Check `~/.config/graph-agent/settings.json` exists with default_style="fd"
3. Run: `graph-agent "chart: A=10, B=20" --type bar`
   - No style specified → should use FD default
4. Restart and verify settings persisted
<!-- SECTION:PLAN:END -->
