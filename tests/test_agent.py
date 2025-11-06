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
