"""Visual regression tests for chart generation using pytest-image-snapshot.

These tests ensure that chart styling, brand colors, and layout remain consistent.
Any visual changes to charts will cause these tests to fail, preventing unintended
regressions from matplotlib updates or code changes.

To update snapshots after intentional styling changes:
    pytest tests/test_visual_regression.py --image-snapshot-update

To save diff images on failure:
    pytest tests/test_visual_regression.py --image-snapshot-save-diff
"""

import json
from PIL import Image
from graph_agent.tools import matplotlib_chart_generator


# ============================================================================
# Standard Chart Tests (4 combinations: FD/BNR x bar/line)
# ============================================================================

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


def test_fd_line_chart_standard(image_snapshot):
    """FD line chart with standard quarterly data."""
    data = json.dumps([
        {"label": "Q1", "value": 100},
        {"label": "Q2", "value": 120},
        {"label": "Q3", "value": 110},
        {"label": "Q4", "value": 130}
    ])

    filepath = matplotlib_chart_generator(data, "line", "fd", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/fd_line_standard.png", threshold=0.1)


def test_bnr_bar_chart_standard(image_snapshot):
    """BNR bar chart with standard monthly data."""
    data = json.dumps([
        {"label": "Jan", "value": 10},
        {"label": "Feb", "value": 20},
        {"label": "Mar", "value": 15},
        {"label": "Apr", "value": 25}
    ])

    filepath = matplotlib_chart_generator(data, "bar", "bnr", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/bnr_bar_standard.png", threshold=0.1)


def test_bnr_line_chart_standard(image_snapshot):
    """BNR line chart with standard monthly data."""
    data = json.dumps([
        {"label": "Jan", "value": 10},
        {"label": "Feb", "value": 20},
        {"label": "Mar", "value": 15},
        {"label": "Apr", "value": 25}
    ])

    filepath = matplotlib_chart_generator(data, "line", "bnr", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/bnr_line_standard.png", threshold=0.1)


# ============================================================================
# Edge Case Tests
# ============================================================================

def test_single_data_point(image_snapshot):
    """Chart with only one data point."""
    data = json.dumps([
        {"label": "Single", "value": 42}
    ])

    filepath = matplotlib_chart_generator(data, "bar", "fd", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/single_point.png", threshold=0.1)


def test_large_dataset(image_snapshot):
    """Chart with 12 data points (monthly data for a year)."""
    data = json.dumps([
        {"label": "Jan", "value": 100},
        {"label": "Feb", "value": 105},
        {"label": "Mar", "value": 110},
        {"label": "Apr", "value": 115},
        {"label": "May", "value": 120},
        {"label": "Jun", "value": 125},
        {"label": "Jul", "value": 130},
        {"label": "Aug", "value": 128},
        {"label": "Sep", "value": 122},
        {"label": "Oct", "value": 118},
        {"label": "Nov", "value": 112},
        {"label": "Dec", "value": 108}
    ])

    filepath = matplotlib_chart_generator(data, "line", "fd", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/large_dataset.png", threshold=0.1)


def test_decimal_values(image_snapshot):
    """Chart with decimal values (like Dutch comma decimals: 4,1 → 4.1)."""
    data = json.dumps([
        {"label": "Mon", "value": 4.1},
        {"label": "Tue", "value": 4.2},
        {"label": "Wed", "value": 4.4},
        {"label": "Thu", "value": 4.7},
        {"label": "Fri", "value": 4.2}
    ])

    filepath = matplotlib_chart_generator(data, "bar", "bnr", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/decimal_values.png", threshold=0.1)


def test_very_small_values(image_snapshot):
    """Chart with very small decimal values."""
    data = json.dumps([
        {"label": "A", "value": 0.01},
        {"label": "B", "value": 0.02},
        {"label": "C", "value": 0.015},
        {"label": "D", "value": 0.025}
    ])

    filepath = matplotlib_chart_generator(data, "line", "fd", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/small_values.png", threshold=0.1)


def test_very_large_values(image_snapshot):
    """Chart with very large values (thousands)."""
    data = json.dumps([
        {"label": "Q1", "value": 10000},
        {"label": "Q2", "value": 15000},
        {"label": "Q3", "value": 12500},
        {"label": "Q4", "value": 18000}
    ])

    filepath = matplotlib_chart_generator(data, "bar", "bnr", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/large_values.png", threshold=0.1)


def test_mixed_value_ranges(image_snapshot):
    """Chart with mixed small and large values to test scaling."""
    data = json.dumps([
        {"label": "A", "value": 10},
        {"label": "B", "value": 100},
        {"label": "C", "value": 50},
        {"label": "D", "value": 200}
    ])

    filepath = matplotlib_chart_generator(data, "line", "fd", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/mixed_ranges.png", threshold=0.1)


def test_zero_value(image_snapshot):
    """Chart including zero value."""
    data = json.dumps([
        {"label": "A", "value": 10},
        {"label": "B", "value": 0},
        {"label": "C", "value": 15},
        {"label": "D", "value": 5}
    ])

    filepath = matplotlib_chart_generator(data, "bar", "fd", "png")
    image = Image.open(filepath)
    image_snapshot(image, "tests/snapshots/zero_value.png", threshold=0.1)
