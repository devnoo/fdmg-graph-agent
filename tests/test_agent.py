"""Tests for Graph Agent LangGraph workflow."""

import pytest
from unittest.mock import Mock, patch
from graph_agent.state import GraphState
from graph_agent import agent


def test_parse_intent_node_with_chart_request():
    """Test parse_intent node identifies chart-related requests."""
    state = GraphState(
        messages=[{"role": "user", "content": "create a bar chart"}],
        interaction_mode="direct",
        intent="unknown",
    )

    # Mock the LLM to return 'make_chart'
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "make_chart"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = agent.parse_intent(state)

    assert result["intent"] == "make_chart"
    assert result["messages"] == state["messages"]


def test_parse_intent_node_with_off_topic_request():
    """Test parse_intent node identifies off-topic requests."""
    state = GraphState(
        messages=[{"role": "user", "content": "make me a sandwich"}],
        interaction_mode="direct",
        intent="unknown",
    )

    # Mock the LLM to return 'off_topic'
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "off_topic"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = agent.parse_intent(state)

    assert result["intent"] == "off_topic"


def test_reject_task_node_for_off_topic():
    """Test reject_task node returns proper message for off-topic requests."""
    state = GraphState(
        messages=[{"role": "user", "content": "make me a sandwich"}],
        interaction_mode="direct",
        intent="off_topic",
    )

    result = agent.reject_task(state)

    assert len(result["messages"]) == 2
    assert result["messages"][1]["role"] == "assistant"
    expected_msg = (
        "I can only help you create charts. Please ask me to make a bar or line chart."
    )
    assert result["messages"][1]["content"] == expected_msg


def test_reject_task_node_for_chart_request():
    """Test reject_task node returns 'not implemented' message for chart requests."""
    state = GraphState(
        messages=[{"role": "user", "content": "create a bar chart"}],
        interaction_mode="direct",
        intent="make_chart",
    )

    result = agent.reject_task(state)

    assert len(result["messages"]) == 2
    assert result["messages"][1]["role"] == "assistant"
    assert (
        result["messages"][1]["content"]
        == "Chart generation is not yet implemented. Check back soon!"
    )


def test_graph_compilation():
    """Test that the graph compiles successfully."""
    graph = agent.create_graph()
    assert graph is not None


def test_graph_execution_off_topic():
    """Test full graph execution with off-topic request."""
    # Mock the LLM
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "off_topic"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        graph = agent.create_graph()
        initial_state = GraphState(
            messages=[{"role": "user", "content": "make me a sandwich"}],
            interaction_mode="direct",
            intent="unknown",
        )

        result = graph.invoke(initial_state)

        assert result["intent"] == "off_topic"
        assert len(result["messages"]) == 2
        assert "can only help you create charts" in result["messages"][1]["content"]


