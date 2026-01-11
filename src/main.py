"""Main CLI entry point for Facebook Surfer agent."""

import asyncio
import sys
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

import click
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from src.agents.facebook_surfer import FacebookSurferAgent
from src.session import FacebookSessionManager, set_global_session
from src.tools.base import set_current_async_page, set_current_page

# Load environment variables from .env file
load_dotenv()


def print_banner():
    """Print application banner."""
    click.echo("=" * 60)
    click.echo("  Facebook Surfer Agent - DeepAgents + Playwright")
    click.echo("=" * 60)
    click.echo("")


@contextmanager
def init_session(login: bool = False, profile: str = "./profiles/facebook"):
    """Initialize or restore browser session (context manager).

    Args:
        login: Whether to start login flow
        profile: Path to browser profile directory

    Yields:
        FacebookSessionManager with active browser connection
    """
    session = FacebookSessionManager(profile_dir=Path(profile))

    with sync_playwright() as p:
        if login:
            click.echo("Starting human-in-the-loop login flow...")
            click.echo("You have 3 minutes to log in manually.")
            click.echo("")
            success = session.start_login()
            if not success:
                click.echo("Login failed or timed out", err=True)
                sys.exit(1)
            click.echo("Login successful! Session saved.")
        else:
            click.echo("Restoring existing session...")
            success = session.restore_session(p.chromium)
            if not success:
                click.echo("No valid session found.")
                click.echo("Run with --login first to create a session.")
                sys.exit(1)
            click.echo("Session restored!")

        # Set global session for tools
        set_global_session(session)
        if session.get_page():
            set_current_page(session.get_page())

        yield session


def run_single_task(agent: FacebookSurferAgent, task: str, stream: bool, thread_id: str):
    """Run a single task and exit.

    Args:
        agent: FacebookSurferAgent instance
        task: Task description
        stream: Whether to stream execution
        thread_id: Conversation thread ID
    """
    click.echo(f"\nExecuting task: {task}")
    click.echo("-" * 60)

    if stream:
        for event in agent.stream(task, thread_id=thread_id):
            # Parse and display events
            if "messages" in event and event["messages"]:
                latest_msg = event["messages"][-1]
                if hasattr(latest_msg, "content"):
                    content = latest_msg.content
                    if isinstance(content, str):
                        click.echo(f"[Update] {content}")
                    elif isinstance(content, list):
                        for part in content:
                            if isinstance(part, str):
                                click.echo(f"[Update] {part}")
                            elif isinstance(part, dict):
                                # Extract text from content blocks
                                text = part.get("text", str(part))
                                click.echo(f"[Update] {text}")
            if "__interrupt__" in event:
                click.echo(f"[Interrupt] {event['__interrupt__']}")
                # Handle HITL here if needed
                click.echo("Human intervention required. Check agent state.")
    else:
        result = agent.invoke(task, thread_id=thread_id)
        click.echo("\nResult:")
        if "messages" in result and result["messages"]:
            latest_msg = result["messages"][-1]
            if hasattr(latest_msg, "content"):
                content = latest_msg.content
                # Handle content that's a list of content blocks
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            click.echo(block.get("text", str(block)))
                        elif isinstance(block, str):
                            click.echo(block)
                        else:
                            click.echo(str(block))
                elif content:  # Non-empty string or other truthy value
                    click.echo(content)
        else:
            click.echo(result)

    click.echo("-" * 60)
    click.echo("Task complete!")


def run_interactive(agent: FacebookSurferAgent, thread_id: str):
    """Run in interactive mode.

    Args:
        agent: FacebookSurferAgent instance
        thread_id: Conversation thread ID
    """
    click.echo("\nEntering interactive mode.")
    click.echo("Commands: 'exit', 'quit', 'clear', 'state', 'tools'")
    click.echo("")

    while True:
        try:
            task = click.prompt("Task", default="", show_default=False)

            if not task.strip():
                continue

            if task.lower() in ["exit", "quit"]:
                click.echo("Goodbye!")
                break

            if task.lower() == "clear":
                click.echo("\033c", nl=False)
                continue

            if task.lower() == "state":
                state = agent.get_state(thread_id)
                click.echo(f"Current state: {state}")
                continue

            if task.lower() == "tools":
                click.echo(agent.get_tool_summary())
                continue

            # Execute task
            result = agent.invoke(task, thread_id=thread_id)
            click.echo("\nResult:")
            if "messages" in result and result["messages"]:
                latest_msg = result["messages"][-1]
                if hasattr(latest_msg, "content"):
                    content = latest_msg.content
                    # Handle content that's a list of content blocks
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                click.echo(block.get("text", str(block)))
                            elif isinstance(block, str):
                                click.echo(block)
                            else:
                                click.echo(str(block))
                    elif content:  # Non-empty string or other truthy value
                        click.echo(content)
            click.echo("")

        except KeyboardInterrupt:
            click.echo("\nUse 'exit' to quit.")
        except EOFError:
            click.echo("\nGoodbye!")
            break
        except Exception as e:
            click.echo(f"Error: {e}", err=True)


@asynccontextmanager
async def async_init_session(login: bool = False, profile: str = "./profiles/facebook"):
    """Initialize or restore browser session (async context manager).

    Args:
        login: Whether to start login flow
        profile: Path to browser profile directory

    Yields:
        FacebookSessionManager with active browser connection
    """
    session = FacebookSessionManager(profile_dir=Path(profile))

    async with async_playwright() as p:
        if login:
            click.echo("Starting human-in-the-loop login flow...")
            click.echo("You have 3 minutes to log in manually.")
            click.echo("")
            success = await session.start_login_async()
            if not success:
                click.echo("Login failed or timed out", err=True)
                sys.exit(1)
            click.echo("Login successful! Session saved.")
        else:
            click.echo("Restoring existing session...")
            success = await session.restore_session_async(p.chromium)
            if not success:
                click.echo("No valid session found.")
                click.echo("Run with --login first to create a session.")
                sys.exit(1)
            click.echo("Session restored!")

        # Set global session for tools
        set_global_session(session)
        if session.get_async_page():
            set_current_async_page(session.get_async_page())

        yield session


