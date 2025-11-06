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
    )


def create_graph() -> Any:
    """
    Create and compile the LangGraph workflow.

    The workflow consists of:
    1. parse_intent: Analyzes user request and determines intent
    2. reject_task: Generates appropriate response based on intent

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("parse_intent", parse_intent)
    workflow.add_node("reject_task", reject_task)

    # Set entry point
    workflow.set_entry_point("parse_intent")

    # Add edges
    workflow.add_edge("parse_intent", "reject_task")
    workflow.add_edge("reject_task", END)

    # Compile and return
    return workflow.compile()
