"""CLI entry point for Graph Agent."""

import click
from dotenv import load_dotenv
from graph_agent.agent import create_graph
from graph_agent.state import GraphState

# Load environment variables from .env file
load_dotenv()


def run_direct_mode(
    prompt: str, style: str = "fd", format: str = "png", chart_type: str = "bar"
) -> None:
    """
    Execute the agent in direct mode with a single prompt.

    Args:
        prompt: User's request/question
        style: Brand style ('fd' or 'bnr'), defaults to 'fd'
        format: Output format ('png' or 'svg'), defaults to 'png'
        chart_type: Chart type ('bar' or 'line'), defaults to 'bar'
    """
    graph = create_graph()

    # Build chart_request with provided or default parameters
    chart_request = {"type": chart_type, "style": style, "format": format}

    # Create initial state
    initial_state = GraphState(
        messages=[{"role": "user", "content": prompt}],
        interaction_mode="direct",
        intent="unknown",
        input_data=None,
        chart_request=chart_request,
        final_filepath=None,
    )

    # Invoke graph
    result = graph.invoke(initial_state)

    # Print assistant response
    assistant_message = result["messages"][-1]["content"]
    print(assistant_message)


def run_conversational_mode() -> None:
    """
    Execute the agent in conversational mode (REPL).

    Starts a read-eval-print loop where users can have multiple interactions.
    Session state is maintained across turns within a single session.
    Exits when user types 'exit' or 'quit'.
    """
    graph = create_graph()

    # Print welcome message
    print("Welcome to Graph Agent! I can help you create bar and line charts.")
    print("Type 'exit' or 'quit' to leave.")
    print()

    # Initialize session state ONCE at the start
    session_state = GraphState(
        messages=[],
        interaction_mode="conversational",
        intent="unknown",
        input_data=None,
        chart_request={"type": None, "style": None, "format": None},
        final_filepath=None,
    )

    while True:
        # Get user input
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        # Check for exit commands
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        # Skip empty input
        if not user_input:
            continue

        # Append user message to session state
        updated_messages = session_state["messages"] + [
            {"role": "user", "content": user_input}
        ]

        # Update session state with new user message
        session_state = GraphState(
            messages=updated_messages,
            interaction_mode=session_state["interaction_mode"],
            intent=session_state.get("intent", "unknown"),
            input_data=session_state.get("input_data"),
            chart_request=session_state.get("chart_request") or {"type": None, "style": None, "format": None},
            final_filepath=session_state.get("final_filepath"),
        )

        # Invoke graph with current session state
        session_state = graph.invoke(session_state)

        # Get assistant response
        assistant_message = session_state["messages"][-1]["content"]

        # Print assistant response
        print(assistant_message)
        print()


@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--style",
    type=click.Choice(["fd", "bnr"], case_sensitive=False),
    default="fd",
    help="Brand style for the chart (default: fd)",
)
@click.option(
    "--format",
    type=click.Choice(["png", "svg"], case_sensitive=False),
    default="png",
    help="Output format for the chart (default: png)",
)
@click.option(
    "--type",
    type=click.Choice(["bar", "line"], case_sensitive=False),
    default="bar",
    help="Chart type (default: bar)",
)
def main(
    prompt: str = None, style: str = "fd", format: str = "png", type: str = "bar"
) -> None:
    """
    Graph Agent CLI - Create brand-compliant charts from natural language.

    Usage:
        graph-agent                                     Start conversational mode (REPL)
        graph-agent "your request"                      Execute in direct mode and exit
        graph-agent "your request" --style fd --format png --type bar    Generate chart directly

    Examples:
        graph-agent "create a bar chart"
        graph-agent "A=10, B=20, C=30" --style fd --format png --type bar
        graph-agent
    """
    try:
        if prompt:
            # Direct mode
            run_direct_mode(prompt, style=style, format=format, chart_type=type)
        else:
            # Conversational mode
            run_conversational_mode()
    except ValueError as e:
        # Handle configuration errors (like missing API key)
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