def test_graph_execution_chart_request():
    """Test full graph execution with chart request (now generates charts with defaults)."""
    import os

    # Mock the LLM
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        # First call: parse_intent
        intent_response = Mock()
        intent_response.content = "make_chart"

        # Second call: extract_data with defaults
        extract_response = Mock()
        extract_response.content = (
            '{"data": [{"label": "A", "value": 10}], '
            '"type": null, "style": null, "format": null}'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        graph = agent.create_graph()
        initial_state = GraphState(
            messages=[{"role": "user", "content": "create a bar chart with A=10"}],
            interaction_mode="conversational",
            intent="unknown",
            input_data=None,
            chart_request={"type": None, "style": None, "format": None},
            final_filepath=None,
        )

        result = graph.invoke(initial_state)

        assert result["intent"] == "make_chart"
        # Now generates actual charts, so check for success message
        assert "Chart saved:" in result["messages"][-1]["content"]
        assert result["final_filepath"] is not None

        # Cleanup
        if result.get("final_filepath") and os.path.exists(result["final_filepath"]):
            os.remove(result["final_filepath"])


def test_get_llm_requires_api_key():
    """Test that get_llm raises error if GOOGLE_API_KEY is not set."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            agent.get_llm()


def test_get_llm_with_api_key():
    """Test that get_llm returns a valid LLM instance with API key."""
    with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
        with patch("graph_agent.agent.ChatGoogleGenerativeAI") as mock_chat:
            mock_chat.return_value = Mock()
            llm = agent.get_llm()
            assert llm is not None
            mock_chat.assert_called_once()


def test_extract_data_node():
    """Test extract_data node extracts JSON data from text in direct mode."""
    state = GraphState(
        messages=[{"role": "user", "content": "A=10, B=20, C=30"}],
        interaction_mode="direct",
        intent="make_chart",
        input_data=None,
        chart_request={"type": "bar", "style": "fd", "format": "png"},
        final_filepath=None,
    )

    # Mock the LLM to return valid JSON (new format with parameters)
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = (
            '{"data": [{"label": "A", "value": 10}, {"label": "B", "value": 20}], '
            '"type": null, "style": null, "format": null}'
        )
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = agent.extract_data(state)

    assert result["input_data"] is not None
    assert "A" in result["input_data"]
    assert "10" in result["input_data"]
    # Parameters should keep original values from direct mode
    assert result["chart_request"]["type"] == "bar"
    assert result["chart_request"]["style"] == "fd"
    assert result["chart_request"]["format"] == "png"


def test_extract_data_handles_invalid_json():
    """Test extract_data handles invalid JSON response."""
    state = GraphState(
        messages=[{"role": "user", "content": "some text"}],
        interaction_mode="direct",
        intent="make_chart",
        input_data=None,
        chart_request={"type": "bar", "style": "fd", "format": "png"},
        final_filepath=None,
    )

    # Mock the LLM to return invalid JSON
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "This is not JSON"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = agent.extract_data(state)

    # Should provide a default fallback
    assert result["input_data"] is not None
    assert "unknown" in result["input_data"]


def test_generate_chart_tool_node():
    """Test generate_chart_tool creates chart file."""
    import json

    state = GraphState(
        messages=[{"role": "user", "content": "create chart"}],
        interaction_mode="direct",
        intent="make_chart",
        input_data=json.dumps(
            [{"label": "A", "value": 10}, {"label": "B", "value": 20}]
        ),
        chart_request={"type": "bar", "style": "fd", "format": "png"},
        final_filepath=None,
    )

    # Mock the matplotlib_chart_generator
    with patch("graph_agent.tools.matplotlib_chart_generator") as mock_gen:
        mock_gen.return_value = "/tmp/chart-123.png"

        result = agent.generate_chart_tool(state)

    assert result["final_filepath"] == "/tmp/chart-123.png"
    assert len(result["messages"]) == 2
    assert "Chart saved:" in result["messages"][1]["content"]
    mock_gen.assert_called_once()


def test_route_after_intent_off_topic():
    """Test route_after_intent routes off-topic to reject_task."""
    state = GraphState(
        messages=[{"role": "user", "content": "test"}],
        interaction_mode="direct",
        intent="off_topic",
        input_data=None,
        chart_request=None,
        final_filepath=None,
    )

    result = agent.route_after_intent(state)
    assert result == "reject_task"


def test_route_after_intent_make_chart_with_request():
    """Test route_after_intent routes chart request with parameters to extract_data."""
    state = GraphState(
        messages=[{"role": "user", "content": "test"}],
        interaction_mode="direct",
        intent="make_chart",
        input_data=None,
        chart_request={"type": "bar", "style": "fd", "format": "png"},
        final_filepath=None,
    )

    result = agent.route_after_intent(state)
    assert result == "extract_data"


def test_route_after_intent_make_chart_without_request():
    """Test route_after_intent routes chart request to extract_data (handles conversational mode)."""
    state = GraphState(
        messages=[{"role": "user", "content": "test"}],
        interaction_mode="conversational",
        intent="make_chart",
        input_data=None,
        chart_request=None,
        final_filepath=None,
    )

    result = agent.route_after_intent(state)
    # Now routes to extract_data for both modes (extract_data handles parameter extraction)
    assert result == "extract_data"


def test_full_chart_generation_flow():
    """Test full chart generation flow from start to finish (direct mode)."""
    import json
    import os

    # Mock LLM responses
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        # First call for parse_intent
        intent_response = Mock()
        intent_response.content = "make_chart"

        # Second call for extract_data (new format with parameters)
        extract_response = Mock()
        extract_response.content = (
            '{"data": [{"label": "A", "value": 10}, {"label": "B", "value": 20}], '
            '"type": null, "style": null, "format": null}'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        graph = agent.create_graph()
        initial_state = GraphState(
            messages=[{"role": "user", "content": "A=10, B=20"}],
            interaction_mode="direct",
            intent="unknown",
            input_data=None,
            chart_request={"type": "bar", "style": "fd", "format": "png"},
            final_filepath=None,
        )

        result = graph.invoke(initial_state)

        # Verify intent was detected
        assert result["intent"] == "make_chart"

        # Verify data was extracted
        assert result["input_data"] is not None

        # Verify chart file was generated
        assert result["final_filepath"] is not None
        assert os.path.exists(result["final_filepath"])

        # Verify success message
        assert "Chart saved:" in result["messages"][-1]["content"]

        # Cleanup
        if os.path.exists(result["final_filepath"]):
            os.remove(result["final_filepath"])


def test_extract_data_with_all_parameters_from_nl():
    """Test extract_data extracts all parameters from natural language (conversational mode)."""
    state = GraphState(
        messages=[
            {"role": "user", "content": "create a line chart with A=10, B=20. Use BNR style, SVG format."}
        ],
        interaction_mode="conversational",
        intent="make_chart",
        input_data=None,
        chart_request={"type": None, "style": None, "format": None},
        final_filepath=None,
    )

    # Mock LLM to return full extraction
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = (
            '{"data": [{"label": "A", "value": 10}, {"label": "B", "value": 20}], '
            '"type": "line", "style": "bnr", "format": "svg"}'
        )
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = agent.extract_data(state)

    # Verify data extraction
    assert result["input_data"] is not None
    assert "A" in result["input_data"]

    # Verify all parameters extracted
    assert result["chart_request"]["type"] == "line"
    assert result["chart_request"]["style"] == "bnr"
    assert result["chart_request"]["format"] == "svg"


def test_extract_data_with_partial_parameters_from_nl():
    """Test extract_data with some parameters specified, others default."""
    state = GraphState(
        messages=[
            {"role": "user", "content": "bar chart with X=5, Y=10. FD style."}
        ],
        interaction_mode="conversational",
        intent="make_chart",
        input_data=None,
        chart_request={"type": None, "style": None, "format": None},
        final_filepath=None,
    )

    # Mock LLM to return partial extraction (no format specified)
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = (
            '{"data": [{"label": "X", "value": 5}, {"label": "Y", "value": 10}], '
            '"type": "bar", "style": "fd", "format": null}'
        )
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = agent.extract_data(state)

    # Verify extracted parameters
    assert result["chart_request"]["type"] == "bar"
    assert result["chart_request"]["style"] == "fd"
    # Verify default applied for missing format
    assert result["chart_request"]["format"] == "png"


def test_extract_data_with_no_parameters_from_nl():
    """Test extract_data applies defaults when no parameters specified."""
    state = GraphState(
        messages=[
            {"role": "user", "content": "make a chart with Q1=100, Q2=200"}
        ],
        interaction_mode="conversational",
        intent="make_chart",
        input_data=None,
        chart_request={"type": None, "style": None, "format": None},
        final_filepath=None,
    )

    # Mock LLM to return no parameters (all null)
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = (
            '{"data": [{"label": "Q1", "value": 100}, {"label": "Q2", "value": 200}], '
            '"type": null, "style": null, "format": null}'
        )
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = agent.extract_data(state)

    # Verify all defaults applied
    assert result["chart_request"]["type"] == "bar"
    assert result["chart_request"]["style"] == "fd"
    assert result["chart_request"]["format"] == "png"


def test_conversational_mode_full_flow():
    """Test full conversational mode flow with parameter extraction."""
    import json
    import os

    # Mock LLM responses
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        # First call: parse_intent
        intent_response = Mock()
        intent_response.content = "make_chart"

        # Second call: extract_data with parameters
        extract_response = Mock()
        extract_response.content = (
            '{"data": [{"label": "A", "value": 10}, {"label": "B", "value": 20}], '
            '"type": "line", "style": "bnr", "format": "svg"}'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        graph = agent.create_graph()
        initial_state = GraphState(
            messages=[
                {"role": "user", "content": "line chart: A=10, B=20. BNR style, SVG."}
            ],
            interaction_mode="conversational",
            intent="unknown",
            input_data=None,
            chart_request={"type": None, "style": None, "format": None},
            final_filepath=None,
        )

        result = graph.invoke(initial_state)

        # Verify intent detected
        assert result["intent"] == "make_chart"

        # Verify parameters extracted from natural language
        assert result["chart_request"]["type"] == "line"
        assert result["chart_request"]["style"] == "bnr"
        assert result["chart_request"]["format"] == "svg"

        # Verify chart generated
        assert result["final_filepath"] is not None
        assert result["final_filepath"].endswith(".svg")
        assert os.path.exists(result["final_filepath"])

        # Verify success message
        assert "Chart saved:" in result["messages"][-1]["content"]

        # Cleanup
        if os.path.exists(result["final_filepath"]):
            os.remove(result["final_filepath"])


def test_dutch_query_with_bnr_style(tmp_path, monkeypatch):
    """Test Dutch language query with BNR style and decimal commas."""
    import json
    import os

    # Use temp config directory to isolate test
    config_dir = tmp_path / ".config" / "graph-agent"
    config_file = config_dir / "settings.json"

    import graph_agent.config as config_module
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

    # Mock LLM responses
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        # First call: parse_intent
        intent_response = Mock()
        intent_response.content = "make_chart"

        # Second call: extract_data with Dutch query and BNR style
        extract_response = Mock()
        extract_response.content = (
            '{"data": ['
            '{"label": "2020", "value": 25}, '
            '{"label": "2021", "value": 26}, '
            '{"label": "2022", "value": 26.5}, '
            '{"label": "2023", "value": 27.3}, '
            '{"label": "2024", "value": 27.9}, '
            '{"label": "2025", "value": 29}'
            '], '
            '"type": null, "style": "bnr", "format": null}'
        )

        mock_llm.invoke.side_effect = [intent_response, extract_response]
        mock_get_llm.return_value = mock_llm

        graph = agent.create_graph()
        initial_state = GraphState(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Ik wil een grafiek die aangeeft hoeveel miljard studieschuld "
                        "studenten hebben in de laatste jaren. De waarden zijn: "
                        "2020 = 25, 2021 = 26, 2022=26,5, 2023 = 27,3, 2024 = 27,9, "
                        "en 2025 = 29 gebruik bnr stijl"
                    ),
                }
            ],
            interaction_mode="conversational",
            intent="unknown",
            has_file=False,
            config_change=None,
            input_data=None,
            chart_request={"type": None, "style": None, "format": None},
            final_filepath=None,
        )

        result = graph.invoke(initial_state)

        # Verify intent detected
        assert result["intent"] == "make_chart"

        # Verify BNR style extracted from Dutch text
        assert result["chart_request"]["style"] == "bnr"
        assert result["chart_request"]["type"] == "bar"  # Default
        assert result["chart_request"]["format"] == "png"  # Default

        # Verify data extracted correctly with 6 data points
        data = json.loads(result["input_data"])
        assert len(data) == 6
        assert data[0] == {"label": "2020", "value": 25}
        assert data[2] == {"label": "2022", "value": 26.5}
        assert data[5] == {"label": "2025", "value": 29}

        # Verify chart generated
        assert result["final_filepath"] is not None
        assert os.path.exists(result["final_filepath"])
        assert result["final_filepath"].endswith(".png")

        # Verify success message
        assert "Chart saved:" in result["messages"][-1]["content"]

        # Cleanup
        if os.path.exists(result["final_filepath"]):
            os.remove(result["final_filepath"])
