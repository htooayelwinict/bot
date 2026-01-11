"""Main entry point for Facebook Surfer agent."""

import sys
from pathlib import Path

import click


@click.group()
def cli():
    """Facebook Surfer - AI-powered Facebook automation agent."""
    pass


@cli.command()
@click.option("--profile", default="./profiles/facebook", help="Path to Facebook profile")
def login(profile: str):
    """Create or restore Facebook session."""
    from playwright.sync_api import sync_playwright
    from src.session.profile_manager import (
        FacebookProfileManager,
        check_login_status,
        wait_for_login,
    )

    profile_manager = FacebookProfileManager(profile_dir=Path(profile))

    with sync_playwright() as p:
        context, page, was_restored = profile_manager.get_or_create_session(p.chromium)

        # Navigate to Facebook
        page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=60000)

        # Check login status
        if not check_login_status(page):
            click.echo("⚠️  Not logged in. Please log in manually...")
            if not wait_for_login(page):
                click.echo("❌ Login timeout", err=True)
                profile_manager.close()
                sys.exit(1)
            # Save session after successful login
            profile_manager.save_session()
        elif was_restored:
            click.echo("✅ Restored existing session - already logged in!")

        click.echo("✅ Session established successfully")
        click.echo("Press Ctrl+C to exit...")

        try:
            click.pause()
        except KeyboardInterrupt:
            click.echo("\nClosing session...")
        finally:
            profile_manager.close()


@cli.command()
@click.argument("task")
@click.option("--model", default="gpt-4o", help="OpenAI model to use")
@click.option("--stream", is_flag=True, help="Stream agent output in real-time")
def run(task: str, model: str, stream: bool):
    """Run a task with the Facebook Surfer agent."""
    click.echo(f"Running task: {task}")
    click.echo(f"Model: {model}")
    click.echo("Agent coming soon in Phase 3b!")


@cli.command()
def test():
    """Run tests for the project."""
    import subprocess

    result = subprocess.run(["pytest", "-v"], cwd=Path(__file__).parent.parent)
    sys.exit(result.returncode)


if __name__ == "__main__":
    cli()
