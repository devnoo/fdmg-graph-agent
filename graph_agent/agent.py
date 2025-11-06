"""LangGraph agent implementation for Graph Agent."""

import os
import logging
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from graph_agent.state import GraphState

# Configure logging
logger = logging.getLogger(__name__)


def get_llm() -> ChatGoogleGenerativeAI:
    """
    Initialize and return the Gemini LLM.

    Returns:
        ChatGoogleGenerativeAI: Configured LLM instance

    Raises:
        ValueError: If GOOGLE_API_KEY environment variable is not set
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is required. "
            "Please set it with your Google AI API key."
        )

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", temperature=0, google_api_key=api_key
    )


def parse_intent(state: GraphState) -> GraphState:
    """
    Parse user intent to determine if request is chart-related, config change, or off-topic.
    Also detects if user mentioned an Excel file path.

    This node uses the Gemini LLM to analyze the user's message and classify
    it as either a chart-related request ('make_chart'), config change ('set_config'),
    or an off-topic request ('off_topic'). It also checks for file path references.

    Args:
        state: Current graph state containing messages

    Returns:
        Updated state with intent, has_file, and config_change fields populated
    """
    import json
    import re

    llm = get_llm()

    # Get the last user message
    user_message = state["messages"][-1]["content"]
    logger.debug(f"parse_intent: Analyzing message: {user_message[:100]}...")

    # Enhanced prompt to detect intent, file presence, and config changes
    system_prompt = """Analyze the following user request and determine:
1. If it's about creating a chart/graph
2. If it's about setting a default preference (style or format)
3. If it mentions an Excel file (.xlsx or .xls)

Return a JSON object with this EXACT format:
{{
  "intent": "make_chart" or "set_config" or "off_topic",
  "has_file": true or false,
  "config_type": "style" or "format" or null,
  "config_value": "fd" or "bnr" or "png" or "svg" or null
}}

Intent should be "make_chart" if:
- Keywords: chart, graph, bar, line, plot, visualize, visualization, grafiek, diagram
- Data patterns: "A=10, B=20", "Monday: 4.1", "Q1=120, Q2=150"
- Requests with structured numerical data (even without explicit chart keywords)
- Mentions reading from an Excel file

Intent should be "set_config" if:
- "Set my default style to FD" -> config_type: "style", config_value: "fd"
- "Make BNR my default style" -> config_type: "style", config_value: "bnr"
- "Set default format to SVG" -> config_type: "format", config_value: "svg"
- "Change my default output format to PNG" -> config_type: "format", config_value: "png"
- Keywords: "set default", "make my default", "change default", "default style", "default format"

Intent should be "off_topic" for anything else (like making sandwiches, booking appointments, etc.)

has_file should be true if:
- Mentions a file path ending in .xlsx or .xls
- Mentions "Excel file", "spreadsheet", "from file"
- Contains what looks like a file path (e.g., "data.xlsx", "/path/to/file.xlsx", "sales.xls")

config_type and config_value should ONLY be set when intent is "set_config".

User request: {request}

