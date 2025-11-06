"""Tests for GraphState definition."""

from graph_agent.state import GraphState


def test_graph_state_structure():
    """Test that GraphState has the required fields."""
    state = GraphState(
        messages=[{"role": "user", "content": "test"}],
        interaction_mode="direct",
        intent="unknown",
        input_data=None,
        chart_request=None,
        final_filepath=None,
    )

    assert "messages" in state
    assert "interaction_mode" in state
    assert "intent" in state
    assert "input_data" in state
    assert "chart_request" in state
    assert "final_filepath" in state
    assert isinstance(state["messages"], list)
    assert state["interaction_mode"] in ["direct", "conversational"]
    assert state["intent"] in ["make_chart", "off_topic", "unknown"]


def test_graph_state_messages_format():
    """Test that messages follow the expected format."""
    state = GraphState(
        messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ],
        interaction_mode="conversational",
        intent="unknown",
        input_data=None,
        chart_request=None,
        final_filepath=None,
    )

    assert len(state["messages"]) == 2
    assert state["messages"][0]["role"] == "user"
    assert state["messages"][1]["role"] == "assistant"


def test_graph_state_interaction_modes():
    """Test valid interaction modes."""
    # Direct mode
    state_direct = GraphState(
        messages=[],
        interaction_mode="direct",
        intent="unknown",
        input_data=None,
        chart_request=None,
        final_filepath=None,
    )
    assert state_direct["interaction_mode"] == "direct"

    # Conversational mode
    state_conv = GraphState(
        messages=[],
        interaction_mode="conversational",
        intent="unknown",
        input_data=None,
        chart_request=None,
        final_filepath=None,
    )
    assert state_conv["interaction_mode"] == "conversational"


def test_graph_state_intent_types():
    """Test valid intent types."""
    intents = ["make_chart", "off_topic", "unknown"]

    for intent_type in intents:
        state = GraphState(
            messages=[],
            interaction_mode="direct",
            intent=intent_type,
            input_data=None,
            chart_request=None,
            final_filepath=None,
        )
        assert state["intent"] == intent_type


def test_graph_state_chart_fields():
    """Test chart-specific fields in GraphState."""
    state = GraphState(
        messages=[{"role": "user", "content": "create a chart"}],
        interaction_mode="direct",
        intent="make_chart",
        input_data='[{"label": "A", "value": 10}, {"label": "B", "value": 20}]',
        chart_request={"type": "bar", "style": "fd", "format": "png"},
        final_filepath="/path/to/chart-20251106.png",
    )

    assert state["input_data"] is not None
    assert state["chart_request"] is not None
    assert state["final_filepath"] is not None
    assert state["chart_request"]["type"] == "bar"
    assert state["chart_request"]["style"] == "fd"
    assert state["chart_request"]["format"] == "png"
