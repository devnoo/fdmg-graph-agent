---
id: task-16
title: Context-Aware Intent Detection for Conversational Follow-ups
status: To Do
assignee: []
created_date: '2025-11-11 09:28'
labels:
  - enhancement
  - conversational-mode
  - intent-detection
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Enhance the intent detection system to understand conversational context. Currently, when a user creates a chart and then asks follow-up questions like "can you change the style?" or "add more values", the system rejects these as off-topic because it only analyzes the last message in isolation.

## Problem
The `parse_intent` node only looks at `state["messages"][-1]["content"]` without considering:
- Conversation history (previous messages)
- Whether a chart was just created
- Follow-up modification requests

## Example Failure Case
1. User: "Draw a line graph for Q1=100, Q2=200" → Works ✓
2. User: "Can you change the style to BNR?" → Rejected as off-topic ✗
3. User: "Add Q3=150" → Rejected as off-topic ✗

## Proposed Solution

### 1. **Conversation Context Analysis**
Modify `parse_intent()` to pass conversation history to the LLM:
- Include last 3-5 messages (not just the last one)
- Let LLM understand context: "User just made a chart, this is a follow-up request"
- Detect modification keywords: "change", "modify", "update", "add", "remove", "switch to"

### 2. **New Intent Type: `modify_chart`**
Add a new intent classification:
- `make_chart`: Create new chart from scratch
- `modify_chart`: Modify/update existing chart (NEW)
- `set_config`: Set default preferences
- `off_topic`: Unrelated requests

### 3. **Chart State Tracking**
Track whether a chart was recently created:
- Add `last_chart_params` to `GraphState` (stores type/style/format/data from last chart)
- Persist this across conversation turns
- Use to detect if user is referring to "the chart" or "it"

### 4. **Enhanced Prompt Engineering**
Update the system prompt in `parse_intent()`:
```
Analyze the conversation history (not just the last message) to determine intent:

Context indicators for "modify_chart":
- Previous message created a chart
- User says: "change style", "make it BNR", "switch to bar", "add values", "update it"
- User refers to previous chart: "the chart", "it", "this graph"

Return JSON:
{
  "intent": "make_chart" | "modify_chart" | "set_config" | "off_topic",
  "modification_type": "style" | "type" | "data" | "format" | null,
  "has_file": true/false,
  ...
}
```

### 5. **New Node: `modify_existing_chart`**
Create a node that:
- Retrieves last chart parameters from state
- Merges new parameters from user request
- Regenerates chart with combined parameters
- Maintains conversation continuity

### 6. **Routing Logic Update**
Update `route_after_intent()`:
```python
if intent == "modify_chart":
    return "modify_existing_chart"  # NEW path
elif intent == "make_chart":
    # ... existing logic
```

## Files to Modify

1. **graph_agent/state.py**
   - Add `last_chart_params` field to `GraphState`

2. **graph_agent/agent.py**
   - Modify `parse_intent()`: Pass conversation history to LLM
   - Update system prompt with context awareness
   - Add new node `modify_existing_chart()`
   - Update `route_after_intent()` to handle `modify_chart`
   - Track `last_chart_params` in `generate_chart_tool()`

3. **tests/test_agent.py**
   - Add tests for conversation context scenarios
   - Test follow-up requests: style change, type change, data additions
   - Test multi-turn conversations

## Benefits
- Natural conversational flow in REPL mode
- Users can iteratively refine charts without repeating all parameters
- Better UX for journalists working iteratively

## Implementation Phases

### Phase 1: Context Analysis (Minimal Change)
- Modify `parse_intent()` to include last 3 messages in prompt
- Update LLM prompt to detect follow-ups
- Map follow-ups to existing `make_chart` intent
- Test: "create chart" → "change style" works

### Phase 2: Dedicated Modification Path (Full Solution)
- Add `modify_chart` intent
- Create `modify_existing_chart()` node
- Add `last_chart_params` to state
- Implement proper merging logic

### Phase 3: Advanced Features (Future)
- Multi-step modifications: "change to bar AND use BNR style"
- Undo/redo support
- Comparison mode: "show me both FD and BNR versions"
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 User can create chart and immediately ask to change style without rejection
- [ ] #2 User can say 'add more data points' after creating chart
- [ ] #3 User can say 'change to bar chart' after creating line chart
- [ ] #4 System recognizes pronouns: 'change it to BNR', 'make this a bar chart'
- [ ] #5 Context awareness limited to last 3-5 messages (performance)
- [ ] #6 New intent 'modify_chart' detected correctly in conversational mode
- [ ] #7 Last chart parameters persisted in state across turns
- [ ] #8 Tests cover multi-turn conversations with modifications
- [ ] #9 Direct mode unaffected (single-shot commands still work)
- [ ] #10 Off-topic requests still correctly rejected even with chart history
<!-- AC:END -->