JSON response:"""

    prompt = system_prompt.format(request=user_message)

    # Call LLM
    response = llm.invoke(prompt)
    response_text = response.content.strip()
    logger.debug(f"parse_intent: LLM returned: {response_text}")

    # Parse JSON response
    try:
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
            response_text = response_text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(response_text)
        intent = parsed.get("intent", "off_topic").strip().lower()
        has_file = parsed.get("has_file", False)
        config_type = parsed.get("config_type")
        config_value = parsed.get("config_value")
        logger.debug(f"parse_intent: Parsed - intent: {intent}, has_file: {has_file}, "
                    f"config_type: {config_type}, config_value: {config_value}")

    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"parse_intent: Failed to parse JSON response: {e}")
        # Fall back to basic intent detection
        intent = "make_chart" if "chart" in user_message.lower() or "graph" in user_message.lower() else "off_topic"
        # Check for file patterns
        has_file = bool(re.search(r'\.(xlsx?|xls)\b', user_message, re.IGNORECASE))
        config_type = None
        config_value = None

    # Ensure intent is valid
    if intent not in ["make_chart", "set_config", "off_topic"]:
        logger.warning(f"parse_intent: Invalid intent '{intent}', defaulting to 'off_topic'")
        intent = "off_topic"

    # Fallback: Check for obvious data patterns if LLM said off_topic
    if intent == "off_topic":
        # Look for patterns like "A=10", "Monday: 4.1", "Q1 = 120"
        data_pattern = r"[A-Za-z0-9]+\s*[=:]\s*[0-9,.]+"
        if re.search(data_pattern, user_message):
            logger.info("parse_intent: Detected data pattern, overriding to 'make_chart'")
            intent = "make_chart"

    # Fallback: Double-check for file patterns
    if not has_file:
        has_file = bool(re.search(r'\.(xlsx?|xls)\b', user_message, re.IGNORECASE))
        if has_file:
            logger.info("parse_intent: Regex detected file pattern")

    # Build config_change object
    config_change = None
    if intent == "set_config" and config_type and config_value:
        config_change = {"type": config_type, "value": config_value}
        logger.info(f"parse_intent: Config change detected - {config_type}: {config_value}")

    logger.info(f"parse_intent: Final - intent: {intent}, has_file: {has_file}, config_change: {config_change}")

    # Update state
    return GraphState(
        messages=state["messages"],
        interaction_mode=state["interaction_mode"],
        intent=intent,
        has_file=has_file,
        config_change=config_change,
        input_data=state.get("input_data"),
        chart_request=state.get("chart_request"),
        final_filepath=state.get("final_filepath"),
    )


def reject_task(state: GraphState) -> GraphState:
    """
    Generate appropriate response based on detected intent.

    For off-topic requests: Returns polite rejection message
    For chart requests: Returns 'not yet implemented' message

    Args:
        state: Current graph state with intent populated

    Returns:
        Updated state with assistant response added to messages
    """
    if state["intent"] == "off_topic":
        response = "I can only help you create charts. Please ask me to make a bar or line chart."
    elif state["intent"] == "make_chart":
        response = "Chart generation is not yet implemented. Check back soon!"
    else:
        # Fallback for unknown intent
        response = "I can only help you create charts. Please ask me to make a bar or line chart."

    # Add assistant response to messages
    updated_messages = state["messages"] + [{"role": "assistant", "content": response}]

    return GraphState(
        messages=updated_messages,
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        has_file=state.get("has_file", False),
        config_change=state.get("config_change"),
        input_data=state.get("input_data"),
        chart_request=state.get("chart_request"),
        final_filepath=state.get("final_filepath"),
    )


def handle_config(state: GraphState) -> GraphState:
    """
    Handle configuration change requests from the user.

    This node processes requests to set default style or format preferences.
    It updates the config file and returns a confirmation message.

    Args:
        state: Current graph state with config_change populated

    Returns:
        Updated state with confirmation message added to messages
    """
    from graph_agent.config import save_user_preferences

    config_change = state.get("config_change")

    if not config_change:
        # No config change detected, return error message
        response = "I couldn't understand that configuration change."
        logger.warning("handle_config: Called but no config_change in state")
    else:
        config_type = config_change.get("type")
        config_value = config_change.get("value")

        if config_type == "style":
            save_user_preferences(default_style=config_value)
            response = f"Your default style is now set to {config_value.upper()}."
            logger.info(f"handle_config: Set default style to {config_value}")
        elif config_type == "format":
            save_user_preferences(default_format=config_value)
            response = f"Your default format is now set to {config_value.upper()}."
            logger.info(f"handle_config: Set default format to {config_value}")
        else:
            response = "I couldn't understand that configuration change."
            logger.warning(f"handle_config: Unknown config_type '{config_type}'")

    # Add confirmation message to conversation
    updated_messages = state["messages"] + [{"role": "assistant", "content": response}]

    return GraphState(
        messages=updated_messages,
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        has_file=state.get("has_file", False),
        config_change=config_change,
        input_data=state.get("input_data"),
        chart_request=state.get("chart_request"),
        final_filepath=state.get("final_filepath"),
    )


def extract_data(state: GraphState) -> GraphState:
    """
    Extract structured data and chart parameters from user's natural language prompt using Gemini.

    This node uses the LLM to parse the user's message and extract:
    1. Label-value pairs (data)
    2. Chart parameters (type, style, format) if mentioned

    Args:
        state: Current graph state containing user message

    Returns:
        Updated state with input_data and chart_request fields populated
    """
    import json

    llm = get_llm()

    # Get the last user message
    user_message = state["messages"][-1]["content"]
    logger.debug(f"extract_data: Processing message: {user_message[:100]}...")

    # Create prompt for data and parameter extraction
    extraction_prompt = """Extract data and chart parameters from the following text.

