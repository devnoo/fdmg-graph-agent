"""State definition for Graph Agent LangGraph workflow."""

from typing import TypedDict, Literal


class GraphState(TypedDict):
    """
    State object for the Graph Agent workflow.

    Attributes:
        messages: List of message dictionaries with 'role' and 'content' keys
        interaction_mode: Mode of interaction - 'direct' for single command or 'conversational' for REPL
        intent: Detected user intent - 'make_chart', 'off_topic', or 'unknown'
    """

    messages: list[dict]
    interaction_mode: Literal["direct", "conversational"]
    intent: Literal["make_chart", "off_topic", "unknown"]
