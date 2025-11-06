"""CLI entry point for Graph Agent."""

import click
from graph_agent.agent import create_graph
from graph_agent.state import GraphState


def run_direct_mode(prompt: str) -> None:
    """
    Execute the agent in direct mode with a single prompt.

    Args:
        prompt: User's request/question
    """
    graph = create_graph()

    # Create initial state
    initial_state = GraphState(
        messages=[{"role": "user", "content": prompt}],
        interaction_mode="direct",
        intent="unknown",
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
    Exits when user types 'exit' or 'quit'.
    """
    graph = create_graph()

    # Print welcome message
    print("Welcome to Graph Agent! I can help you create bar and line charts.")
    print("Type 'exit' or 'quit' to leave.")
    print()

    # Initialize conversation state
    messages = []

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

        # Add user message
        messages.append({"role": "user", "content": user_input})

        # Create state for this turn
        current_state = GraphState(
            messages=messages.copy(),
            interaction_mode="conversational",
            intent="unknown",
        )

        # Invoke graph
        result = graph.invoke(current_state)

        # Get assistant response
        assistant_message = result["messages"][-1]["content"]

        # Update messages with assistant response
        messages.append({"role": "assistant", "content": assistant_message})

        # Print assistant response
        print(assistant_message)
        print()


@click.command()
@click.argument("prompt", required=False)
def main(prompt: str = None) -> None:
    """
    Graph Agent CLI - Create brand-compliant charts from natural language.

    Usage:
        graph-agent                     Start conversational mode (REPL)
        graph-agent "your request"      Execute in direct mode and exit

    Examples:
        graph-agent "create a bar chart"
        graph-agent
    """
    try:
        if prompt:
            # Direct mode
            run_direct_mode(prompt)
        else:
            # Conversational mode
            run_conversational_mode()
    except ValueError as e:
        # Handle configuration errors (like missing API key)
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