Return a JSON object with this exact format:
{{
  "data": [{{"label": "label1", "value": number1}}, {{"label": "label2", "value": number2}}, ...],
  "type": "bar" or "line" or null,
  "style": "fd" or "bnr" or null,
  "format": "png" or "svg" or null
}}

Data extraction examples:
- "A=10, B=20, C=30" -> "data": [{{"label": "A", "value": 10}}, {{"label": "B", "value": 20}}, {{"label": "C", "value": 30}}]
- "Monday: 4.1, Tuesday: 4.2" -> "data": [{{"label": "Monday", "value": 4.1}}, {{"label": "Tuesday", "value": 4.2}}]

Parameter extraction examples:
- "bar chart" or "bar graph" -> "type": "bar"
- "line chart" or "line graph" -> "type": "line"
- "FD style" or "FD colors" or "Financial Daily" or "Financieele Dagblad" -> "style": "fd"
- "BNR style" or "BNR colors" -> "style": "bnr"
- "PNG format" or "as PNG" or "save as PNG" -> "format": "png"
- "SVG format" or "as SVG" or "save as SVG" -> "format": "svg"

IMPORTANT:
- Return ONLY the JSON object, no other text
- Set parameters to null if not mentioned in the text
- Always extract the data array

Text to extract from: {text}

