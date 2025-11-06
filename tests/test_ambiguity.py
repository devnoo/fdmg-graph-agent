"""Unit tests for ambiguity resolution functionality."""

import json
import pytest
from unittest.mock import Mock, patch
from graph_agent.state import GraphState
from graph_agent import agent


class TestIsCategoricalData:
    """Test the is_categorical_data helper function."""

    def test_categorical_data_with_generic_labels(self):
        """Test that generic labels are identified as categorical."""
        data = json.dumps([
            {"label": "A", "value": 10},
            {"label": "B", "value": 20},
            {"label": "C", "value": 30}
        ])
        assert agent.is_categorical_data(data) is True

    def test_categorical_data_with_names(self):
        """Test that names are identified as categorical."""
        data = json.dumps([
            {"label": "Alice", "value": 10},
            {"label": "Bob", "value": 20},
            {"label": "Charlie", "value": 30}
        ])
        assert agent.is_categorical_data(data) is True

    def test_time_series_with_month_names(self):
        """Test that month names are identified as time-series."""
        data = json.dumps([
            {"label": "January", "value": 10},
            {"label": "February", "value": 20},
            {"label": "March", "value": 30}
        ])
        assert agent.is_categorical_data(data) is False

    def test_time_series_with_abbreviated_months(self):
        """Test that abbreviated months are identified as time-series."""
        data = json.dumps([
            {"label": "Jan", "value": 10},
            {"label": "Feb", "value": 20},
            {"label": "Mar", "value": 30}
        ])
        assert agent.is_categorical_data(data) is False

    def test_time_series_with_quarters(self):
        """Test that quarters are identified as time-series."""
        data = json.dumps([
            {"label": "Q1", "value": 100},
            {"label": "Q2", "value": 120},
            {"label": "Q3", "value": 110}
        ])
        assert agent.is_categorical_data(data) is False

    def test_time_series_with_years(self):
        """Test that years are identified as time-series."""
        data = json.dumps([
            {"label": "2020", "value": 100},
            {"label": "2021", "value": 120},
            {"label": "2022", "value": 150}
        ])
        assert agent.is_categorical_data(data) is False

    def test_time_series_with_mixed_year_labels(self):
        """Test that labels containing years are identified as time-series."""
        data = json.dumps([
            {"label": "Jan 2024", "value": 100},
            {"label": "Feb 2024", "value": 120}
        ])
        assert agent.is_categorical_data(data) is False

    def test_invalid_json_defaults_to_categorical(self):
        """Test that invalid JSON defaults to categorical."""
        assert agent.is_categorical_data("not json") is True

    def test_empty_data_defaults_to_categorical(self):
        """Test that empty data defaults to categorical."""
        assert agent.is_categorical_data("[]") is True


