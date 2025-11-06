"""Acceptance tests for CLI error handling and validation."""

import os
from unittest.mock import Mock, patch
from click.testing import CliRunner
from graph_agent.cli import main


# ============================================================================
# INVALID JSON DETECTION TESTS (6 tests)
# ============================================================================


def test_cli_rejects_plain_text_response():
    """
    Test that CLI exits with error when LLM returns plain text instead of JSON.

    Acceptance Criteria:
    - Exit code 1
    - No chart file generated
    - Error message mentions JSON parsing failure
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        # Intent detection: make_chart
        intent_response = Mock()
        intent_response.content = "make_chart"

        # Data extraction: returns plain text (not JSON)
        extract_response = Mock()
        extract_response.content = "This is plain text, not JSON"

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10, B=20", "--type", "bar"])

        # Verify error exit code
        assert result.exit_code == 1

        # Verify error message mentions JSON
        assert "JSON" in result.output or "parse" in result.output.lower()

        # Verify no chart files were created
        output_files = [f for f in os.listdir(".") if f.startswith("chart-")]
        assert len(output_files) == 0


def test_cli_rejects_malformed_json():
    """
    Test that CLI rejects malformed JSON (missing brackets, invalid syntax).
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Malformed JSON: missing closing bracket
        extract_response = Mock()
        extract_response.content = '[{"label": "A", "value": 10'

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10", "--type", "bar"])

        assert result.exit_code == 1
        assert "JSON" in result.output or "parse" in result.output.lower()


def test_cli_rejects_json_object_instead_of_array():
    """
    Test that CLI rejects JSON object when array is expected.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Valid JSON but wrong structure (object instead of array)
        extract_response = Mock()
        extract_response.content = '{"label": "A", "value": 10}'

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10", "--type", "bar"])

        assert result.exit_code == 1
        assert "array" in result.output.lower() or "format" in result.output.lower()


def test_cli_rejects_json_with_missing_label_field():
    """
    Test that CLI rejects JSON array with objects missing 'label' field.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Missing 'label' field
        extract_response = Mock()
        extract_response.content = '[{"value": 10}, {"value": 20}]'

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10, B=20", "--type", "bar"])

        assert result.exit_code == 1
        assert "label" in result.output.lower()


