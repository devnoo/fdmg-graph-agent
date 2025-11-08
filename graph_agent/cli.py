"""CLI entry point for Graph Agent."""

import sys
import logging
import click
from dotenv import load_dotenv
from graph_agent.agent import create_graph
from graph_agent.state import GraphState

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_direct_mode(
    prompt: str, style: str = "fd", format: str = "png", chart_type: str = "bar", output_file: str = None
) -> None:
    """
    Execute the agent in direct mode with a single prompt.

    Args:
        prompt: User's request/question
        style: Brand style ('fd' or 'bnr'), defaults to 'fd'
        format: Output format ('png' or 'svg'), defaults to 'png'
        chart_type: Chart type ('bar' or 'line'), defaults to 'bar'
        output_file: Custom output filename, defaults to None
    """
    logger.info(f"Starting direct mode with prompt: {prompt[:50]}...")
    logger.debug(f"Parameters: type={chart_type}, style={style}, format={format}, output_file={output_file}")

    graph = create_graph()

    # Build chart_request with provided or default parameters
    chart_request = {"type": chart_type, "style": style, "format": format}

    # Create initial state
    initial_state = GraphState(
        messages=[{"role": "user", "content": prompt}],
        interaction_mode="direct",
        intent="unknown",
        has_file=False,
        config_change=None,
        input_data=None,
        chart_request=chart_request,
        missing_params=None,
        output_filename=output_file,
        final_filepath=None,
        error_message=None,
    )

    # Invoke graph
    logger.debug("Invoking graph for direct mode")
    result = graph.invoke(initial_state)
    logger.debug(f"Graph execution complete. Intent: {result['intent']}")

    # Get assistant response
    assistant_message = result["messages"][-1]["content"]

    # Check if this is an error (either starts with "Error:" or is a rejection message)
    is_error = assistant_message.startswith("Error:") or assistant_message.startswith("I can only")

    if is_error:
        # Print error to stderr and exit with code 1
        print(assistant_message, file=sys.stderr)
        logger.info("Direct mode failed with error")
        sys.exit(1)
    else:
        # Success: print to stdout and exit with code 0
        print(assistant_message)
        logger.info("Direct mode completed successfully")
        sys.exit(0)


def run_conversational_mode() -> None:
    """
    Execute the agent in conversational mode (REPL).

    Starts a read-eval-print loop where users can have multiple interactions.
    Session state is maintained across turns within a single session.
    Exits when user types 'exit' or 'quit'.
    """
    logger.info("Starting conversational mode (REPL)")
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
        has_file=False,
        config_change=None,
        input_data=None,
        chart_request={"type": None, "style": None, "format": None},
        missing_params=None,
        output_filename=None,
        final_filepath=None,
        error_message=None,
    )
    logger.debug("Initialized session state")

    turn_count = 0
    while True:
        # Get user input
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.info("Received EOF/KeyboardInterrupt, exiting")
            print("\nGoodbye!")
            break

        # Check for exit commands
        if user_input.lower() in ["exit", "quit"]:
            logger.info(f"User requested exit with '{user_input}'")
            print("Goodbye!")
            break

        # Skip empty input
        if not user_input:
            continue

        turn_count += 1
        logger.info(f"Turn {turn_count}: User input: {user_input[:50]}...")
        logger.debug(f"Current message history length: {len(session_state['messages'])}")

        # Append user message to session state
        updated_messages = session_state["messages"] + [
            {"role": "user", "content": user_input}
        ]

        # Update session state with new user message
        session_state = GraphState(
            messages=updated_messages,
            interaction_mode=session_state["interaction_mode"],
            intent=session_state.get("intent", "unknown"),
            has_file=session_state.get("has_file", False),
            config_change=session_state.get("config_change"),
            input_data=session_state.get("input_data"),
            chart_request=session_state.get("chart_request") or {"type": None, "style": None, "format": None},
            missing_params=session_state.get("missing_params"),
            output_filename=session_state.get("output_filename"),
            final_filepath=session_state.get("final_filepath"),
            error_message=session_state.get("error_message"),
        )
        logger.debug(f"Updated session state with user message (total messages: {len(session_state['messages'])})")

        # Invoke graph with current session state
        logger.debug("Invoking graph with session state")
        session_state = graph.invoke(session_state)
        logger.debug(f"Graph execution complete. Intent: {session_state['intent']}, "
                    f"Chart params: {session_state.get('chart_request')}")
        logger.debug(f"Message history now has {len(session_state['messages'])} messages")

        # Get assistant response
        assistant_message = session_state["messages"][-1]["content"]
        logger.info(f"Assistant response: {assistant_message[:100]}...")

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
@click.option(
    "--output-file",
    type=str,
    default=None,
    help="Custom output filename (e.g., 'my_chart.png' or 'charts/output.svg')",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Logging level (default: INFO)",
)
def main(
    prompt: str = None, style: str = "fd", format: str = "png", type: str = "bar", output_file: str = None, log_level: str = "INFO"
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
    # Set logging level based on CLI parameter
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))
    logger.debug(f"Logging level set to {log_level}")

    try:
        if prompt:
            # Direct mode
            run_direct_mode(prompt, style=style, format=format, chart_type=type, output_file=output_file)
        else:
            # Conversational mode
            run_conversational_mode()
    except ValueError as e:
        # Handle configuration errors (like missing API key)
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
