"""State definition for Graph Agent LangGraph workflow."""

from typing import TypedDict, Literal


class GraphState(TypedDict):
    """
    State object for the Graph Agent workflow.

    Attributes:
        messages: List of message dictionaries with 'role' and 'content' keys
        interaction_mode: Mode of interaction - 'direct' for single command or 'conversational' for REPL
        intent: Detected user intent - 'make_chart', 'off_topic', or 'unknown'
        has_file: Whether the user mentioned an Excel file path
        input_data: JSON string of extracted data points (e.g., '[{"label": "A", "value": 10}, ...]')
        chart_request: Dictionary with chart parameters (type, style, format)
        final_filepath: Absolute path to the generated chart file
    """

    messages: list[dict]
    interaction_mode: Literal["direct", "conversational"]
    intent: Literal["make_chart", "off_topic", "unknown"]
    has_file: bool
    input_data: str | None
    chart_request: dict | None
    final_filepath: str | None
