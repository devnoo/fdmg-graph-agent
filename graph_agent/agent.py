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
    Parse user intent to determine if request is chart-related or off-topic.

    This node uses the Gemini LLM to analyze the user's message and classify
    it as either a chart-related request ('make_chart') or an off-topic request
    ('off_topic').

    Args:
        state: Current graph state containing messages

    Returns:
        Updated state with intent field populated
    """
    llm = get_llm()

    # Get the last user message
    user_message = state["messages"][-1]["content"]
    logger.debug(f"parse_intent: Analyzing message: {user_message[:100]}...")

    # Create a prompt for intent detection
    system_prompt = """Analyze the following user request and determine if it's about creating a chart or graph.

Chart-related indicators:
- Keywords: chart, graph, bar, line, plot, visualize, visualization, grafiek, diagram
- Data patterns: "A=10, B=20", "Monday: 4.1", "Q1=120, Q2=150"
- Requests with structured numerical data (even without explicit chart keywords)

Respond with EXACTLY one of these two words:
- 'make_chart' if the request is about creating a chart/graph OR contains structured data (label=value pairs)
- 'off_topic' if the request is about anything else (like making sandwiches, booking appointments, etc.)

User request: {request}

Your response (one word only):"""

    prompt = system_prompt.format(request=user_message)

    # Call LLM
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()
    logger.debug(f"parse_intent: LLM returned intent: {intent}")

    # Ensure intent is valid
    if intent not in ["make_chart", "off_topic"]:
        logger.warning(f"parse_intent: Invalid intent '{intent}', defaulting to 'off_topic'")
        intent = "off_topic"  # Default to off_topic if unclear

    # Fallback: Check for obvious data patterns if LLM said off_topic
    if intent == "off_topic":
        import re

        # Look for patterns like "A=10", "Monday: 4.1", "Q1 = 120"
        data_pattern = r"[A-Za-z0-9]+\s*[=:]\s*[0-9,.]+"
        if re.search(data_pattern, user_message):
            logger.info("parse_intent: Detected data pattern, overriding to 'make_chart'")
            intent = "make_chart"

    logger.info(f"parse_intent: Final intent: {intent}")

    # Update state
    return GraphState(
        messages=state["messages"],
        interaction_mode=state["interaction_mode"],
        intent=intent,
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

    # Apply defaults for missing parameters
    if chart_request["type"] is None:
        chart_request["type"] = "bar"
    if chart_request["style"] is None:
        chart_request["style"] = "fd"
    if chart_request["format"] is None:
        chart_request["format"] = "png"

    logger.info(f"extract_data: Final chart_request: type={chart_request['type']}, "
               f"style={chart_request['style']}, format={chart_request['format']}")

    # Update state
    return GraphState(
        messages=state["messages"],
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        input_data=input_data,
        chart_request=chart_request,
        final_filepath=state.get("final_filepath"),
    )


def generate_chart_tool(state: GraphState) -> GraphState:
    """
    Generate chart using matplotlib tool and save to file.

    This node calls the matplotlib_chart_generator tool with data from state
    and saves the generated chart file.

    Args:
        state: Current graph state with input_data and chart_request populated

    Returns:
        Updated state with final_filepath and success message in messages
    """
    from graph_agent.tools import matplotlib_chart_generator

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

    # Add success message
    updated_messages = state["messages"] + [
        {"role": "assistant", "content": f"Chart saved: {filepath}"}
    ]

    # Update state
    return GraphState(
        messages=updated_messages,
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        input_data=state["input_data"],
        chart_request=state["chart_request"],
        final_filepath=filepath,
    )


def route_after_intent(state: GraphState) -> str:
    """
    Route to appropriate node based on detected intent.

    For make_chart intent:
    - Always proceed to extract_data node (handles both direct and conversational modes)
    - Direct mode: extract_data uses pre-set chart_request parameters from CLI flags
    - Conversational mode: extract_data extracts parameters from natural language

    Args:
        state: Current graph state with intent populated

    Returns:
        Name of next node to execute
    """
    intent = state["intent"]
    mode = state["interaction_mode"]
    logger.debug(f"route_after_intent: Intent={intent}, Mode={mode}")

    if state["intent"] == "off_topic":
        logger.info("route_after_intent: Routing to reject_task (off-topic)")
        return "reject_task"
    elif state["intent"] == "make_chart":
        # Proceed to extract_data for both direct and conversational modes
        logger.info(f"route_after_intent: Routing to extract_data ({mode} mode)")
        return "extract_data"
    else:
        logger.warning(f"route_after_intent: Unknown intent '{intent}', routing to reject_task")
        return "reject_task"


def create_graph() -> Any:
    """
    Create and compile the LangGraph workflow.

    The workflow consists of:
    1. parse_intent: Analyzes user request and determines intent
    2. Conditional routing:
       - If off_topic: reject_task -> END
       - If make_chart: extract_data -> generate_chart -> END
    3. extract_data: Extracts structured data from natural language
    4. generate_chart: Creates chart file using matplotlib

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("parse_intent", parse_intent)
    workflow.add_node("reject_task", reject_task)
    workflow.add_node("extract_data", extract_data)
    workflow.add_node("generate_chart", generate_chart_tool)

    # Set entry point
    workflow.set_entry_point("parse_intent")

    # Add conditional routing after parse_intent
    workflow.add_conditional_edges(
        "parse_intent",
        route_after_intent,
        {"reject_task": "reject_task", "extract_data": "extract_data"},
    )

    # Add edges for chart generation flow
    workflow.add_edge("extract_data", "generate_chart")

    # Add terminal edges
    workflow.add_edge("reject_task", END)
    workflow.add_edge("generate_chart", END)

    # Compile and return
    return workflow.compile()