JSON object:"""

    prompt = extraction_prompt.format(text=user_message)

    # Call LLM
    logger.debug("extract_data: Calling LLM for data and parameter extraction")
    response = llm.invoke(prompt)
    extracted_json = response.content.strip()
    logger.debug(f"extract_data: Raw LLM response: {extracted_json[:200]}...")

    # Clean up response - remove markdown code blocks if present
    if extracted_json.startswith("```"):
        logger.debug("extract_data: Cleaning markdown code blocks from response")
        lines = extracted_json.split("\n")
        extracted_json = "\n".join(lines[1:-1]) if len(lines) > 2 else extracted_json
        extracted_json = (
            extracted_json.replace("```json", "").replace("```", "").strip()
        )

    # Validate and parse JSON
    try:
        parsed = json.loads(extracted_json)
        data = parsed.get("data", [])
        logger.debug(f"extract_data: Parsed data: {data}")

        # If data is empty or invalid, create default
        if not data:
            logger.warning("extract_data: No data extracted, using default")
            data = [{"label": "unknown", "value": 0}]

        # Convert data back to JSON string
        input_data = json.dumps(data)

        # Extract parameters (may be None)
        extracted_type = parsed.get("type")
        extracted_style = parsed.get("style")
        extracted_format = parsed.get("format")
        logger.debug(f"extract_data: Extracted parameters from NL - type: {extracted_type}, "
                    f"style: {extracted_style}, format: {extracted_format}")

    except (json.JSONDecodeError, AttributeError) as e:
        # If invalid, create default structure
        logger.error(f"extract_data: Failed to parse JSON: {e}")
        logger.debug(f"extract_data: Problematic JSON: {extracted_json}")
        input_data = '[{"label": "unknown", "value": 0}]'
        extracted_type = None
        extracted_style = None
        extracted_format = None

    # Get current chart_request or create default
    chart_request = state.get("chart_request") or {"type": None, "style": None, "format": None}
    logger.debug(f"extract_data: Current chart_request: {chart_request}")

    # Merge extracted parameters with existing chart_request
    # Only override if extracted parameter is not None
    if extracted_type:
        chart_request["type"] = extracted_type
    if extracted_style:
        chart_request["style"] = extracted_style
    if extracted_format:
        chart_request["format"] = extracted_format

    # Apply defaults for missing parameters using priority logic
    # Priority: Explicit > Default > Last Used > Fallback
    from graph_agent.config import load_user_preferences

    prefs = load_user_preferences()
    logger.debug(f"extract_data: Loaded preferences: {prefs}")

    # Apply type default (always default to bar if not specified)
    if chart_request["type"] is None:
        chart_request["type"] = "bar"

    # Apply style with priority logic: Explicit > Default > Last Used > None
    if chart_request["style"] is None:
        chart_request["style"] = (
            prefs.get("default_style") or
            prefs.get("last_used_style") or
            "fd"  # Final fallback
        )
        logger.debug(f"extract_data: Applied style priority: {chart_request['style']}")

    # Apply format with priority logic: Explicit > Default > Last Used > PNG
    if chart_request["format"] is None:
        chart_request["format"] = (
            prefs.get("default_format") or
            prefs.get("last_used_format") or
            "png"  # Final fallback
        )
        logger.debug(f"extract_data: Applied format priority: {chart_request['format']}")

    logger.info(f"extract_data: Final chart_request: type={chart_request['type']}, "
               f"style={chart_request['style']}, format={chart_request['format']}")

    # Update state
    return GraphState(
        messages=state["messages"],
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        has_file=state.get("has_file", False),
        input_data=input_data,
        chart_request=chart_request,
        final_filepath=state.get("final_filepath"),
    )


def generate_chart_tool(state: GraphState) -> GraphState:
    """
    Generate chart using matplotlib tool and save to file.

    This node calls the matplotlib_chart_generator tool with data from state
    and saves the generated chart file. It also updates the last_used_style
    and last_used_format in the config file.

    Args:
        state: Current graph state with input_data and chart_request populated

    Returns:
        Updated state with final_filepath and success message in messages
    """
    from graph_agent.tools import matplotlib_chart_generator
    from graph_agent.config import update_last_used

    # Get chart parameters
    chart_request = state["chart_request"]
    input_data = state["input_data"]

    # Generate chart
    filepath = matplotlib_chart_generator(
        data=input_data,
        chart_type=chart_request["type"],
        style=chart_request["style"],
        format=chart_request["format"],
    )

    # Update last used preferences
    update_last_used(
        style=chart_request["style"],
        format=chart_request["format"]
    )
    logger.info(f"generate_chart_tool: Updated last_used to style={chart_request['style']}, "
               f"format={chart_request['format']}")

    # Add success message
    updated_messages = state["messages"] + [
        {"role": "assistant", "content": f"Chart saved: {filepath}"}
    ]

    # Update state
    return GraphState(
        messages=updated_messages,
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        has_file=state.get("has_file", False),
        config_change=state.get("config_change"),
        input_data=state["input_data"],
        chart_request=state["chart_request"],
        final_filepath=filepath,
    )


def call_data_tool(state: GraphState) -> GraphState:
    """
    Extract file path from user message and parse Excel file.

    This node uses the LLM to extract the file path, then calls parse_excel_a1
    to extract data from the Excel file.

    Args:
        state: Current graph state with file reference in messages

    Returns:
        Updated state with input_data populated from Excel file
    """
    import json
    from graph_agent.tools import parse_excel_a1

    llm = get_llm()

    # Get the last user message
    user_message = state["messages"][-1]["content"]
    logger.debug(f"call_data_tool: Extracting file path from: {user_message[:100]}...")

    # Create prompt to extract file path
    extraction_prompt = """Extract the Excel file path from the following text.

