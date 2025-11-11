---
id: task-14
title: 'BUG: Dutch Chart Type Not Detected + Wrong Language Response'
status: Done
assignee: []
created_date: '2025-11-07 07:07'
updated_date: '2025-11-08 07:31'
labels:
  - bug
  - language
  - i18n
  - critical
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

When user explicitly requests "lijn grafiek" (line chart) in Dutch, the system:
1. Fails to detect that chart type was specified (asks "do you want bar or line?")
2. Responds in English instead of Dutch

**Scenario:**
```
User: "kan je een lijn grafiek genereren voor fdmg_timeseries.xlsx"
```

**Expected Behavior:**
- System detects "lijn grafiek" = line chart
- Generates line chart without asking
- All responses in Dutch

**Actual Behavior:**
- System asks: "Do you want a bar or line chart?" (in English)
- Ignores the explicit "lijn grafiek" request

## Root Causes

### Issue 1: Dutch Chart Type Keywords Not Recognized

**Location:** Likely in `extract_data` or `parse_intent` nodes

The LLM prompt for chart type detection may not include Dutch keywords like:
- "lijn grafiek" / "lijngrafiek" → line chart
- "staaf grafiek" / "staafdiagram" → bar chart
- "grafiek" → chart (generic)

### Issue 2: Language Mismatch in Response

**Location:** Ambiguity resolution or clarification prompts

When the agent asks clarifying questions, it's using English instead of detecting and matching the user's language (Dutch).

## Fix Required

### Fix 1: Add Dutch Chart Type Detection

Update LLM prompts to recognize Dutch chart type keywords:

**Dutch → English mapping:**
- "lijn" / "lijn grafiek" / "lijngrafiek" → line
- "staaf" / "staaf grafiek" / "staafdiagram" / "balk" → bar
- "diagram" / "grafiek" → generic chart

**Implementation:**
- Update `extract_data` node prompt to include Dutch examples
- OR add explicit pattern matching for Dutch keywords before LLM call

### Fix 2: Language-Aware Responses

Ensure all system responses match the user's language:

1. **Detect language** from user's last message
2. **Store language** in state (e.g., `detected_language: "nl" | "en"`)
3. **Use language** when generating:
   - Clarification questions
   - Error messages  
   - Confirmation messages

**Dutch Clarification Examples:**
- "Wil je een staafdiagram of een lijngrafiek?"
- "Welk werkblad wil je gebruiken: 'Sheet1' of 'Sheet2'?"
- "Welke stijl: FD of BNR?"

## Test Cases

### Dutch Chart Type Detection
- [ ] "lijn grafiek" → detected as line chart
- [ ] "lijngrafiek" → detected as line chart
- [ ] "staafdiagram" → detected as bar chart
- [ ] "staaf grafiek" → detected as bar chart
- [ ] "balkdiagram" → detected as bar chart
- [ ] "grafiek" without type → asks for clarification (in Dutch)

### Language Response Matching
- [ ] Dutch query → Dutch clarification questions
- [ ] Dutch query → Dutch error messages
- [ ] English query → English responses
- [ ] Mixed session: language switches with user's last message

### Integration Tests
- [ ] "kan je een lijn grafiek genereren voor data.xlsx" → generates line chart, no questions
- [ ] "maak een staafdiagram" → generates bar chart
- [ ] "genereer een grafiek voor A=10, B=20" → asks "staaf of lijn?" in Dutch

## Files to Modify

1. **`graph_agent/agent.py`:**
   - `extract_data` node: Update LLM prompt with Dutch chart type examples
   - `resolve_ambiguity` node: Detect user language and use it for questions
   - Add language detection utility function

2. **`graph_agent/state.py`:**
   - Add `detected_language: str | None` to GraphState (optional)

3. **Tests:**
   - Add Dutch chart type tests to `test_agent.py`
   - Add language matching tests

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Dutch chart type keywords detected correctly (lijn grafiek, staafdiagram, etc.)
- [x] #2 System responds in the same language as user's query (Dutch → Dutch, English → English)
- [x] #3 Explicit chart type in prompt (Dutch or English) prevents unnecessary clarification questions
- [x] #4 All clarification questions and error messages are language-aware
- [x] #5 No regression in existing English language functionality
- [x] #6 Integration tests pass for Dutch chart type detection scenarios
<!-- SECTION:DESCRIPTION:END -->
<!-- AC:END -->
