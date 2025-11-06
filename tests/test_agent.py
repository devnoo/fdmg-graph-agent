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
    """Test full graph execution with chart request."""
    # Mock the LLM
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "make_chart"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        graph = agent.create_graph()
        initial_state = GraphState(
            messages=[{"role": "user", "content": "create a bar chart"}],
            interaction_mode="direct",
            intent="unknown",
        )

        result = graph.invoke(initial_state)

        assert result["intent"] == "make_chart"
        assert len(result["messages"]) == 2
        assert "not yet implemented" in result["messages"][1]["content"]


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
    """Test extract_data node extracts JSON data from text."""
    state = GraphState(
        messages=[{"role": "user", "content": "A=10, B=20, C=30"}],
        interaction_mode="direct",
        intent="make_chart",
        input_data=None,
        chart_request={"type": "bar", "style": "fd", "format": "png"},
        final_filepath=None,
    )

    # Mock the LLM to return valid JSON
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = (
            '[{"label": "A", "value": 10}, {"label": "B", "value": 20}]'
        )
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = agent.extract_data(state)

    assert result["input_data"] is not None
    assert "A" in result["input_data"]
    assert "10" in result["input_data"]


def test_extract_data_handles_invalid_json():
    """Test extract_data handles invalid JSON response with error message."""
    state = GraphState(
        messages=[{"role": "user", "content": "some text"}],
        interaction_mode="direct",
        intent="make_chart",
        input_data=None,
        chart_request={"type": "bar", "style": "fd", "format": "png"},
        final_filepath=None,
        error_message=None,
    )

    # Mock the LLM to return invalid JSON
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "This is not JSON"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        result = agent.extract_data(state)

    # Should set error_message and input_data should be None
    assert result["input_data"] is None
    assert result["error_message"] is not None
    assert (
        "parse" in result["error_message"].lower()
        or "json" in result["error_message"].lower()
    )


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
    """Test route_after_intent routes chart request without parameters to reject_task."""
    state = GraphState(
        messages=[{"role": "user", "content": "test"}],
        interaction_mode="direct",
        intent="make_chart",
        input_data=None,
        chart_request=None,
        final_filepath=None,
    )

    result = agent.route_after_intent(state)
    assert result == "reject_task"


def test_full_chart_generation_flow():
    """Test full chart generation flow from start to finish."""
    import json
    import os

    # Mock LLM responses
    with patch("graph_agent.agent.get_llm") as mock_get_llm:
        mock_llm = Mock()

        # First call for parse_intent
        intent_response = Mock()
        intent_response.content = "make_chart"

        # Second call for extract_data
        extract_response = Mock()
        extract_response.content = json.dumps(
            [{"label": "A", "value": 10}, {"label": "B", "value": 20}]
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


# ============================================================================
# DATA VALIDATION UNIT TESTS (Phase 2)
# ============================================================================


def test_validate_extracted_data_valid_json_array():
    """Test validation accepts valid JSON array with proper structure."""
    import json

    valid_data = json.dumps([{"label": "A", "value": 10}, {"label": "B", "value": 20}])

    # This function should not exist yet - will fail until implemented
    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(valid_data)
    assert error is None


def test_validate_extracted_data_rejects_empty_array():
    """Test validation rejects empty JSON array."""
    import json

    empty_data = json.dumps([])

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(empty_data)
    assert error is not None
    assert "data" in error.lower()


def test_validate_extracted_data_rejects_insufficient_data():
    """Test validation requires at least 2 data points."""
    import json

    single_point = json.dumps([{"label": "A", "value": 10}])

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(single_point)
    assert error is not None
    assert "at least 2" in error.lower() or "insufficient" in error.lower()


def test_validate_extracted_data_rejects_all_zero_values():
    """Test validation rejects data where all values are zero."""
    import json

    zero_data = json.dumps([{"label": "A", "value": 0}, {"label": "B", "value": 0}])

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(zero_data)
    assert error is not None
    assert "zero" in error.lower() or "meaningful" in error.lower()


def test_validate_extracted_data_rejects_nan_values():
    """Test validation rejects NaN values."""
    import json

    nan_data = json.dumps([{"label": "A", "value": None}, {"label": "B", "value": 20}])

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(nan_data)
    assert error is not None
    assert "invalid" in error.lower() or "null" in error.lower()


def test_validate_extracted_data_rejects_empty_labels():
    """Test validation rejects empty label strings."""
    import json

    empty_label = json.dumps([{"label": "", "value": 10}, {"label": "B", "value": 20}])

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(empty_label)
    assert error is not None
    assert "label" in error.lower() and "empty" in error.lower()


def test_validate_extracted_data_rejects_whitespace_labels():
    """Test validation rejects whitespace-only labels."""
    import json

    whitespace_label = json.dumps(
        [{"label": "   ", "value": 10}, {"label": "B", "value": 20}]
    )

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(whitespace_label)
    assert error is not None
    assert "label" in error.lower()


def test_validate_extracted_data_rejects_missing_label_field():
    """Test validation rejects objects missing 'label' field."""
    import json

    missing_label = json.dumps([{"value": 10}, {"label": "B", "value": 20}])

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(missing_label)
    assert error is not None
    assert "label" in error.lower()


def test_validate_extracted_data_rejects_missing_value_field():
    """Test validation rejects objects missing 'value' field."""
    import json

    missing_value = json.dumps([{"label": "A"}, {"label": "B", "value": 20}])

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(missing_value)
    assert error is not None
    assert "value" in error.lower()


def test_validate_extracted_data_rejects_non_numeric_values():
    """Test validation rejects non-numeric value types."""
    import json

    string_value = json.dumps(
        [{"label": "A", "value": "ten"}, {"label": "B", "value": 20}]
    )

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(string_value)
    assert error is not None
    assert "number" in error.lower() or "numeric" in error.lower()


def test_validate_extracted_data_rejects_invalid_json():
    """Test validation rejects malformed JSON."""
    invalid_json = "This is not JSON"

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(invalid_json)
    assert error is not None
    assert "json" in error.lower() or "parse" in error.lower()


def test_validate_extracted_data_rejects_json_object():
    """Test validation rejects JSON object instead of array."""
    json_object = '{"label": "A", "value": 10}'

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(json_object)
    assert error is not None
    assert "array" in error.lower()


def test_validate_extracted_data_accepts_negative_values():
    """Test validation accepts negative values (for profit/loss charts)."""
    import json

    negative_data = json.dumps(
        [{"label": "Profit", "value": 100}, {"label": "Loss", "value": -50}]
    )

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(negative_data)
    assert error is None


def test_validate_extracted_data_accepts_float_values():
    """Test validation accepts float values."""
    import json

    float_data = json.dumps(
        [{"label": "Mon", "value": 4.5}, {"label": "Tue", "value": 3.2}]
    )

    from graph_agent.agent import validate_extracted_data

    error = validate_extracted_data(float_data)
    assert error is None