Return ONLY the file path (without quotes) or "NONE" if no file path is found.

Examples:
- "create chart from sales.xlsx" -> sales.xlsx
- "make a graph from /home/user/data.xlsx" -> /home/user/data.xlsx
- "chart with quarterly_revenue.xls" -> quarterly_revenue.xls
- "make a chart with A=10, B=20" -> NONE

Text: {text}

File path:"""

    prompt = extraction_prompt.format(text=user_message)

    # Call LLM to extract file path
    logger.debug("call_data_tool: Calling LLM to extract file path")
    response = llm.invoke(prompt)
    file_path = response.content.strip()
    logger.debug(f"call_data_tool: Extracted file path: {file_path}")

    # Check if valid file path was extracted
    if file_path.upper() == "NONE" or not file_path:
        logger.warning("call_data_tool: No file path found, falling back to extract_data")
        # If no file found, this shouldn't happen if has_file was true, but handle gracefully
        # Set has_file to False and return state unchanged
        return GraphState(
            messages=state["messages"],
            interaction_mode=state["interaction_mode"],
            intent=state["intent"],
            has_file=False,
            input_data=state.get("input_data"),
            chart_request=state.get("chart_request"),
            final_filepath=state.get("final_filepath"),
        )

    # Try to parse the Excel file
    try:
        logger.info(f"call_data_tool: Parsing Excel file: {file_path}")
        data_json = parse_excel_a1(file_path)
        logger.info(f"call_data_tool: Successfully parsed file")

        # Also extract chart parameters from the message
        # Get current chart_request or create default
        chart_request = state.get("chart_request") or {"type": None, "style": None, "format": None}

        # Extract parameters from natural language
        param_prompt = """Extract chart parameters from the following text.

Return a JSON object with this exact format:
{{
  "type": "bar" or "line" or null,
  "style": "fd" or "bnr" or null,
  "format": "png" or "svg" or null
}}

Set parameters to null if not mentioned.

Text: {text}