async def run_single_task_async(agent: FacebookSurferAgent, task: str, stream: bool, thread_id: str):
    """Run a single task and exit (async version).

    Args:
        agent: FacebookSurferAgent instance
        task: Task description
        stream: Whether to stream execution
        thread_id: Conversation thread ID
    """
    click.echo(f"\nExecuting task: {task}")
    click.echo("-" * 60)

    if stream:
        async for event in agent.stream(task, thread_id=thread_id):
            # Parse and display events
            if "messages" in event and event["messages"]:
                latest_msg = event["messages"][-1]
                if hasattr(latest_msg, "content"):
                    content = latest_msg.content
                    if isinstance(content, str):
                        click.echo(f"[Update] {content}")
                    elif isinstance(content, list):
                        for part in content:
                            if isinstance(part, str):
                                click.echo(f"[Update] {part}")
                            elif isinstance(part, dict):
                                # Extract text from content blocks
                                text = part.get("text", str(part))
                                click.echo(f"[Update] {text}")
            if "__interrupt__" in event:
                click.echo(f"[Interrupt] {event['__interrupt__']}")
                # Handle HITL here if needed
                click.echo("Human intervention required. Check agent state.")
    else:
        result = await agent.invoke(task, thread_id=thread_id)
        click.echo("\nResult:")
        if "messages" in result and result["messages"]:
            latest_msg = result["messages"][-1]
            if hasattr(latest_msg, "content"):
                content = latest_msg.content
                # Handle content that's a list of content blocks
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            click.echo(block.get("text", str(block)))
                        elif isinstance(block, str):
                            click.echo(block)
                        else:
                            click.echo(str(block))
                elif content:  # Non-empty string or other truthy value
                    click.echo(content)
        else:
            click.echo(result)

    click.echo("-" * 60)
    click.echo("Task complete!")


async def run_interactive_async(agent: FacebookSurferAgent, thread_id: str):
    """Run in interactive mode (async version).

    Args:
        agent: FacebookSurferAgent instance
        thread_id: Conversation thread ID
    """
    click.echo("\nEntering interactive mode.")
    click.echo("Commands: 'exit', 'quit', 'clear', 'state', 'tools'")
    click.echo("")

    while True:
        try:
            task = click.prompt("Task", default="", show_default=False)

            if not task.strip():
                continue

            if task.lower() in ["exit", "quit"]:
                click.echo("Goodbye!")
                break

            if task.lower() == "clear":
                click.echo("\033c", nl=False)
                continue

            if task.lower() == "state":
                state = await agent.get_state(thread_id)
                click.echo(f"Current state: {state}")
                continue

            if task.lower() == "tools":
                click.echo(agent.get_tool_summary())
                continue

            # Execute task
            result = await agent.invoke(task, thread_id=thread_id)
            click.echo("\nResult:")
            if "messages" in result and result["messages"]:
                latest_msg = result["messages"][-1]
                if hasattr(latest_msg, "content"):
                    content = latest_msg.content
                    # Handle content that's a list of content blocks
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                click.echo(block.get("text", str(block)))
                            elif isinstance(block, str):
                                click.echo(block)
                            else:
                                click.echo(str(block))
                    elif content:  # Non-empty string or other truthy value
                        click.echo(content)
            click.echo("")

        except KeyboardInterrupt:
            click.echo("\nUse 'exit' to quit.")
        except EOFError:
            click.echo("\nGoodbye!")
            break
        except Exception as e:
            click.echo(f"Error: {e}", err=True)


@click.group()
def cli():
    """Facebook Surfer - AI-powered Facebook automation agent."""
    pass


@cli.command()
@click.option("--profile", default="./profiles/facebook", help="Path to Facebook profile")
def login(profile: str):
    """Create or restore Facebook session."""
    with init_session(login=True, profile=profile):
        click.echo("\n✅ Session established successfully")
        click.echo("Press Ctrl+C to exit...")

        try:
            click.pause()
        except KeyboardInterrupt:
            click.echo("\nClosing session...")


@cli.command()
@click.argument("task", required=False)
@click.option("--stream", is_flag=True, help="Stream execution in real-time")
@click.option("--thread", default="default", help="Conversation thread ID")
@click.option("--model", default="gpt-4o-mini", help="OpenAI model to use")
@click.option("--no-banner", is_flag=True, help="Skip banner display")
def run(task: str | None, stream: bool, thread: str, model: str, no_banner: bool):
    """Run a task with the Facebook Surfer agent.

    If no task is provided, enters interactive mode.
    """
    async def _run():
        # Print banner
        if not no_banner:
            print_banner()

        # Initialize session (restore existing) and run within context
        async with async_init_session(login=False):
            # Create agent
            click.echo(f"\nInitializing agent with {model}...")
            agent = FacebookSurferAgent(model=model)
            click.echo(f"Agent ready with {agent.tool_count} tools registered.")

            # Execute task or run interactively
            if task:
                await run_single_task_async(agent, task, stream, thread)
            else:
                await run_interactive_async(agent, thread)

            click.echo("\nDone!")

    asyncio.run(_run())


@cli.command()
def test():
    """Run tests for the project."""
    import subprocess

    result = subprocess.run(
        ["pytest", "-v"],
        cwd=Path(__file__).parent.parent,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    cli()
