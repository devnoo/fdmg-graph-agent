"""LangGraph agent implementation for Graph Agent."""

import os
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from graph_agent.state import GraphState


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

    # Create a prompt for intent detection
    system_prompt = """Analyze the following user request and determine if it's about creating a chart or graph.

Chart-related keywords include: chart, graph, bar, line, plot, visualize, visualization, data visualization.

Respond with EXACTLY one of these two words:
- 'make_chart' if the request is about creating any type of chart or graph
- 'off_topic' if the request is about anything else

User request: {request}

Your response (one word only):"""

    prompt = system_prompt.format(request=user_message)

    # Call LLM
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()

    # Ensure intent is valid
    if intent not in ["make_chart", "off_topic"]:
        intent = "off_topic"  # Default to off_topic if unclear

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
    Extract structured data from user's natural language prompt using Gemini.

    This node uses the LLM to parse the user's message and extract label-value
    pairs in JSON format.

    Args:
        state: Current graph state containing user message

    Returns:
        Updated state with input_data field populated with JSON string
    """
    import json

    llm = get_llm()

    # Get the last user message
    user_message = state["messages"][-1]["content"]

    # Create prompt for data extraction
    extraction_prompt = """Extract all label-value pairs from the following text.

Return the data as a JSON array with this exact format:
[{{"label": "label1", "value": number1}}, {{"label": "label2", "value": number2}}, ...]

Examples:
- "A=10, B=20, C=30" -> [{{"label": "A", "value": 10}}, {{"label": "B", "value": 20}}, {{"label": "C", "value": 30}}]
- "Monday: 4.1, Tuesday: 4.2" -> [{{"label": "Monday", "value": 4.1}}, {{"label": "Tuesday", "value": 4.2}}]
- "Q1: 120, Q2: 150" -> [{{"label": "Q1", "value": 120}}, {{"label": "Q2", "value": 150}}]

IMPORTANT: Return ONLY the JSON array, no other text.

Text to extract from: {text}

JSON array:"""

    prompt = extraction_prompt.format(text=user_message)

    # Call LLM
    response = llm.invoke(prompt)
    extracted_json = response.content.strip()

    # Validate JSON
    try:
        json.loads(extracted_json)  # Validate it's proper JSON
    except json.JSONDecodeError:
        # If invalid, create a default structure
        extracted_json = '[{"label": "unknown", "value": 0}]'

    # Update state
    return GraphState(
        messages=state["messages"],
        interaction_mode=state["interaction_mode"],
        intent=state["intent"],
        input_data=extracted_json,
        chart_request=state.get("chart_request"),
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

    Args:
        state: Current graph state with intent populated

    Returns:
        Name of next node to execute
    """
    if state["intent"] == "off_topic":
        return "reject_task"
    elif state["intent"] == "make_chart":
        # Check if chart_request is present (direct mode with flags)
        if state.get("chart_request"):
            return "extract_data"
        else:
            # No chart parameters, reject for now (Story 4+ will handle this)
            return "reject_task"
    else:
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