JSON object:"""

        param_response = llm.invoke(param_prompt.format(text=user_message))
        param_json = param_response.content.strip()

        # Clean up response
        if param_json.startswith("```"):
            lines = param_json.split("\n")
            param_json = "\n".join(lines[1:-1]) if len(lines) > 2 else param_json
            param_json = param_json.replace("```json", "").replace("```", "").strip()

        try:
            params = json.loads(param_json)
            if params.get("type"):
                chart_request["type"] = params["type"]
            if params.get("style"):
                chart_request["style"] = params["style"]
            if params.get("format"):
                chart_request["format"] = params["format"]
        except (json.JSONDecodeError, AttributeError):
            logger.warning("call_data_tool: Failed to parse parameters, using defaults")

        # Apply defaults for missing parameters using priority logic
        # Priority: Explicit > Default > Last Used > Fallback
        from graph_agent.config import load_user_preferences

        prefs = load_user_preferences()
        logger.debug(f"call_data_tool: Loaded preferences: {prefs}")

        # Apply type default (always default to bar if not specified)
        if chart_request["type"] is None:
            chart_request["type"] = "bar"

        # Apply style with priority logic: Explicit > Default > Last Used > FD
        if chart_request["style"] is None:
            chart_request["style"] = (
                prefs.get("default_style") or
                prefs.get("last_used_style") or
                "fd"  # Final fallback
            )
            logger.debug(f"call_data_tool: Applied style priority: {chart_request['style']}")

        # Apply format with priority logic: Explicit > Default > Last Used > PNG
        if chart_request["format"] is None:
            chart_request["format"] = (
                prefs.get("default_format") or
                prefs.get("last_used_format") or
                "png"  # Final fallback
            )
            logger.debug(f"call_data_tool: Applied format priority: {chart_request['format']}")

        logger.info(f"call_data_tool: Chart parameters: type={chart_request['type']}, "
                   f"style={chart_request['style']}, format={chart_request['format']}")

        # Return updated state with data from Excel
        return GraphState(
            messages=state["messages"],
            interaction_mode=state["interaction_mode"],
            intent=state["intent"],
            has_file=True,
            input_data=data_json,
            chart_request=chart_request,
            final_filepath=state.get("final_filepath"),
        )

    except ValueError as e:
        # Error parsing Excel file - add error message to conversation
        logger.error(f"call_data_tool: Error parsing Excel file: {e}")
        error_message = str(e)
        updated_messages = state["messages"] + [
            {"role": "assistant", "content": error_message}
        ]

        # Return state with error message
        return GraphState(
            messages=updated_messages,
            interaction_mode=state["interaction_mode"],
            intent="off_topic",  # Set to off_topic to end conversation
            has_file=state.get("has_file", False),
            input_data=state.get("input_data"),
            chart_request=state.get("chart_request"),
            final_filepath=state.get("final_filepath"),
        )


def route_after_intent(state: GraphState) -> str:
    """
    Route to appropriate node based on detected intent and file presence.

    For make_chart intent:
    - If has_file=True: Route to call_data_tool to parse Excel file
    - If has_file=False: Route to extract_data to extract from natural language

    For set_config intent:
    - Route to handle_config to update user preferences

    For off_topic intent:
    - Route to reject_task

    Args:
        state: Current graph state with intent and has_file populated

    Returns:
        Name of next node to execute
    """
    intent = state["intent"]
    has_file = state.get("has_file", False)
    mode = state["interaction_mode"]
    logger.debug(f"route_after_intent: Intent={intent}, HasFile={has_file}, Mode={mode}")

    if intent == "off_topic":
        logger.info("route_after_intent: Routing to reject_task (off-topic)")
        return "reject_task"
    elif intent == "set_config":
        logger.info("route_after_intent: Routing to handle_config (config change)")
        return "handle_config"
    elif intent == "make_chart":
        if has_file:
            logger.info(f"route_after_intent: Routing to call_data_tool (file-based, {mode} mode)")
            return "call_data_tool"
        else:
            logger.info(f"route_after_intent: Routing to extract_data (text-based, {mode} mode)")
            return "extract_data"
    else:
        logger.warning(f"route_after_intent: Unknown intent '{intent}', routing to reject_task")
        return "reject_task"


def create_graph() -> Any:
    """
    Create and compile the LangGraph workflow.

    The workflow consists of:
    1. parse_intent: Analyzes user request and determines intent and file presence
    2. Conditional routing:
       - If off_topic: reject_task -> END
       - If set_config: handle_config -> END
       - If make_chart + has_file: call_data_tool -> generate_chart -> END
       - If make_chart + no file: extract_data -> generate_chart -> END
    3. handle_config: Handles user preference changes (default style/format)
    4. call_data_tool: Parses Excel file and extracts data
    5. extract_data: Extracts structured data from natural language
    6. generate_chart: Creates chart file using matplotlib

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("parse_intent", parse_intent)
    workflow.add_node("reject_task", reject_task)
    workflow.add_node("handle_config", handle_config)  # NEW: Config management
    workflow.add_node("call_data_tool", call_data_tool)
    workflow.add_node("extract_data", extract_data)
    workflow.add_node("generate_chart", generate_chart_tool)

    # Set entry point
    workflow.set_entry_point("parse_intent")

    # Add conditional routing after parse_intent
    workflow.add_conditional_edges(
        "parse_intent",
        route_after_intent,
        {
            "reject_task": "reject_task",
            "handle_config": "handle_config",  # NEW: Route for config changes
            "call_data_tool": "call_data_tool",
            "extract_data": "extract_data",
        },
    )

    # Add edges for chart generation flow
    workflow.add_edge("call_data_tool", "generate_chart")
    workflow.add_edge("extract_data", "generate_chart")

    # Add terminal edges
    workflow.add_edge("reject_task", END)
    workflow.add_edge("handle_config", END)  # NEW: Terminal edge for config changes
    workflow.add_edge("generate_chart", END)

    # Compile and return
    return workflow.compile()
