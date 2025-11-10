"""Tests for Graph Agent LangGraph workflow."""

import pytest
from unittest.mock import Mock, patch
from graph_agent.state import GraphState
from graph_agent import agent
from graph_agent.agent import create_graph


class MockLLM:
    """Mock LLM for testing that returns predefined responses in sequence."""

    def __init__(self):
        self.responses = []
        self.call_count = 0

    def add_response(self, content):
        """Add a response to the queue."""
        self.responses.append(content)

    def invoke(self, prompt):
        """Return next response from queue."""
        if self.call_count >= len(self.responses):
            raise ValueError(f"MockLLM: No more responses (called {self.call_count} times)")
        response = Mock()
        response.content = self.responses[self.call_count]
        self.call_count += 1
        return response


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


def test_report_error_node_for_off_topic():
    """Test report_error node returns proper message for off-topic requests."""
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
    expected_msg = (
        "Ik kan je alleen helpen met het maken van grafieken. Vraag me alsjeblieft om een staaf- of lijngrafiek te maken."
    )
    assert result["messages"][1]["content"] == expected_msg


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
        assert "alleen helpen met het maken van grafieken" in result["messages"][1]["content"]


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
    """Test route_after_intent routes off-topic to report_error."""
    state = GraphState(
        messages=[{"role": "user", "content": "test"}],
        interaction_mode="direct",
        intent="off_topic",
        has_file=False,
        config_change=None,
        input_data=None,
        chart_request=None,
        missing_params=None,
        final_filepath=None,
    )

    result = agent.route_after_intent(state)
    assert result == "report_error"


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


