---
id: task-10
title: Add Visual Regression Testing with pytest-image-snapshot
status: Done
assignee:
  - '@developer'
created_date: '2025-11-06 16:12'
updated_date: '2025-11-06 16:20'
labels:
  - testing
  - visual-regression
  - quality-assurance
  - chart-generation
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Context
The POC demonstrated that pytest-image-snapshot works perfectly for testing chart visual appearance. We should implement comprehensive visual regression tests to catch any unintended changes to chart styling, brand colors, or layout.

## Why This Matters
- Ensures brand styling (FD/BNR colors) never accidentally changes
- Catches visual regressions from matplotlib or dependency updates
- Validates that charts remain publication-ready
- Provides confidence when refactoring chart generation code

## Current POC Results
✅ Successfully tested with:
- FD bar chart with Q1-Q4 data
- BNR line chart with Jan-Apr data
- Threshold of 0.1 for minor rendering variations

## Implementation Scope

### Test Coverage Needed
1. **Brand Styles**:
   - FD bar chart
   - FD line chart
   - BNR bar chart
   - BNR line chart

2. **Edge Cases**:
   - Single data point
   - Large datasets (10+ points)
   - Decimal values with commas (4,1 → 4.1)
   - Very small values (0.01, 0.001)
   - Very large values (10000+)
   - Negative values (if supported)

3. **Output Formats**:
   - PNG format (primary)
   - SVG format (if visual comparison possible)

### Technical Implementation

**Dependencies**:
```toml
# Already installed in POC
pytest-image-snapshot>=0.4.5
Pillow  # Required by pytest-image-snapshot
```

**Test Structure**:
```python
# tests/test_visual_regression.py
import json
from PIL import Image
from graph_agent.tools import matplotlib_chart_generator

def test_fd_bar_chart_standard(image_snapshot):
    """FD bar chart with standard quarterly data."""
    data = json.dumps([
        {"label": "Q1", "value": 100},
        {"label": "Q2", "value": 120},
        {"label": "Q3", "value": 110},
        {"label": "Q4", "value": 130}
    ])
    filepath = matplotlib_chart_generator(data, "bar", "fd", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/fd_bar_standard.png", threshold=0.1)
```

**Snapshot Management**:
- Store snapshots in `tests/snapshots/` directory
- Add snapshots to git for baseline comparison
- Update with `pytest --image-snapshot-update` when intentional changes made
- Use descriptive names: `{brand}_{type}_{scenario}.png`

**pytest.ini Configuration**:
```ini
[tool:pytest]
# Save diff images on failure for debugging
addopts = --image-snapshot-save-diff
```

### Benefits
- Automated visual quality assurance
- Quick detection of styling regressions
- Documentation through visual baselines
- Confidence in refactoring

### Testing Strategy
1. Generate baseline snapshots for all scenarios
2. Run visual regression tests in CI/CD pipeline
3. Review and update snapshots when styling intentionally changes
4. Use `--image-snapshot-save-diff` to debug failures

## Example Usage
```bash
# Run visual regression tests
uv run python -m pytest tests/test_visual_regression.py -v

# Update snapshots after intentional changes
uv run python -m pytest tests/test_visual_regression.py --image-snapshot-update

# Save diff images on failure
uv run python -m pytest tests/test_visual_regression.py --image-snapshot-save-diff
```

## Success Criteria
- Visual regression tests for all 4 chart type/style combinations
- Edge case coverage (single point, large datasets, decimals)
- Snapshots committed to repository
- Documentation in CLAUDE.md for running and updating snapshots
- All existing tests still pass (currently 45 tests)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Visual regression tests exist for FD bar, FD line, BNR bar, and BNR line charts
- [x] #2 Edge cases tested: single data point, large datasets (10+ points), decimal values
- [x] #3 Baseline snapshots committed to tests/snapshots/ directory
- [x] #4 Tests pass on first run and on subsequent runs (comparison works)
- [x] #5 Documentation added to CLAUDE.md for running and updating visual regression tests
- [x] #6 pytest flags documented: --image-snapshot-update and --image-snapshot-save-diff
- [x] #7 All existing 45 tests continue to pass
- [x] #8 Visual regression tests can be run independently: pytest tests/test_visual_regression.py
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Implementation Completed (2025-11-06)

### Changes Made:

1. **Created comprehensive visual regression test suite** (`tests/test_visual_regression.py`):
   - 4 standard chart tests (FD bar, FD line, BNR bar, BNR line)
   - 7 edge case tests (single point, large dataset, decimals, small values, large values, mixed ranges, zero value)
   - Total: 11 visual regression tests
   - All tests use threshold of 0.1 (10% tolerance for minor rendering variations)

2. **Added dependencies** (`pyproject.toml`):
   - pytest-image-snapshot>=0.4.5
   - pillow>=10.0.0

3. **Generated baseline snapshots** (`tests/snapshots/`):
   - 11 PNG snapshots committed to repository
   - Snapshots serve as visual baseline for comparison
   - File sizes range from 37K to 133K

4. **Updated .gitignore**:
   - Added `tests/snapshots/*-diff.png` to ignore diff images generated during debugging

5. **Updated CLAUDE.md documentation**:
   - Added visual regression commands to Testing section
   - Created dedicated "Visual Regression Testing" subsection with:
     - How it works explanation
     - Update command: `--image-snapshot-update`
     - Debug command: `--image-snapshot-save-diff`
     - Coverage details
     - Important notes about snapshots and thresholds

### Test Results:
✅ **All 56 tests passing** (45 existing + 11 new visual regression tests)

### Quality Gates Passed:
✅ Visual regression tests for all 4 chart type/style combinations
✅ Edge case coverage implemented
✅ Baseline snapshots generated and verified
✅ Tests pass on first run and subsequent runs (comparison working)
✅ Documentation complete in CLAUDE.md
✅ All existing tests continue to pass
✅ Visual regression tests can be run independently

### Files Created:
- tests/test_visual_regression.py (comprehensive test suite)
- tests/snapshots/*.png (11 baseline snapshots)

### Files Modified:
- pyproject.toml (added dependencies)
- .gitignore (added diff image exclusion)
- CLAUDE.md (added visual regression documentation)

### Usage Examples:
```bash
# Run visual regression tests
uv run python -m pytest tests/test_visual_regression.py -v

# Update snapshots after styling changes
uv run python -m pytest tests/test_visual_regression.py --image-snapshot-update

# Debug failures with diff images
uv run python -m pytest tests/test_visual_regression.py --image-snapshot-save-diff
```

**Status**: Task-10 complete! Visual regression testing fully implemented and documented.
<!-- SECTION:NOTES:END -->
