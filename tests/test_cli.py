"""Tests for CLI functionality."""

from unittest.mock import Mock, patch
from click.testing import CliRunner
from graph_agent import cli


def test_cli_command_exists():
    """Test that the main CLI command exists."""
    assert hasattr(cli, "main")
    assert callable(cli.main)


def test_cli_direct_mode_with_off_topic():
    """Test CLI in direct mode with off-topic request."""
    runner = CliRunner()

    # Mock the graph to return off-topic response
    with patch("graph_agent.cli.create_graph") as mock_create_graph:
        mock_graph = Mock()
        expected_response = "I can only help you create charts. Please ask me to make a bar or line chart."
        mock_graph.invoke.return_value = {
            "messages": [
                {"role": "user", "content": "make me a sandwich"},
                {"role": "assistant", "content": expected_response},
            ],
            "interaction_mode": "direct",
            "intent": "off_topic",
        }
        mock_create_graph.return_value = mock_graph

        result = runner.invoke(cli.main, ["make me a sandwich"])

        # Story 8: Off-topic requests exit with code 1
        assert result.exit_code == 1
        assert "I can only help you create charts" in result.output


def test_cli_direct_mode_with_chart_request():
    """Test CLI in direct mode with chart request."""
    runner = CliRunner()

    # Mock the graph to return chart response
    with patch("graph_agent.cli.create_graph") as mock_create_graph:
        mock_graph = Mock()
        mock_graph.invoke.return_value = {
            "messages": [
                {"role": "user", "content": "create a bar chart"},
                {
                    "role": "assistant",
                    "content": "Chart generation is not yet implemented. Check back soon!",
                },
            ],
            "interaction_mode": "direct",
            "intent": "make_chart",
        }
        mock_create_graph.return_value = mock_graph

        result = runner.invoke(cli.main, ["create a bar chart"])

        assert result.exit_code == 0
        assert "not yet implemented" in result.output


def test_cli_conversational_mode_starts_repl():
    """Test CLI in conversational mode starts with welcome message."""
    runner = CliRunner()

    # Mock the graph
    with patch("graph_agent.cli.create_graph") as mock_create_graph:
        mock_graph = Mock()
        mock_create_graph.return_value = mock_graph

        # Simulate user typing 'exit'
        result = runner.invoke(cli.main, input="exit\n")

        assert result.exit_code == 0
        assert (
            "Welcome to Graph Agent" in result.output or "Graph Agent" in result.output
        )


def test_cli_conversational_mode_exit_command():
    """Test that 'exit' command exits the REPL."""
    runner = CliRunner()

    with patch("graph_agent.cli.create_graph") as mock_create_graph:
        mock_graph = Mock()
        mock_create_graph.return_value = mock_graph

        result = runner.invoke(cli.main, input="exit\n")

        assert result.exit_code == 0
        assert "Goodbye" in result.output or result.exit_code == 0


def test_cli_conversational_mode_quit_command():
    """Test that 'quit' command exits the REPL."""
    runner = CliRunner()

    with patch("graph_agent.cli.create_graph") as mock_create_graph:
        mock_graph = Mock()
        mock_create_graph.return_value = mock_graph

        result = runner.invoke(cli.main, input="quit\n")

        assert result.exit_code == 0


def test_cli_conversational_mode_handles_requests():
    """Test that conversational mode handles user requests."""
    runner = CliRunner()

    with patch("graph_agent.cli.create_graph") as mock_create_graph:
        mock_graph = Mock()
        expected_msg = "I can only help you create charts. Please ask me to make a bar or line chart."
        mock_graph.invoke.return_value = {
            "messages": [
                {"role": "user", "content": "test"},
                {"role": "assistant", "content": expected_msg},
            ],
            "interaction_mode": "conversational",
            "intent": "off_topic",
        }
        mock_create_graph.return_value = mock_graph

        result = runner.invoke(cli.main, input="test\nexit\n")

        assert result.exit_code == 0
        # Verify the graph was called
        assert mock_graph.invoke.called


def test_cli_no_args_starts_conversational():
    """Test that CLI with no arguments starts conversational mode."""
    runner = CliRunner()

    with patch("graph_agent.cli.create_graph") as mock_create_graph:
        mock_graph = Mock()
        mock_create_graph.return_value = mock_graph

        result = runner.invoke(cli.main, input="exit\n")

        assert result.exit_code == 0
        # Should show welcome or prompt
        assert len(result.output) > 0


def test_run_direct_mode():
    """Test run_direct_mode function."""
    import pytest

    with patch("graph_agent.cli.create_graph") as mock_create_graph:
        mock_graph = Mock()
        mock_graph.invoke.return_value = {
            "messages": [
                {"role": "user", "content": "test"},
                {"role": "assistant", "content": "Chart saved: /tmp/chart.png"},
            ],
            "interaction_mode": "direct",
            "intent": "make_chart",
        }
        mock_create_graph.return_value = mock_graph

        # run_direct_mode now calls sys.exit(), so we need to catch it
        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                cli.run_direct_mode("test")
            # Should exit with code 0 for success
            assert exc_info.value.code == 0
            # Verify print was called with response
            assert mock_print.called


def test_run_conversational_mode():
    """Test run_conversational_mode function."""
    with patch("graph_agent.cli.create_graph") as mock_create_graph:
        mock_graph = Mock()
        mock_graph.invoke.return_value = {
            "messages": [
                {"role": "user", "content": "test"},
                {"role": "assistant", "content": "response"},
            ],
            "interaction_mode": "conversational",
            "intent": "off_topic",
        }
        mock_create_graph.return_value = mock_graph

        with patch("builtins.input", side_effect=["test", "exit"]):
            with patch("builtins.print") as mock_print:
                cli.run_conversational_mode()
                # Verify welcome and goodbye messages
                assert mock_print.called
