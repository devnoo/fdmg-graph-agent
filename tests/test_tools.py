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


# Tests for parse_excel_a1 function


def test_parse_excel_a1_simple_file():
    """Test parsing simple Excel file with headers."""
    import json
    from pathlib import Path
    from graph_agent.tools import parse_excel_a1

    # Get absolute path to test fixture
    test_file = Path(__file__).parent / "fixtures" / "simple.xlsx"

    # Parse the test file
    result = parse_excel_a1(str(test_file))

    # Verify JSON structure
    data = json.loads(result)
    assert len(data) == 4
    assert data[0] == {"label": "Q1", "value": 120}
    assert data[1] == {"label": "Q2", "value": 150}
    assert data[2] == {"label": "Q3", "value": 140}
    assert data[3] == {"label": "Q4", "value": 180}


def test_parse_excel_a1_multi_sheet():
    """Test parsing multi-sheet file (uses first sheet with data)."""
    import json
    from pathlib import Path
    from graph_agent.tools import parse_excel_a1

    # Get absolute path to test fixture
    test_file = Path(__file__).parent / "fixtures" / "multi_sheet.xlsx"

    # Parse the test file (data is in second sheet)
    result = parse_excel_a1(str(test_file))

    # Verify it found and parsed the Sales sheet
    data = json.loads(result)
    assert len(data) == 3
    assert data[0] == {"label": "Jan", "value": 100}
    assert data[1] == {"label": "Feb", "value": 120}
    assert data[2] == {"label": "Mar", "value": 110}


def test_parse_excel_a1_decimal_values():
    """Test parsing file with decimal values."""
    import json
    from pathlib import Path
    from graph_agent.tools import parse_excel_a1

    # Get absolute path to test fixture
    test_file = Path(__file__).parent / "fixtures" / "decimals.xlsx"

    result = parse_excel_a1(str(test_file))

    data = json.loads(result)
    assert len(data) == 4
    assert data[0] == {"label": "2020", "value": 25.5}
    assert data[1] == {"label": "2021", "value": 26.8}
    assert data[2] == {"label": "2022", "value": 27.3}
    assert data[3] == {"label": "2023", "value": 29.1}


def test_parse_excel_a1_file_not_found():
    """Test error handling for missing file."""
    from graph_agent.tools import parse_excel_a1
    import pytest

    with pytest.raises(ValueError) as excinfo:
        parse_excel_a1("nonexistent.xlsx")

    assert "Could not find file" in str(excinfo.value)


def test_parse_excel_a1_invalid_format():
    """Test error handling for invalid file format."""
    from graph_agent.tools import parse_excel_a1
    import pytest
    import tempfile

    # Create a temporary non-Excel file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        temp_path = f.name
        f.write(b"Not an Excel file")

    try:
        with pytest.raises(ValueError) as excinfo:
            parse_excel_a1(temp_path)
        assert "must be .xlsx or .xls format" in str(excinfo.value)
    finally:
        os.remove(temp_path)


def test_parse_excel_a1_absolute_path():
    """Test that absolute paths work correctly."""
    import json
    from graph_agent.tools import parse_excel_a1
    from pathlib import Path

    # Use absolute path
    test_file = Path(__file__).parent / "fixtures" / "simple.xlsx"
    abs_path = test_file.resolve()

    result = parse_excel_a1(str(abs_path))

    # Verify it parsed successfully
    data = json.loads(result)
    assert len(data) == 4


# Tests for custom filename handling (Story 9)


def test_matplotlib_chart_generator_custom_filename_with_extension():
    """Test custom filename with extension."""
    from graph_agent.tools import matplotlib_chart_generator
    from pathlib import Path

    data = json.dumps([{"label": "A", "value": 10}])
    custom_name = "my_custom_chart.png"

    filepath = matplotlib_chart_generator(
        data=data,
        chart_type="bar",
        style="fd",
        format="png",
        output_filename=custom_name
    )

    # Verify custom filename was used
    assert Path(filepath).name == custom_name
    assert os.path.exists(filepath)

    # Cleanup
    os.remove(filepath)