def test_file_not_found_error_handling():
    """Test that non-existent Excel file is handled gracefully without crash."""
    # Mock parse_excel_a1 to raise ValueError (file not found)
    def mock_parse_excel_raise_error(file_path):
        raise ValueError(f"Fout: Kan bestand '{file_path}' niet vinden. Controleer alsjeblieft het bestandspad en probeer het opnieuw.")

    with patch("graph_agent.tools.parse_excel_a1", side_effect=mock_parse_excel_raise_error):
        with patch("graph_agent.agent.get_llm") as mock_get_llm:
            # Mock the get_llm function
            mock_llm = MockLLM()
            mock_get_llm.return_value = mock_llm

            # Create graph
            graph = create_graph()

            # Create initial state with file reference
            initial_state = GraphState(
                messages=[{"role": "user", "content": "Maak een grafiek van nonexistent.xlsx"}],
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

            # Configure mock LLM responses
            # parse_intent: detect file and make_chart intent
            mock_llm.add_response('{"intent": "make_chart", "has_file": true, "config_type": null, "config_value": null}')
            # call_data_tool: extract file path
            mock_llm.add_response("nonexistent.xlsx")

            # Invoke graph - should NOT crash
            result = graph.invoke(initial_state)

            # Verify error message is in the conversation
            assert len(result["messages"]) == 2  # User message + error message
            assert result["messages"][-1]["role"] == "assistant"
            error_msg = result["messages"][-1]["content"]
            assert "Fout:" in error_msg or "Kan bestand" in error_msg
            assert "nonexistent.xlsx" in error_msg

            # Verify error_message field is set
            assert result["error_message"] is not None
            assert "nonexistent.xlsx" in result["error_message"]

            # Verify chart was NOT generated (final_filepath is None)
            assert result["final_filepath"] is None


def test_file_not_found_conversational_mode():
    """Test file not found in conversational mode - should show error and allow continuation."""
    # Mock parse_excel_a1 to raise ValueError
    def mock_parse_excel_raise_error(file_path):
        raise ValueError(f"Fout: Kan bestand '{file_path}' niet vinden.")

    with patch("graph_agent.tools.parse_excel_a1", side_effect=mock_parse_excel_raise_error):
        with patch("graph_agent.agent.get_llm") as mock_get_llm:
            # Mock the get_llm function
            mock_llm = MockLLM()
            mock_get_llm.return_value = mock_llm

            # Create graph
            graph = create_graph()

            # Initial state in conversational mode
            initial_state = GraphState(
                messages=[{"role": "user", "content": "Create chart from missing_file.xlsx"}],
                interaction_mode="conversational",
                intent="unknown",
                has_file=False,
                config_change=None,
                input_data=None,
                chart_request={"type": None, "style": None, "format": None},
                missing_params=None,
                output_filename=None,
                final_filepath=None,
                error_message=None,
            )

            # Configure mock responses
            mock_llm.add_response('{"intent": "make_chart", "has_file": true, "config_type": null, "config_value": null}')
            mock_llm.add_response("missing_file.xlsx")

            # Invoke graph
            result = graph.invoke(initial_state)

            # Verify error was handled gracefully
            assert len(result["messages"]) == 2
            assert "Fout:" in result["messages"][-1]["content"] or "Kan bestand" in result["messages"][-1]["content"]
            assert result["error_message"] is not None
            assert result["final_filepath"] is None


def test_dutch_line_chart_detection():
    """Test that 'lijn grafiek' is detected as line chart."""
    from unittest.mock import Mock, patch
    from graph_agent.agent import create_graph
    from graph_agent.state import GraphState
    import os

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        # parse_intent response
        intent_response = Mock()
        intent_response.content = '{"intent": "make_chart", "has_file": false, "config_type": null, "config_value": null}'

        # extract_data response - should extract "line" from "lijn grafiek"
        extract_response = Mock()
        extract_response.content = (
            '{"data": [{"label": "A", "value": 10}, {"label": "B", "value": 20}], '
            '"type": "line", "style": "fd", "format": "png", "filename": null}'
        )

        # extract_logical_name response
        logical_name_response = Mock()
        logical_name_response.content = "grafiek"

        mock_llm.invoke.side_effect = [intent_response, extract_response, logical_name_response]
        mock_get_llm.return_value = mock_llm

        graph = create_graph()
        initial_state = GraphState(
            messages=[{"role": "user", "content": "kan je een lijn grafiek maken voor A=10, B=20"}],
            interaction_mode="direct",
            intent="unknown",
            has_file=False,
            config_change=None,
            input_data=None,
            chart_request={"type": None, "style": None, "format": None},
            missing_params=None,
            output_filename=None,
            final_filepath=None,
            error_message=None,
        )

        result = graph.invoke(initial_state)

        # Verify line chart was detected
        assert result["chart_request"]["type"] == "line"
        assert result["final_filepath"] is not None
        assert result["final_filepath"].endswith(".png")

        # Cleanup
        if os.path.exists(result["final_filepath"]):
            os.remove(result["final_filepath"])


def test_dutch_bar_chart_detection():
    """Test that 'staafdiagram' is detected as bar chart."""
    from unittest.mock import Mock, patch
    from graph_agent.agent import create_graph
    from graph_agent.state import GraphState
    import os

    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        # parse_intent response
        intent_response = Mock()
        intent_response.content = '{"intent": "make_chart", "has_file": false, "config_type": null, "config_value": null}'

        # extract_data response - should extract "bar" from "staafdiagram"
        extract_response = Mock()
        extract_response.content = (
            '{"data": [{"label": "X", "value": 5}, {"label": "Y", "value": 10}], '
            '"type": "bar", "style": "fd", "format": "png", "filename": null}'
        )

        # extract_logical_name response
        logical_name_response = Mock()
        logical_name_response.content = "staafdiagram"

        mock_llm.invoke.side_effect = [intent_response, extract_response, logical_name_response]
        mock_get_llm.return_value = mock_llm

        graph = create_graph()
        initial_state = GraphState(
            messages=[{"role": "user", "content": "maak een staafdiagram voor X=5, Y=10"}],
            interaction_mode="direct",
            intent="unknown",
            has_file=False,
            config_change=None,
            input_data=None,
            chart_request={"type": None, "style": None, "format": None},
            missing_params=None,
            output_filename=None,
            final_filepath=None,
            error_message=None,
        )

        result = graph.invoke(initial_state)

        # Verify bar chart was detected
        assert result["chart_request"]["type"] == "bar"
        assert result["final_filepath"] is not None

        # Cleanup
        if os.path.exists(result["final_filepath"]):
            os.remove(result["final_filepath"])


def test_language_detection_dutch():
    """Test that Dutch text is correctly detected."""
    from graph_agent.agent import detect_language

    assert detect_language("kan je een grafiek maken") == "nl"
    assert detect_language("maak een lijn grafiek voor de data") == "nl"
    assert detect_language("ik wil graag een diagram") == "nl"
    assert detect_language("genereer een staafdiagram") == "nl"


def test_language_detection_english():
    """Test that English text is correctly detected."""
    from graph_agent.agent import detect_language

    assert detect_language("create a bar chart") == "en"
    assert detect_language("make a line graph") == "en"
    assert detect_language("generate chart for data") == "en"
    assert detect_language("A=10, B=20, C=30") == "en"


def test_dutch_clarification_question():
    """Test that clarification questions are asked in Dutch when user speaks Dutch."""
    from graph_agent.agent import ask_clarification
    from graph_agent.state import GraphState

    state = GraphState(
        messages=[{"role": "user", "content": "kan je een grafiek maken voor A=10, B=20"}],
        interaction_mode="conversational",
        intent="make_chart",
        has_file=False,
        config_change=None,
        input_data='[{"label": "A", "value": 10}, {"label": "B", "value": 20}]',
        chart_request={"type": None, "style": None, "format": None},
        missing_params=["type"],
        output_filename=None,
        final_filepath=None,
        error_message=None,
    )

    result = ask_clarification(state)

    # Should ask in Dutch
    question = result["messages"][-1]["content"]
    assert "staafdiagram" in question.lower() or "lijngrafiek" in question.lower()
    assert "welk" in question.lower() or "wil je" in question.lower()


def test_english_clarification_question():
    """Test that clarification questions are asked in English when user speaks English."""
    from graph_agent.agent import ask_clarification
    from graph_agent.state import GraphState

    state = GraphState(
        messages=[{"role": "user", "content": "create a chart for A=10, B=20"}],
        interaction_mode="conversational",
        intent="make_chart",
        has_file=False,
        config_change=None,
        input_data='[{"label": "A", "value": 10}, {"label": "B", "value": 20}]',
        chart_request={"type": None, "style": None, "format": None},
        missing_params=["type"],
        output_filename=None,
        final_filepath=None,
        error_message=None,
    )

    result = ask_clarification(state)

    # Should ask in English
    question = result["messages"][-1]["content"]
    assert "bar" in question.lower() or "line" in question.lower()
    assert "what" in question.lower() or "would you like" in question.lower()
