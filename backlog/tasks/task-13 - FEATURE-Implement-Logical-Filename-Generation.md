---
id: task-13
title: 'FEATURE: Implement Logical Filename Generation'
status: Done
assignee: []
created_date: '2025-11-07 07:07'
updated_date: '2025-11-07 11:19'
labels:
  - enhancement
  - requirements
  - critical
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

Generated chart filenames use generic `chart-[timestamp].[ext]` format instead of semantic `[logical_name]-[timestamp].[ext]` format as specified in requirements.

**Current Behavior:**
- `chart-20251107072658.png`
- `chart-20251107075226.png`

**Required Behavior (PRD Section 4.1):**
- `studieschuld-20251107072658.png`
- `quarterly-20251107075226.png`
- `cities-20251107080000.svg`

## Requirements Reference

**PRD Section 4.1 - File Output Logic:**
> The filename format **must** be: `[logical_name]-[timestamp].[ext]` (e.g., `studieschuld-20251106110500.png`). The `logical_name` should be a one- or two-word summary derived from the prompt.

## Implementation Approach

### Option 1: LLM-Based Name Extraction (Recommended)
Use Gemini to extract a logical 1-2 word name from the user's prompt/data.

**Example prompts → logical names:**
- "Maak een grafiek van studieschuld data" → `studieschuld`
- "Q1=100, Q2=150, Q3=200, Q4=180" → `quarterly`
- "Amsterdam=500, Rotterdam=400, Utrecht=300" → `cities` or `netherlands`
- "Create a bar chart for monthly sales" → `sales` or `monthly`

**Pros:**
- Intelligent, context-aware naming
- Handles Dutch and English equally well
- Can extract meaning from natural language

**Cons:**
- Requires additional LLM call
- Slight performance overhead

### Option 2: Rule-Based Extraction
Extract first meaningful word from prompt or first label from data.

**Pros:**
- Fast, no LLM required
- Deterministic

**Cons:**
- Less intelligent
- May produce poor names (e.g., "make" from "make a chart...")

### Recommended: Hybrid Approach
1. Try LLM extraction with simple prompt: "Extract a 1-2 word filename prefix from: {user_prompt}. Return only the prefix, no explanation."
2. Fallback to "chart" if LLM fails or returns empty

## Where to Implement

**Option A:** In `generate_chart_tool` node
- Extract logical name from `state["messages"][-1].content` (user's last message)
- Pass to `matplotlib_chart_generator()`

**Option B:** In `matplotlib_chart_generator()` function
- Accept optional `logical_name` parameter
- Generate filename: `{logical_name}-{timestamp}.{format}` if provided
- Fallback to `chart-{timestamp}.{format}` if None

**Recommended:** Option A (in node) for better separation of concerns

## Filename Sanitization

Ensure logical names are filesystem-safe:
- Lowercase only
- Replace spaces with hyphens
- Remove special characters (keep only a-z, 0-9, hyphen)
- Max length: 20 characters

**Examples:**
- "Café sales" → `cafe-sales`
- "Q1/Q2 Results" → `q1-q2-results`
- "Year-over-year growth rate" → `year-over-year-gro` (truncated)

## Test Cases

- [ ] Dutch prompt: "studieschuld data" → `studieschuld-TIMESTAMP.png`
- [ ] English prompt: "quarterly sales" → `quarterly-TIMESTAMP.png`
- [ ] Data-only: "A=10, B=20" → `data-TIMESTAMP.png` or similar
- [ ] Excel file: "fdmg_categorical_example.xlsx" → extract from filename or sheet name
- [ ] Special characters sanitized correctly
- [ ] Fallback to "chart" when extraction fails

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 All chart files use [logical_name]-[timestamp].[ext] format
- [x] #2 Logical names are meaningful 1-2 word summaries
- [x] #3 Names are filesystem-safe (lowercase, alphanumeric, hyphens only)
- [x] #4 Dutch and English prompts both produce appropriate names
- [x] #5 Excel files extract names from filename or content
- [x] #6 Fallback to 'chart' prefix when extraction fails
- [x] #7 All existing tests pass with updated filename format
<!-- SECTION:DESCRIPTION:END -->
<!-- AC:END -->