def test_matplotlib_chart_generator_custom_filename_without_extension():
    """Test custom filename without extension - should add appropriate extension."""
    from graph_agent.tools import matplotlib_chart_generator
    from pathlib import Path

    data = json.dumps([{"label": "A", "value": 10}])
    custom_name = "my_chart_no_ext"

    filepath = matplotlib_chart_generator(
        data=data,
        chart_type="bar",
        style="fd",
        format="png",
        output_filename=custom_name
    )

    # Verify extension was added
    assert Path(filepath).name == "my_chart_no_ext.png"
    assert os.path.exists(filepath)

    # Cleanup
    os.remove(filepath)


def test_matplotlib_chart_generator_custom_filename_with_subdirectory():
    """Test custom filename with subdirectory - should create directory."""
    from graph_agent.tools import matplotlib_chart_generator
    from pathlib import Path
    import shutil

    data = json.dumps([{"label": "A", "value": 10}])
    custom_name = "test_charts/subdir/chart.png"

    filepath = matplotlib_chart_generator(
        data=data,
        chart_type="bar",
        style="fd",
        format="png",
        output_filename=custom_name
    )

    # Verify directory was created and file exists
    assert os.path.exists(filepath)
    assert "test_charts" in filepath
    assert "subdir" in filepath

    # Cleanup - remove entire test_charts directory
    base_dir = Path.cwd() / "test_charts"
    if base_dir.exists():
        shutil.rmtree(base_dir)


def test_matplotlib_chart_generator_custom_filename_svg_format():
    """Test custom filename with SVG format."""
    from graph_agent.tools import matplotlib_chart_generator
    from pathlib import Path

    data = json.dumps([{"label": "A", "value": 10}])
    custom_name = "my_svg_chart.svg"

    filepath = matplotlib_chart_generator(
        data=data,
        chart_type="line",
        style="bnr",
        format="svg",
        output_filename=custom_name
    )

    # Verify custom filename and format
    assert Path(filepath).name == custom_name
    assert filepath.endswith(".svg")
    assert os.path.exists(filepath)

    # Cleanup
    os.remove(filepath)


def test_matplotlib_chart_generator_custom_filename_absolute_path():
    """Test custom filename with absolute path."""
    from graph_agent.tools import matplotlib_chart_generator
    from pathlib import Path
    import tempfile

    data = json.dumps([{"label": "A", "value": 10}])

    # Create temp directory and specify absolute path
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_name = os.path.join(tmpdir, "absolute_chart.png")

        filepath = matplotlib_chart_generator(
            data=data,
            chart_type="bar",
            style="fd",
            format="png",
            output_filename=custom_name
        )

        # Verify absolute path was used correctly
        assert filepath == custom_name
        assert os.path.exists(filepath)
        # File will be cleaned up automatically with tmpdir


def test_matplotlib_chart_generator_extension_mismatch_warning():
    """Test filename with extension mismatch (should use filename as-is with warning)."""
    from graph_agent.tools import matplotlib_chart_generator
    from pathlib import Path

    data = json.dumps([{"label": "A", "value": 10}])
    # Request PNG format but provide .svg extension in filename
    custom_name = "mismatch_chart.svg"

    filepath = matplotlib_chart_generator(
        data=data,
        chart_type="bar",
        style="fd",
        format="png",  # Format is PNG
        output_filename=custom_name  # But filename has .svg
    )

    # Should use filename as provided (with warning logged)
    assert Path(filepath).name == custom_name
    assert filepath.endswith(".svg")
    assert os.path.exists(filepath)

    # Cleanup
    os.remove(filepath)


def test_sanitize_filename_basic():
    """Test basic filename sanitization."""
    from graph_agent.tools import sanitize_filename

    assert sanitize_filename("Café sales") == "cafe-sales"
    assert sanitize_filename("Q1/Q2 Results") == "q1-q2-results"
    assert sanitize_filename("Monthly Revenue") == "monthly-revenue"
    assert sanitize_filename("Year_over_year growth") == "year-over-year-growt"  # Truncated to 20 chars


def test_sanitize_filename_special_characters():
    """Test sanitization removes special characters."""
    from graph_agent.tools import sanitize_filename

    assert sanitize_filename("Data (2024)") == "data-2024"
    assert sanitize_filename("Sales & Marketing") == "sales-marketing"
    assert sanitize_filename("Q1@Q2#Q3") == "q1q2q3"