def test_cli_rejects_json_with_missing_value_field():
    """
    Test that CLI rejects JSON array with objects missing 'value' field.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Missing 'value' field
        extract_response = Mock()
        extract_response.content = '[{"label": "A"}, {"label": "B"}]'

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10, B=20", "--type", "bar"])

        assert result.exit_code == 1
        assert "value" in result.output.lower()


def test_cli_rejects_json_with_wrong_value_type():
    """
    Test that CLI rejects JSON where value is not a number.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Value is string instead of number (provide 2 points to pass minimum data check)
        extract_response = Mock()
        extract_response.content = (
            '[{"label": "A", "value": "ten"}, {"label": "B", "value": 20}]'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10", "--type", "bar"])

        assert result.exit_code == 1
        assert "number" in result.output.lower() or "numeric" in result.output.lower()


# ============================================================================
# INSUFFICIENT DATA DETECTION TESTS (4 tests)
# ============================================================================


def test_cli_rejects_empty_json_array():
    """
    Test that CLI rejects empty JSON array (no data points).
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Empty array
        extract_response = Mock()
        extract_response.content = "[]"

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["create chart", "--type", "bar"])

        assert result.exit_code == 1
        assert "data" in result.output.lower()


def test_cli_rejects_single_data_point():
    """
    Test that CLI requires at least 2 data points for meaningful chart.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Only one data point
        extract_response = Mock()
        extract_response.content = '[{"label": "A", "value": 10}]'

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10", "--type", "bar"])

        assert result.exit_code == 1
        assert (
            "at least 2" in result.output.lower()
            or "insufficient" in result.output.lower()
        )


def test_cli_rejects_empty_label():
    """
    Test that CLI rejects data points with empty label strings.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Empty label
        extract_response = Mock()
        extract_response.content = (
            '[{"label": "", "value": 10}, {"label": "B", "value": 20}]'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["=10, B=20", "--type", "bar"])

        assert result.exit_code == 1
        assert "label" in result.output.lower() and "empty" in result.output.lower()


def test_cli_rejects_whitespace_only_label():
    """
    Test that CLI rejects data points with whitespace-only labels.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Whitespace-only label
        extract_response = Mock()
        extract_response.content = (
            '[{"label": "   ", "value": 10}, {"label": "B", "value": 20}]'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["   =10, B=20", "--type", "bar"])

        assert result.exit_code == 1
        assert "label" in result.output.lower()


# ============================================================================
# DATA QUALITY VALIDATION TESTS (3 tests)
# ============================================================================


def test_cli_rejects_all_zero_values():
    """
    Test that CLI rejects data where all values are zero (invisible chart).
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # All zero values
        extract_response = Mock()
        extract_response.content = (
            '[{"label": "A", "value": 0}, {"label": "B", "value": 0}]'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=0, B=0", "--type", "bar"])

        assert result.exit_code == 1
        assert "zero" in result.output.lower() or "meaningful" in result.output.lower()


def test_cli_rejects_nan_values():
    """
    Test that CLI rejects NaN (Not a Number) values.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # NaN value (represented as null in JSON)
        extract_response = Mock()
        extract_response.content = (
            '[{"label": "A", "value": null}, {"label": "B", "value": 20}]'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=NaN, B=20", "--type", "bar"])

        assert result.exit_code == 1
        assert "invalid" in result.output.lower() or "value" in result.output.lower()


def test_cli_rejects_infinity_values():
    """
    Test that CLI rejects Infinity values.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Infinity value (JSON doesn't support, but could be string)
        extract_response = Mock()
        extract_response.content = (
            '[{"label": "A", "value": 10}, {"label": "B", "value": "Infinity"}]'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10, B=Infinity", "--type", "bar"])

        assert result.exit_code == 1
        assert "invalid" in result.output.lower() or "value" in result.output.lower()


# ============================================================================
# SUCCESS CASES (3 tests)
# ============================================================================


def test_cli_succeeds_with_valid_integer_data():
    """
    Test that CLI successfully generates chart with valid integer data.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Valid data
        extract_response = Mock()
        extract_response.content = (
            '[{"label": "A", "value": 10}, {"label": "B", "value": 20}]'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10, B=20", "--type", "bar"])

        # Success exit code
        assert result.exit_code == 0

        # Verify chart was created
        assert "Chart saved:" in result.output

        # Cleanup: remove generated chart
        import re

        match = re.search(r"chart-[\w-]+\.png", result.output)
        if match:
            filepath = match.group(0)
            if os.path.exists(filepath):
                os.remove(filepath)


def test_cli_succeeds_with_valid_float_data():
    """
    Test that CLI successfully generates chart with valid float data.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Valid float data
        extract_response = Mock()
        extract_response.content = (
            '[{"label": "Mon", "value": 4.5}, {"label": "Tue", "value": 3.2}]'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["Mon=4.5, Tue=3.2", "--type", "bar"])

        assert result.exit_code == 0
        assert "Chart saved:" in result.output

        # Cleanup
        import re

        match = re.search(r"chart-[\w-]+\.png", result.output)
        if match:
            filepath = match.group(0)
            if os.path.exists(filepath):
                os.remove(filepath)


def test_cli_succeeds_with_mixed_positive_negative_values():
    """
    Test that CLI successfully handles mixed positive and negative values.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Mixed positive/negative
        extract_response = Mock()
        extract_response.content = (
            '[{"label": "Profit", "value": 100}, {"label": "Loss", "value": -50}]'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["Profit=100, Loss=-50", "--type", "bar"])

        assert result.exit_code == 0
        assert "Chart saved:" in result.output

        # Cleanup
        import re

        match = re.search(r"chart-[\w-]+\.png", result.output)
        if match:
            filepath = match.group(0)
            if os.path.exists(filepath):
                os.remove(filepath)


# ============================================================================
# ERROR MESSAGE QUALITY TESTS (2 tests)
# ============================================================================


def test_error_messages_are_actionable():
    """
    Test that error messages provide clear guidance on what went wrong.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Empty array
        extract_response = Mock()
        extract_response.content = "[]"

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["make chart", "--type", "bar"])

        assert result.exit_code == 1

        # Error message should be specific and actionable
        output_lower = result.output.lower()
        assert "error" in output_lower or "failed" in output_lower
        # Should explain what the problem is
        assert "data" in output_lower or "extract" in output_lower


def test_error_messages_avoid_technical_jargon():
    """
    Test that error messages are user-friendly and avoid implementation details.
    """
    runner = CliRunner()

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        intent_response = Mock()
        intent_response.content = "make_chart"

        # Malformed JSON
        extract_response = Mock()
        extract_response.content = "not json"

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        result = runner.invoke(main, ["A=10", "--type", "bar"])

        assert result.exit_code == 1

        # Should avoid technical terms like "JSONDecodeError", "stack trace", etc.
        output_lower = result.output.lower()
        assert "jsondecode" not in output_lower
        assert "traceback" not in output_lower
        assert "exception" not in output_lower
