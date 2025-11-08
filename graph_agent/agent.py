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
        missing_params=state.get("missing_params"),
        output_filename=state.get("output_filename"),
        final_filepath=state.get("final_filepath"),
        error_message=state.get("error_message"),
    )


def report_error(state: GraphState) -> GraphState:
    """
    Generate error message based on error type.

    This node handles:
    1. Off-topic requests (from Story 2)
    2. Ambiguity errors in direct mode (from Story 8)

    For ambiguity errors, the message clearly states what's missing
    and how to fix the command.

    Args:
        state: Current graph state with intent and missing_params populated

    Returns:
        Updated state with error message added to messages
    """
    intent = state.get("intent")
    missing = state.get("missing_params", [])

    # Off-topic requests (existing from Story 2)
    if intent == "off_topic":
        response = "I can only help you create charts. Please ask me to make a bar or line chart."
        logger.info("report_error: Off-topic request")

    # Ambiguity errors (new for Story 8)
    elif missing:
        if len(missing) == 1:
            if missing[0] == "type":
                response = "Error: Chart type is ambiguous. Please specify using --type bar or --type line"
                logger.info("report_error: Missing chart type")
            elif missing[0] == "style":
                response = "Error: Brand style not specified. Please use --style fd or --style bnr, or set a default style."
                logger.info("report_error: Missing brand style")
            else:
                response = "Error: Missing required parameter."
                logger.warning(f"report_error: Unknown missing param: {missing[0]}")
        else:
            # Multiple missing parameters
            response = "Error: Missing required parameters:\n"
            if "type" in missing:
                response += "  - Chart type: use --type bar or --type line\n"
            if "style" in missing:
                response += "  - Brand style: use --style fd or --style bnr"
            logger.info(f"report_error: Multiple missing params: {missing}")

    # Fallback
    else:
        response = "Error: Unable to process request."
        logger.warning("report_error: Called with no clear error condition")

    # Add error message to messages
    updated_messages = state["messages"] + [{"role": "assistant", "content": response}]

    return GraphState(
        messages=updated_messages,
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        has_file=state.get("has_file", False),
        config_change=state.get("config_change"),
        input_data=state.get("input_data"),
        chart_request=state.get("chart_request"),
        missing_params=state.get("missing_params"),
        output_filename=state.get("output_filename"),
        final_filepath=state.get("final_filepath"),
        error_message=state.get("error_message"),
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
        missing_params=state.get("missing_params"),
        output_filename=state.get("output_filename"),
        final_filepath=state.get("final_filepath"),
        error_message=state.get("error_message"),
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
    extraction_prompt = """Extract data, chart parameters, and output filename from the following text.

Return a JSON object with this exact format:
{{
  "data": [{{"label": "label1", "value": number1}}, {{"label": "label2", "value": number2}}, ...],
  "type": "bar" or "line" or null,
  "style": "fd" or "bnr" or null,
  "format": "png" or "svg" or null,
  "filename": "string" or null
}}

Data extraction examples:
- "A=10, B=20, C=30" -> "data": [{{"label": "A", "value": 10}}, {{"label": "B", "value": 20}}, {{"label": "C", "value": 30}}]
- "Monday: 4.1, Tuesday: 4.2" -> "data": [{{"label": "Monday", "value": 4.1}}, {{"label": "Tuesday", "value": 4.2}}]

Parameter extraction examples:
- "bar chart" or "bar graph" or "staafdiagram" or "staaf grafiek" or "balkdiagram" -> "type": "bar"
- "line chart" or "line graph" or "lijngrafiek" or "lijn grafiek" -> "type": "line"
- "FD style" or "FD colors" or "Financial Daily" or "Financieele Dagblad" -> "style": "fd"
- "BNR style" or "BNR colors" -> "style": "bnr"
- "PNG format" or "as PNG" or "save as PNG" -> "format": "png"
- "SVG format" or "as SVG" or "save as SVG" -> "format": "svg"

Filename extraction examples:
- "save as results.png" -> "filename": "results.png"
- "call it quarterly_revenue.svg" -> "filename": "quarterly_revenue.svg"
- "name it sales_chart" -> "filename": "sales_chart"
- "output file charts/output.png" -> "filename": "charts/output.png"
- No filename mentioned -> "filename": null

IMPORTANT:
- Return ONLY the JSON object, no other text
- Set parameters to null if not mentioned in the text
- Always extract the data array
- Extract filename only if explicitly requested

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
        extracted_filename = parsed.get("filename")
        logger.debug(f"extract_data: Extracted parameters from NL - type: {extracted_type}, "
                    f"style: {extracted_style}, format: {extracted_format}, filename: {extracted_filename}")

    except (json.JSONDecodeError, AttributeError) as e:
        # If invalid, create default structure
        logger.error(f"extract_data: Failed to parse JSON: {e}")
        logger.debug(f"extract_data: Problematic JSON: {extracted_json}")
        input_data = '[{"label": "unknown", "value": 0}]'
        extracted_type = None
        extracted_style = None
        extracted_format = None
        extracted_filename = None

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

    # Apply filename priority: CLI flag > in-query > None (fallback in tool)
    # Priority 1: CLI flag (already in state if provided)
    # Priority 2: In-query extraction (extracted_filename)
    # Priority 3: None (will use timestamp fallback in matplotlib_chart_generator)
    output_filename = state.get("output_filename")  # CLI flag takes priority
    if not output_filename and extracted_filename:
        # Use extracted filename from query if no CLI flag
        output_filename = extracted_filename
        logger.info(f"extract_data: Using filename from query: {output_filename}")
    elif output_filename:
        logger.info(f"extract_data: Using filename from CLI flag: {output_filename}")
    else:
        logger.debug("extract_data: No filename specified, will use timestamp fallback")

    # Update state
    return GraphState(
        messages=state["messages"],
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        has_file=state.get("has_file", False),
        config_change=state.get("config_change"),
        input_data=input_data,
        chart_request=chart_request,
        missing_params=state.get("missing_params"),
        output_filename=output_filename,
        final_filepath=state.get("final_filepath"),
        error_message=state.get("error_message"),
    )


def is_categorical_data(data_json: str) -> bool:
    """
    Determine if data is categorical (vs time-series).

    Time-series data contains temporal indicators like months, quarters, or years.
    Categorical data contains generic labels like names, categories, or arbitrary labels.

    Args:
        data_json: JSON string of data points

    Returns:
        True if data is categorical, False if time-series
    """
    import json

    try:
        data = json.loads(data_json)
    except (json.JSONDecodeError, TypeError):
        logger.warning("is_categorical_data: Invalid JSON, defaulting to categorical")
        return True

    if not data:
        return True

    # Time indicators
    time_keywords = [
        'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
        'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september',
        'october', 'november', 'december',
        'q1', 'q2', 'q3', 'q4', 'quarter',
        '2020', '2021', '2022', '2023', '2024', '2025', '2026', '2027', '2028', '2029', '2030'
    ]

    # Check first few labels for time indicators
    for item in data[:3]:  # Check first 3 labels
        label = str(item.get('label', '')).lower()
        if any(keyword in label for keyword in time_keywords):
            logger.info(f"is_categorical_data: Detected time-series pattern in label '{label}'")
            return False  # Time-series

    logger.info("is_categorical_data: No time-series patterns detected, treating as categorical")
    return True  # Categorical


def resolve_ambiguity(state: GraphState) -> GraphState:
    """
    Check for missing chart parameters and determine if clarification is needed.

    This node applies the priority resolution logic and checks if any required
    parameters are still missing after all fallbacks have been tried.

    For chart type:
    - If explicitly set → use it
    - If data is time-series → default to line
    - If data is categorical → mark as missing (need to ask)

    For style:
    - Apply priority: Explicit > Default > Last Used > None
    - If still None → mark as missing (need to ask)

    For format:
    - Always has a fallback to PNG, never missing

    Args:
        state: Current graph state with input_data and chart_request

    Returns:
        Updated state with missing_params populated and chart_request resolved
    """
    from graph_agent.config import load_user_preferences

    prefs = load_user_preferences()
    chart_req = state.get("chart_request") or {"type": None, "style": None, "format": None}
    missing = []

    logger.debug(f"resolve_ambiguity: Initial chart_request: {chart_req}")
    logger.debug(f"resolve_ambiguity: Loaded preferences: {prefs}")

    # Check chart type
    if not chart_req.get("type"):
        # If data is categorical, we need to ask
        if is_categorical_data(state.get("input_data")):
            missing.append("type")
            logger.info("resolve_ambiguity: Type missing for categorical data")
        else:
            # Time-series: default to line
            chart_req["type"] = "line"
            logger.info("resolve_ambiguity: Defaulted type to 'line' for time-series data")

    # Check style (already applied priority logic in extract_data/call_data_tool, but double-check)
    if not chart_req.get("style"):
        chart_req["style"] = (
            prefs.get("default_style") or
            prefs.get("last_used_style") or
            None
        )
        if not chart_req["style"]:
            missing.append("style")
            logger.info("resolve_ambiguity: Style missing (no default or last_used)")

    # Format always has fallback, never missing
    if not chart_req.get("format"):
        chart_req["format"] = (
            prefs.get("default_format") or
            prefs.get("last_used_format") or
            "png"
        )
        logger.debug(f"resolve_ambiguity: Format resolved to: {chart_req['format']}")

    logger.info(f"resolve_ambiguity: Missing parameters: {missing}")
    logger.info(f"resolve_ambiguity: Final chart_request: {chart_req}")

    # Update state
    return GraphState(
        messages=state["messages"],
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        has_file=state.get("has_file", False),
        config_change=state.get("config_change"),
        input_data=state.get("input_data"),
        chart_request=chart_req,
        missing_params=missing if missing else None,
        output_filename=state.get("output_filename"),
        final_filepath=state.get("final_filepath"),
        error_message=state.get("error_message"),
    )


def detect_language(text: str) -> str:
    """
    Detect if text is in Dutch or English based on common keywords.

    Args:
        text: Text to analyze

    Returns:
        "nl" for Dutch, "en" for English
    """
    text_lower = text.lower()

    # Dutch keywords and patterns
    dutch_keywords = [
        "grafiek", "diagram", "maak", "kan je", "wil", "graag",
        "een", "voor", "met", "van", "het", "de", "lijn", "staaf",
        "genereer", "creëer", "toon"
    ]

    # Count Dutch keyword occurrences
    dutch_count = sum(1 for keyword in dutch_keywords if keyword in text_lower)

    # If 2 or more Dutch keywords found, assume Dutch
    if dutch_count >= 2:
        logger.debug(f"detect_language: Detected Dutch ({dutch_count} keywords)")
        return "nl"
    else:
        logger.debug(f"detect_language: Detected English ({dutch_count} Dutch keywords)")
        return "en"


def ask_clarification(state: GraphState) -> GraphState:
    """
    Generate clarification question for missing parameters in user's language.

    This node creates a natural language question asking the user to provide
    the missing chart parameters. Questions are generated in the same language
    as the user's input (Dutch or English).

    Args:
        state: Current graph state with missing_params populated

    Returns:
        Updated state with clarification question added to messages
    """
    missing = state.get("missing_params", [])

    if not missing:
        logger.warning("ask_clarification: Called but no missing params")
        return state

    # Detect user's language from their last message
    user_messages = [msg for msg in state["messages"] if msg["role"] == "user"]
    language = "en"  # Default to English
    if user_messages:
        last_user_msg = user_messages[-1]["content"]
        language = detect_language(last_user_msg)
        logger.info(f"ask_clarification: Detected language: {language}")

    # Generate appropriate question based on what's missing and language
    if language == "nl":
        # Dutch questions
        if "type" in missing and "style" in missing:
            question = "Ik heb je data. Welk type grafiek (staaf/lijn) en welke stijl (FD/BNR)?"
            logger.info("ask_clarification: Asking for both type and style (Dutch)")
        elif "type" in missing:
            question = "Welk type grafiek wil je: staafdiagram of lijngrafiek?"
            logger.info("ask_clarification: Asking for type only (Dutch)")
        elif "style" in missing:
            question = "Welke stijl wil je gebruiken: FD of BNR?"
            logger.info("ask_clarification: Asking for style only (Dutch)")
        else:
            question = "Ik heb meer informatie nodig om je grafiek te maken."
            logger.warning(f"ask_clarification: Unexpected missing params: {missing} (Dutch)")
    else:
        # English questions
        if "type" in missing and "style" in missing:
            question = "I have your data. What type of chart (bar/line) and which style (FD/BNR)?"
            logger.info("ask_clarification: Asking for both type and style (English)")
        elif "type" in missing:
            question = "What type of chart would you like: bar or line?"
            logger.info("ask_clarification: Asking for type only (English)")
        elif "style" in missing:
            question = "Which brand style would you like: FD or BNR?"
            logger.info("ask_clarification: Asking for style only (English)")
        else:
            question = "I need more information to create your chart."
            logger.warning(f"ask_clarification: Unexpected missing params: {missing} (English)")

    # Add question to conversation
    updated_messages = state["messages"] + [{"role": "assistant", "content": question}]

    return GraphState(
        messages=updated_messages,
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        has_file=state.get("has_file", False),
        config_change=state.get("config_change"),
        input_data=state.get("input_data"),
        chart_request=state.get("chart_request"),
        missing_params=missing,
        output_filename=state.get("output_filename"),
        final_filepath=state.get("final_filepath"),
        error_message=state.get("error_message"),
    )


def generate_chart_tool(state: GraphState) -> GraphState:
    """
    Generate chart using matplotlib tool and save to file.

    This node calls the matplotlib_chart_generator tool with data from state
    and saves the generated chart file. It also updates the last_used_style
    and last_used_format in the config file.

    If no custom output_filename is provided, this function extracts a logical
    name from the user's prompt and generates a filename: [logical_name]-[timestamp].[ext]

    Args:
        state: Current graph state with input_data and chart_request populated

    Returns:
        Updated state with final_filepath and success message in messages
    """
    from graph_agent.tools import matplotlib_chart_generator, extract_logical_name
    from graph_agent.config import update_last_used
    from datetime import datetime

    # Get chart parameters
    chart_request = state["chart_request"]
    input_data = state["input_data"]
    output_filename = state.get("output_filename")

    # If no custom filename, generate one with logical name
    if not output_filename:
        # Get user's original prompt (first user message)
        user_messages = [msg for msg in state["messages"] if msg["role"] == "user"]
        if user_messages:
            user_prompt = user_messages[0]["content"]
            logger.debug(f"generate_chart_tool: Extracting logical name from: {user_prompt[:100]}...")

            # Extract logical name using LLM
            llm = get_llm()
            logical_name = extract_logical_name(user_prompt, llm)

            # Generate filename: [logical_name]-[timestamp].[ext]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_filename = f"{logical_name}-{timestamp}.{chart_request['format']}"
            logger.info(f"generate_chart_tool: Generated filename: {output_filename}")
        else:
            # Fallback if no user messages found
            logger.warning("generate_chart_tool: No user messages found, using default naming")
            output_filename = None

    # Generate chart
    filepath = matplotlib_chart_generator(
        data=input_data,
        chart_type=chart_request["type"],
        style=chart_request["style"],
        format=chart_request["format"],
        output_filename=output_filename,
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
        missing_params=state.get("missing_params"),
        output_filename=state.get("output_filename"),
        final_filepath=filepath,
        error_message=state.get("error_message"),
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
            config_change=state.get("config_change"),
            input_data=state.get("input_data"),
            chart_request=state.get("chart_request"),
            missing_params=state.get("missing_params"),
            output_filename=state.get("output_filename"),
            final_filepath=state.get("final_filepath"),
            error_message=state.get("error_message"),
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

Parameter examples (English and Dutch):
- "bar chart" or "staafdiagram" or "staaf grafiek" or "balkdiagram" -> "type": "bar"
- "line chart" or "lijngrafiek" or "lijn grafiek" -> "type": "line"
- "FD style" or "Financieele Dagblad" -> "style": "fd"
- "BNR style" -> "style": "bnr"

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
            config_change=state.get("config_change"),
            input_data=data_json,
            chart_request=chart_request,
            missing_params=state.get("missing_params"),
            output_filename=state.get("output_filename"),
            final_filepath=state.get("final_filepath"),
            error_message=None,  # No error
        )

    except ValueError as e:
        # Error parsing Excel file - add error message to conversation
        logger.error(f"call_data_tool: Error parsing Excel file: {e}")
        error_message = str(e)
        updated_messages = state["messages"] + [
            {"role": "assistant", "content": error_message}
        ]

        # Return state with error message
        # Set error_message to signal that an error occurred and workflow should end
        return GraphState(
            messages=updated_messages,
            interaction_mode=state["interaction_mode"],
            intent=state["intent"],
            has_file=state.get("has_file", False),
            config_change=state.get("config_change"),
            input_data=state.get("input_data"),
            chart_request=state.get("chart_request"),
            missing_params=state.get("missing_params"),
            output_filename=state.get("output_filename"),
            final_filepath=state.get("final_filepath"),
            error_message=error_message,  # Set error to prevent continuing to chart generation
        )


def route_after_call_data_tool(state: GraphState) -> str:
    """
    Route after call_data_tool based on whether an error occurred.

    If error_message is set (file not found, parse error, etc.):
    - Route to END (error message already in conversation)

    If no error:
    - Continue to resolve_ambiguity

    Args:
        state: Current graph state with potential error_message

    Returns:
        Name of next node to execute or END
    """
    error_msg = state.get("error_message")
    logger.debug(f"route_after_call_data_tool: error_message={error_msg}")

    if error_msg:
        logger.info("route_after_call_data_tool: Error occurred, routing to END")
        return "END"
    else:
        logger.info("route_after_call_data_tool: No error, routing to resolve_ambiguity")
        return "resolve_ambiguity"


def route_after_intent(state: GraphState) -> str:
    """
    Route to appropriate node based on detected intent and file presence.

    For make_chart intent:
    - If has_file=True: Route to call_data_tool to parse Excel file
    - If has_file=False: Route to extract_data to extract from natural language

    For set_config intent:
    - Route to handle_config to update user preferences

    For off_topic intent:
    - Route to report_error

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
        logger.info("route_after_intent: Routing to report_error (off-topic)")
        return "report_error"
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
        logger.warning(f"route_after_intent: Unknown intent '{intent}', routing to report_error")
        return "report_error"


def route_after_resolve(state: GraphState) -> str:
    """
    Route based on missing parameters and interaction mode.

    If parameters are missing:
    - Conversational mode: Ask clarification questions
    - Direct mode: Report error and exit (Story 8)

    If all parameters present:
    - Continue to chart generation

    Args:
        state: Current graph state with missing_params populated

    Returns:
        Name of next node to execute
    """
    missing = state.get("missing_params")
    mode = state["interaction_mode"]

    logger.debug(f"route_after_resolve: Missing={missing}, Mode={mode}")

    if missing:
        if mode == "conversational":
            logger.info("route_after_resolve: Routing to ask_clarification (conversational mode)")
            return "ask_clarification"
        else:
            # Direct mode with missing params - fail with error
            logger.info("route_after_resolve: Routing to report_error (direct mode with missing params)")
            return "report_error"
    else:
        logger.info("route_after_resolve: All params present, routing to generate_chart")
        return "generate_chart"


def create_graph() -> Any:
    """
    Create and compile the LangGraph workflow.

    The workflow consists of:
    1. parse_intent: Analyzes user request and determines intent and file presence
    2. Conditional routing:
       - If off_topic: report_error -> END
       - If set_config: handle_config -> END
       - If make_chart + has_file: call_data_tool -> resolve_ambiguity -> ...
       - If make_chart + no file: extract_data -> resolve_ambiguity -> ...
    3. report_error: Handles off-topic requests and ambiguity errors (Story 8)
    4. handle_config: Handles user preference changes (default style/format)
    5. call_data_tool: Parses Excel file and extracts data
    6. extract_data: Extracts structured data from natural language
    7. resolve_ambiguity: Checks for missing parameters and applies defaults
    8. Conditional routing after resolve_ambiguity:
       - If missing params + conversational: ask_clarification -> END (return to REPL)
       - If missing params + direct: report_error -> END (Story 8)
       - If all params present: generate_chart -> END
    9. ask_clarification: Generates clarifying questions for missing parameters
    10. generate_chart: Creates chart file using matplotlib

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("parse_intent", parse_intent)
    workflow.add_node("report_error", report_error)
    workflow.add_node("handle_config", handle_config)
    workflow.add_node("call_data_tool", call_data_tool)
    workflow.add_node("extract_data", extract_data)
    workflow.add_node("resolve_ambiguity", resolve_ambiguity)
    workflow.add_node("ask_clarification", ask_clarification)
    workflow.add_node("generate_chart", generate_chart_tool)

    # Set entry point
    workflow.set_entry_point("parse_intent")

    # Add conditional routing after parse_intent
    workflow.add_conditional_edges(
        "parse_intent",
        route_after_intent,
        {
            "report_error": "report_error",
            "handle_config": "handle_config",
            "call_data_tool": "call_data_tool",
            "extract_data": "extract_data",
        },
    )

    # Add conditional routing after call_data_tool (check for errors)
    workflow.add_conditional_edges(
        "call_data_tool",
        route_after_call_data_tool,
        {
            "END": END,
            "resolve_ambiguity": "resolve_ambiguity",
        },
    )

    # Add edge for extract_data -> ambiguity resolution
    workflow.add_edge("extract_data", "resolve_ambiguity")

    # Add conditional routing after resolve_ambiguity
    workflow.add_conditional_edges(
        "resolve_ambiguity",
        route_after_resolve,
        {
            "ask_clarification": "ask_clarification",
            "report_error": "report_error",  # NEW: Direct mode ambiguity errors
            "generate_chart": "generate_chart",
        },
    )

    # Add terminal edges
    workflow.add_edge("report_error", END)
    workflow.add_edge("handle_config", END)
    workflow.add_edge("ask_clarification", END)  # Returns to REPL for user response
    workflow.add_edge("generate_chart", END)

    # Compile and return
    return workflow.compile()
