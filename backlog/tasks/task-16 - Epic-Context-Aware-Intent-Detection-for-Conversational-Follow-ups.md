---
id: task-16
title: 'Epic: Context-Aware Intent Detection for Conversational Follow-ups'
status: To Do
assignee: []
created_date: '2025-11-11 09:31'
labels:
  - epic
  - conversational-mode
  - intent-detection
  - enhancement
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Enhance the intent detection system to understand conversational context. Currently, when a user creates a chart and then asks follow-up questions like "can you change the style?" or "add more values", the system rejects these as off-topic because it only analyzes the last message in isolation.

## The Problem

The current `parse_intent` node analyzes only the last user message (`state["messages"][-1]["content"]`) without considering:
- Conversation history (previous messages)
- Whether a chart was just created
- Follow-up modification requests

### Example Failure Case
1. User: "Draw a line graph for Q1=100, Q2=200" → Works ✓
2. User: "Can you change the style to BNR?" → Rejected as off-topic ✗
3. User: "Add Q3=150" → Rejected as off-topic ✗

## Epic Goal

Enable natural conversational flow where users can iteratively refine charts through follow-up requests without repeating all parameters. This is critical for journalists working iteratively on visualizations.

## Implementation Strategy

This epic is broken into 3 phases (sub-stories):

1. **Phase 1: Quick Context-Aware Fix** (Minimal change, immediate value)
   - Pass conversation history to LLM
   - Update prompts to detect follow-ups
   - Map to existing intents

2. **Phase 2: Proper Architecture** (Clean separation of concerns)
   - New `modify_chart` intent
   - State tracking for last chart
   - Dedicated modification node

3. **Phase 3: Advanced Features** (Future enhancements)
   - Multi-parameter changes
   - Undo/redo
   - Comparison mode

## Key Files Affected

- `graph_agent/state.py` - Add chart state tracking
- `graph_agent/agent.py` - Update intent detection, add modification node, update routing
- `tests/test_agent.py` - Add multi-turn conversation tests
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All three phase sub-stories completed
- [ ] #2 User can create chart and modify it through natural follow-up requests
- [ ] #3 Conversational mode supports iterative refinement workflow
- [ ] #4 Direct mode remains unaffected
- [ ] #5 Tests demonstrate multi-turn conversation scenarios
- [ ] #6 Performance acceptable with conversation history (no significant slowdown)
<!-- AC:END -->
