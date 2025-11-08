"""State definition for Graph Agent LangGraph workflow."""

from typing import TypedDict, Literal


class GraphState(TypedDict):
    """
    State object for the Graph Agent workflow.

    Attributes:
        messages: List of message dictionaries with 'role' and 'content' keys
        interaction_mode: Mode of interaction - 'direct' for single command or 'conversational' for REPL
        intent: Detected user intent - 'make_chart', 'set_config', 'off_topic', or 'unknown'
        has_file: Whether the user mentioned an Excel file path
        config_change: Dictionary with config change request (type and value), or None
        input_data: JSON string of extracted data points (e.g., '[{"label": "A", "value": 10}, ...]')
        chart_request: Dictionary with chart parameters (type, style, format)
        missing_params: List of missing parameters that need clarification (e.g., ["type", "style"])
        output_filename: User-specified output filename (from CLI flag or in-query detection)
        final_filepath: Absolute path to the generated chart file
        error_message: Error message string when an error occurs (e.g., file not found), or None
    """

    messages: list[dict]
    interaction_mode: Literal["direct", "conversational"]
    intent: Literal["make_chart", "set_config", "off_topic", "unknown"]
    has_file: bool
    config_change: dict | None
    input_data: str | None
    chart_request: dict | None
    missing_params: list[str] | None
    output_filename: str | None
    final_filepath: str | None
    error_message: str | None
