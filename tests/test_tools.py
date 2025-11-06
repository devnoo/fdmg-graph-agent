"""Tests for chart generation tools."""

import json
import os


def test_matplotlib_chart_generator_creates_file():
    """Test that matplotlib_chart_generator creates a chart file."""
    from graph_agent.tools import matplotlib_chart_generator

    # Prepare test data
    data = json.dumps([{"label": "A", "value": 10}, {"label": "B", "value": 20}])

    # Generate chart
    filepath = matplotlib_chart_generator(
        data=data, chart_type="bar", style="fd", format="png"
    )

    # Verify file was created
    assert os.path.exists(filepath)
    assert filepath.endswith(".png")
    assert "chart-" in filepath

    # Cleanup
    os.remove(filepath)


def test_matplotlib_chart_generator_bar_chart():
    """Test bar chart generation."""
    from graph_agent.tools import matplotlib_chart_generator

    data = json.dumps([{"label": "Q1", "value": 100}, {"label": "Q2", "value": 150}])
    filepath = matplotlib_chart_generator(
        data=data, chart_type="bar", style="fd", format="png"
    )

    assert os.path.exists(filepath)
    os.remove(filepath)


def test_matplotlib_chart_generator_line_chart():
    """Test line chart generation."""
    from graph_agent.tools import matplotlib_chart_generator

    data = json.dumps([{"label": "Mon", "value": 10}, {"label": "Tue", "value": 20}])
    filepath = matplotlib_chart_generator(
        data=data, chart_type="line", style="bnr", format="png"
    )

    assert os.path.exists(filepath)
    os.remove(filepath)


def test_matplotlib_chart_generator_fd_style():
    """Test FD brand styling."""
    from graph_agent.tools import matplotlib_chart_generator

    data = json.dumps([{"label": "A", "value": 10}])
    filepath = matplotlib_chart_generator(
        data=data, chart_type="bar", style="fd", format="png"
    )

    # File should be created with FD colors
    assert os.path.exists(filepath)
    os.remove(filepath)


def test_matplotlib_chart_generator_bnr_style():
    """Test BNR brand styling."""
    from graph_agent.tools import matplotlib_chart_generator

    data = json.dumps([{"label": "A", "value": 10}])
    filepath = matplotlib_chart_generator(
        data=data, chart_type="bar", style="bnr", format="png"
    )

    # File should be created with BNR colors
    assert os.path.exists(filepath)
    os.remove(filepath)


def test_matplotlib_chart_generator_png_format():
    """Test PNG output format."""
    from graph_agent.tools import matplotlib_chart_generator

    data = json.dumps([{"label": "A", "value": 10}])
    filepath = matplotlib_chart_generator(
        data=data, chart_type="bar", style="fd", format="png"
    )

    assert filepath.endswith(".png")
    assert os.path.exists(filepath)
    os.remove(filepath)


def test_matplotlib_chart_generator_svg_format():
    """Test SVG output format."""
    from graph_agent.tools import matplotlib_chart_generator

    data = json.dumps([{"label": "A", "value": 10}])
    filepath = matplotlib_chart_generator(
        data=data, chart_type="bar", style="fd", format="svg"
    )

    assert filepath.endswith(".svg")
    assert os.path.exists(filepath)
    os.remove(filepath)


def test_matplotlib_chart_generator_timestamp_filename():
    """Test that filename includes timestamp."""
    from graph_agent.tools import matplotlib_chart_generator
    import re

    data = json.dumps([{"label": "A", "value": 10}])
    filepath = matplotlib_chart_generator(
        data=data, chart_type="bar", style="fd", format="png"
    )

    # Check filename format: chart-YYYYMMDDHHmmss.ext
    filename = os.path.basename(filepath)
    assert re.match(r"chart-\d{14}\.(png|svg)", filename)

    os.remove(filepath)


def test_matplotlib_chart_generator_absolute_path():
    """Test that returned path is absolute."""
    from graph_agent.tools import matplotlib_chart_generator

    data = json.dumps([{"label": "A", "value": 10}])
    filepath = matplotlib_chart_generator(
        data=data, chart_type="bar", style="fd", format="png"
    )

    assert os.path.isabs(filepath)
    os.remove(filepath)


def test_brand_colors_constant():
    """Test that BRAND_COLORS constant exists with correct values."""
    from graph_agent.tools import BRAND_COLORS

    assert "fd" in BRAND_COLORS
    assert "bnr" in BRAND_COLORS

    # FD colors
    assert BRAND_COLORS["fd"]["primary"] == "#379596"
    assert BRAND_COLORS["fd"]["content"] == "#191919"
    assert BRAND_COLORS["fd"]["background"] == "#ffeadb"

    # BNR colors
    assert BRAND_COLORS["bnr"]["primary"] == "#ffd200"
    assert BRAND_COLORS["bnr"]["content"] == "#000"
    assert BRAND_COLORS["bnr"]["background"] == "#fff"
