---
id: task-16.1
title: 'Phase 1: Quick Context-Aware Intent Detection Fix'
status: To Do
assignee: []
created_date: '2025-11-11 09:37'
labels:
  - phase-1
  - intent-detection
  - quick-win
dependencies: []
parent_task_id: task-16
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement minimal changes to make intent detection context-aware by passing conversation history to the LLM. This phase provides immediate value with minimal architectural changes.

## Goal
Enable the system to recognize follow-up requests like "change the style" or "add more data" by giving the LLM conversation context instead of just the last message.

## Changes Required

### 1. Update `parse_intent()` in `graph_agent/agent.py`

**Current behavior:**
```python
# Get the last user message
user_message = state["messages"][-1]["content"]
```

**New behavior:**
```python
# Get conversation history (last 3-5 messages for context)
recent_messages = state["messages"][-5:]  # Last 5 messages
conversation_context = "\n".join([
    f"{msg['role']}: {msg['content']}" 
    for msg in recent_messages
])
```

### 2. Enhanced LLM Prompt

Update the system prompt to analyze conversation context:

```python
system_prompt = """Analyze the conversation history (not just the last message) to determine intent.

CONVERSATION CONTEXT:
{conversation_history}

Intent should be "make_chart" if:
- Keywords: chart, graph, bar, line, plot, visualize, grafiek, diagram
- Data patterns: "A=10, B=20", "Monday: 4.1"
- **FOLLOW-UP REQUESTS**: User just created a chart and now asks to:
  * Change style: "change style", "make it BNR", "switch to FD"
  * Change type: "make it a bar chart", "change to line"
  * Add/modify data: "add Q3=150", "update values", "change A to 15"
  * Change format: "export as SVG", "make it PNG"
- References to previous chart: "the chart", "it", "this graph"

Intent should be "set_config" if:
- Setting defaults: "set my default style to FD"

Intent should be "off_topic" for:
- Unrelated requests (sandwiches, appointments, etc.)
- Generic questions without chart context

Return JSON:
{{
  "intent": "make_chart" or "set_config" or "off_topic",
  "has_file": true or false,
  "config_type": "style" or "format" or null,
  "config_value": "fd" or "bnr" or "png" or "svg" or null,
  "is_follow_up": true or false
}}

Current user request: {request}

JSON response:"""
```

### 3. Handle Follow-ups as New Charts

When `is_follow_up=true` and `intent="make_chart"`:
- The existing workflow handles it naturally
- `extract_data()` will extract new parameters
- Missing parameters get filled from defaults/last_used preferences
- This creates a new chart with modified parameters

### 4. Testing

Add test cases in `tests/test_agent.py`:

```python
def test_parse_intent_follow_up_style_change():
    """Test that 'change style' after chart creation is recognized as make_chart."""
    state = GraphState(
        messages=[
            {"role": "user", "content": "Make a bar chart with A=10, B=20"},
            {"role": "assistant", "content": "Chart saved: chart-123.png"},
            {"role": "user", "content": "Can you change the style to BNR?"}
        ],
        interaction_mode="conversational",
        # ... other fields
    )
    result = parse_intent(state)
    assert result["intent"] == "make_chart"

def test_parse_intent_follow_up_add_data():
    """Test that 'add data' after chart creation is recognized as make_chart."""
    state = GraphState(
        messages=[
            {"role": "user", "content": "Q1=100, Q2=200"},
            {"role": "assistant", "content": "Chart saved: chart-456.png"},
            {"role": "user", "content": "Add Q3=150"}
        ],
        interaction_mode="conversational",
        # ... other fields
    )
    result = parse_intent(state)
    assert result["intent"] == "make_chart"

def test_parse_intent_follow_up_type_change():
    """Test that 'change to bar' after line chart is recognized as make_chart."""
    state = GraphState(
        messages=[
            {"role": "user", "content": "Line chart for Jan=10, Feb=20"},
            {"role": "assistant", "content": "Chart saved: chart-789.png"},
            {"role": "user", "content": "Make it a bar chart"}
        ],
        interaction_mode="conversational",
        # ... other fields
    )
    result = parse_intent(state)
    assert result["intent"] == "make_chart"
```

## Limitations of Phase 1

- Creates **new charts** for each follow-up (no true modification)
- No state tracking of previous chart parameters
- User must repeat data if only changing style
- Works for: "change style" but NOT "add Q3=150 to the existing data"

These limitations are addressed in Phase 2 with proper state tracking.

## Estimated Effort
- Implementation: 1-2 hours
- Testing: 1 hour
- **Total: 2-3 hours**
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 parse_intent() passes last 5 messages to LLM instead of just last message
- [ ] #2 LLM prompt includes conversation context analysis instructions
- [ ] #3 Follow-up request 'change style to BNR' after chart creation detected as make_chart
- [ ] #4 Follow-up request 'change to bar chart' after line chart detected as make_chart
- [ ] #5 Test cases added for multi-turn conversations
- [ ] #6 Off-topic requests still correctly rejected even with chart history
- [ ] #7 Direct mode unaffected (single-shot commands work)
- [ ] #8 Performance acceptable (no significant slowdown from longer prompts)
<!-- AC:END -->