def test_sanitize_filename_length_truncation():
    """Test that long names are truncated to max_length."""
    from graph_agent.tools import sanitize_filename

    result = sanitize_filename("This is a very long filename that should be truncated", max_length=20)
    assert len(result) <= 20
    assert result == "this-is-a-very-long"  # 19 chars

    result = sanitize_filename("Year-over-year growth rate analysis", max_length=20)
    assert len(result) <= 20
    # "year-over-year-growth-rate-analysis" becomes "year-over-year-gro" after truncation and trimming
    assert result == "year-over-year-growt"  # 20 chars


def test_sanitize_filename_empty_fallback():
    """Test that empty strings fallback to 'chart'."""
    from graph_agent.tools import sanitize_filename

    assert sanitize_filename("") == "chart"
    assert sanitize_filename("   ") == "chart"
    assert sanitize_filename("@#$%") == "chart"


def test_extract_logical_name_dutch():
    """Test extracting logical name from Dutch prompt."""
    from unittest.mock import Mock
    from graph_agent.tools import extract_logical_name

    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "studieschuld"
    mock_llm.invoke.return_value = mock_response

    result = extract_logical_name("Maak een grafiek van studieschuld data", mock_llm)
    assert result == "studieschuld"
    assert mock_llm.invoke.called


def test_extract_logical_name_english():
    """Test extracting logical name from English prompt."""
    from unittest.mock import Mock
    from graph_agent.tools import extract_logical_name

    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "sales"
    mock_llm.invoke.return_value = mock_response

    result = extract_logical_name("Create a bar chart for monthly sales", mock_llm)
    assert result == "sales"


def test_extract_logical_name_quarterly_data():
    """Test extracting logical name from quarterly data pattern."""
    from unittest.mock import Mock
    from graph_agent.tools import extract_logical_name

    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "quarterly"
    mock_llm.invoke.return_value = mock_response

    result = extract_logical_name("Q1=100, Q2=150, Q3=200, Q4=180", mock_llm)
    assert result == "quarterly"


def test_extract_logical_name_fallback_on_error():
    """Test fallback to 'chart' when LLM fails."""
    from unittest.mock import Mock
    from graph_agent.tools import extract_logical_name

    mock_llm = Mock()
    mock_llm.invoke.side_effect = Exception("LLM error")

    result = extract_logical_name("Some prompt", mock_llm)
    assert result == "chart"


def test_extract_logical_name_sanitizes_output():
    """Test that extracted name is sanitized."""
    from unittest.mock import Mock
    from graph_agent.tools import extract_logical_name

    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "Café & Sales"  # LLM returned unsanitized name
    mock_llm.invoke.return_value = mock_response

    result = extract_logical_name("Some prompt", mock_llm)
    assert result == "cafe-sales"


def test_logical_filename_in_chart_generation():
    """Test that chart generation uses logical filename format."""
    import json
    import os
    from unittest.mock import patch, Mock
    from graph_agent.agent import create_graph
    from graph_agent.state import GraphState

    # Mock LLM responses
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        with patch("graph_agent.tools.extract_logical_name", return_value="test-data"):
            mock_llm = Mock()

            # First call: parse_intent
            intent_response = Mock()
            intent_response.content = '{"intent": "make_chart", "has_file": false, "config_type": null, "config_value": null}'

            # Second call: extract_data
            extract_response = Mock()
            extract_response.content = (
                '{"data": [{"label": "A", "value": 10}, {"label": "B", "value": 20}], '
                '"type": null, "style": null, "format": null}'
            )

            mock_llm.invoke.side_effect = [intent_response, extract_response]
            mock_get_llm.return_value = mock_llm

            graph = create_graph()
            initial_state = GraphState(
                messages=[{"role": "user", "content": "Create a chart with A=10, B=20"}],
                interaction_mode="direct",
                intent="unknown",
                has_file=False,
                config_change=None,
                input_data=None,
                chart_request={"type": "bar", "style": "fd", "format": "png"},
                missing_params=None,
                output_filename=None,
                final_filepath=None,
                error_message=None,
            )

            result = graph.invoke(initial_state)

            # Verify chart was generated
            assert result["final_filepath"] is not None

            # Verify filename format: should be test-data-TIMESTAMP.png
            filename = os.path.basename(result["final_filepath"])
            assert filename.startswith("test-data-")
            assert filename.endswith(".png")
            assert len(filename) == len("test-data-YYYYMMDDHHMMSS.png")

            # Cleanup
            if os.path.exists(result["final_filepath"]):
                os.remove(result["final_filepath"])