class TestResolveAmbiguity:
    """Test the resolve_ambiguity node."""

    def test_categorical_data_with_no_type_or_style(self, tmp_path, monkeypatch):
        """Test that missing type and style are detected for categorical data."""
        # Use temp config directory with no defaults
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        state = GraphState(
            messages=[{"role": "user", "content": "chart: A=10, B=20"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}, {"label": "B", "value": 20}]),
            chart_request={"type": None, "style": None, "format": None},
            missing_params=None,
            final_filepath=None,
        )

        result = agent.resolve_ambiguity(state)

        assert result["missing_params"] == ["type", "style"]
        assert result["chart_request"]["format"] == "png"  # Format has fallback

    def test_time_series_data_defaults_to_line(self, tmp_path, monkeypatch):
        """Test that time-series data defaults to line chart."""
        # Use temp config directory with no defaults
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        state = GraphState(
            messages=[{"role": "user", "content": "chart with months"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([
                {"label": "Jan", "value": 10},
                {"label": "Feb", "value": 20}
            ]),
            chart_request={"type": None, "style": None, "format": None},
            missing_params=None,
            final_filepath=None,
        )

        result = agent.resolve_ambiguity(state)

        assert result["chart_request"]["type"] == "line"  # Auto-default for time-series
        assert result["missing_params"] == ["style"]  # Only style missing

    def test_explicit_params_not_marked_as_missing(self, tmp_path, monkeypatch):
        """Test that explicitly set parameters are not marked as missing."""
        # Use temp config directory with no defaults
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        state = GraphState(
            messages=[{"role": "user", "content": "bar chart, FD style: A=10, B=20"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": "bar", "style": "fd", "format": None},
            missing_params=None,
            final_filepath=None,
        )

        result = agent.resolve_ambiguity(state)

        assert result["missing_params"] is None  # Nothing missing
        assert result["chart_request"]["type"] == "bar"
        assert result["chart_request"]["style"] == "fd"
        assert result["chart_request"]["format"] == "png"  # Fallback applied

    def test_default_style_from_config(self, tmp_path, monkeypatch):
        """Test that default style from config is used."""
        # Use temp config directory with defaults
        config_dir = tmp_path / ".config" / "graph-agent"
        config_file = config_dir / "settings.json"

        import graph_agent.config as config_module
        monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

        # Set a default style
        from graph_agent.config import save_user_preferences
        save_user_preferences(default_style="bnr")

        state = GraphState(
            messages=[{"role": "user", "content": "bar chart: A=10, B=20"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": "bar", "style": None, "format": None},
            missing_params=None,
            final_filepath=None,
        )

        result = agent.resolve_ambiguity(state)

        assert result["missing_params"] is None  # Nothing missing (default available)
        assert result["chart_request"]["style"] == "bnr"  # From config


class TestAskClarification:
    """Test the ask_clarification node."""

    def test_ask_for_both_type_and_style(self):
        """Test question when both type and style are missing."""
        state = GraphState(
            messages=[{"role": "user", "content": "chart: A=10, B=20"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": None, "style": None, "format": "png"},
            missing_params=["type", "style"],
            final_filepath=None,
        )

        result = agent.ask_clarification(state)

        assert len(result["messages"]) == 2
        assert result["messages"][1]["role"] == "assistant"
        assert "type of chart (bar/line)" in result["messages"][1]["content"]
        assert "style (FD/BNR)" in result["messages"][1]["content"]

    def test_ask_for_type_only(self):
        """Test question when only type is missing."""
        state = GraphState(
            messages=[{"role": "user", "content": "FD chart: A=10, B=20"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": None, "style": "fd", "format": "png"},
            missing_params=["type"],
            final_filepath=None,
        )

        result = agent.ask_clarification(state)

        assert len(result["messages"]) == 2
        assert result["messages"][1]["role"] == "assistant"
        assert "What type of chart would you like: bar or line?" == result["messages"][1]["content"]

    def test_ask_for_style_only(self):
        """Test question when only style is missing."""
        state = GraphState(
            messages=[{"role": "user", "content": "bar chart: A=10, B=20"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": "bar", "style": None, "format": "png"},
            missing_params=["style"],
            final_filepath=None,
        )

        result = agent.ask_clarification(state)

        assert len(result["messages"]) == 2
        assert result["messages"][1]["role"] == "assistant"
        assert "Which brand style would you like: FD or BNR?" == result["messages"][1]["content"]

    def test_no_missing_params(self):
        """Test that no question is added when nothing is missing."""
        state = GraphState(
            messages=[{"role": "user", "content": "bar chart, FD: A=10"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": "bar", "style": "fd", "format": "png"},
            missing_params=None,
            final_filepath=None,
        )

        result = agent.ask_clarification(state)

        # No new message added
        assert len(result["messages"]) == 1


class TestReportError:
    """Test the report_error node (Story 8)."""

    def test_report_error_for_off_topic(self):
        """Test error message for off-topic requests."""
        state = GraphState(
            messages=[{"role": "user", "content": "make me a sandwich"}],
            interaction_mode="direct",
            intent="off_topic",
            has_file=False,
            config_change=None,
            input_data=None,
            chart_request=None,
            missing_params=None,
            final_filepath=None,
        )

        result = agent.report_error(state)

        assert len(result["messages"]) == 2
        assert result["messages"][1]["role"] == "assistant"
        assert "I can only help you create charts" in result["messages"][1]["content"]

    def test_report_error_for_missing_type(self):
        """Test error message when only chart type is missing."""
        state = GraphState(
            messages=[{"role": "user", "content": "chart: A=10, B=20"}],
            interaction_mode="direct",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": None, "style": "fd", "format": "png"},
            missing_params=["type"],
            final_filepath=None,
        )

        result = agent.report_error(state)

        assert len(result["messages"]) == 2
        assert result["messages"][1]["role"] == "assistant"
        assert "Error: Chart type is ambiguous" in result["messages"][1]["content"]
        assert "--type bar or --type line" in result["messages"][1]["content"]

    def test_report_error_for_missing_style(self):
        """Test error message when only style is missing."""
        state = GraphState(
            messages=[{"role": "user", "content": "chart: A=10, B=20"}],
            interaction_mode="direct",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": "bar", "style": None, "format": "png"},
            missing_params=["style"],
            final_filepath=None,
        )

        result = agent.report_error(state)

        assert len(result["messages"]) == 2
        assert result["messages"][1]["role"] == "assistant"
        assert "Error: Brand style not specified" in result["messages"][1]["content"]
        assert "--style fd or --style bnr" in result["messages"][1]["content"]

    def test_report_error_for_multiple_missing(self):
        """Test error message when both type and style are missing."""
        state = GraphState(
            messages=[{"role": "user", "content": "chart: A=10, B=20"}],
            interaction_mode="direct",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": None, "style": None, "format": "png"},
            missing_params=["type", "style"],
            final_filepath=None,
        )

        result = agent.report_error(state)

        assert len(result["messages"]) == 2
        assert result["messages"][1]["role"] == "assistant"
        assert "Error: Missing required parameters:" in result["messages"][1]["content"]
        assert "Chart type: use --type bar or --type line" in result["messages"][1]["content"]
        assert "Brand style: use --style fd or --style bnr" in result["messages"][1]["content"]


class TestRouteAfterResolve:
    """Test the route_after_resolve routing function."""

    def test_route_to_clarification_in_conversational_mode(self):
        """Test routing to ask_clarification when params missing in conversational mode."""
        state = GraphState(
            messages=[{"role": "user", "content": "chart"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": None, "style": None, "format": "png"},
            missing_params=["type", "style"],
            final_filepath=None,
        )

        route = agent.route_after_resolve(state)
        assert route == "ask_clarification"

    def test_route_to_generate_when_params_present(self):
        """Test routing to generate_chart when all params present."""
        state = GraphState(
            messages=[{"role": "user", "content": "chart"}],
            interaction_mode="conversational",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": "bar", "style": "fd", "format": "png"},
            missing_params=None,
            final_filepath=None,
        )

        route = agent.route_after_resolve(state)
        assert route == "generate_chart"

    def test_direct_mode_with_missing_params_routes_to_error(self):
        """Test that direct mode routes to report_error when params are missing (Story 8)."""
        state = GraphState(
            messages=[{"role": "user", "content": "chart"}],
            interaction_mode="direct",
            intent="make_chart",
            has_file=False,
            config_change=None,
            input_data=json.dumps([{"label": "A", "value": 10}]),
            chart_request={"type": None, "style": None, "format": "png"},
            missing_params=["type", "style"],
            final_filepath=None,
        )

        route = agent.route_after_resolve(state)
        # Story 8: Direct mode routes to report_error for missing params
        assert route == "report_error"
