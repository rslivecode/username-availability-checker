#!/usr/bin/env python3
"""
Username Availability Checker
-----------------------------
Interactive CLI tool to check username availability across major platforms.
Shows a logo, asks for a username, checks platforms one by one,
displays a live list, and allows exporting results to CSV.

Includes robust error handling for network failures, timeouts,
rate limits, file I/O problems, and unexpected exceptions.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich import box
from rich.prompt import Prompt, Confirm

from platforms import PLATFORMS

console = Console()

# ---------------------------------------------------------------------------
# Logo / Banner
# ---------------------------------------------------------------------------

LOGO = r"""
[bold cyan]
 ██╗   ██╗███████╗███████╗██████╗      ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗
 ██║   ██║██╔════╝██╔════╝██╔══██╗    ██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝
 ██║   ██║███████╗█████╗  ██████╔╝    ██║     ███████║█████╗  ██║     █████╔╝ 
 ██║   ██║╚════██║██╔══╝  ██╔══██╗    ██║     ██╔══██║██╔══╝  ██║     ██╔═██╗ 
 ╚██████╔╝███████║███████╗██║  ██║    ╚██████╗██║  ██║███████╗╚██████╗██║  ██╗
  ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝     ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝
[/bold cyan]
[bold white]          Username Availability Checker[/bold white]
[dim]          Check availability across major platforms[/dim]
"""


def show_logo() -> None:
    try:
        console.clear()
    except Exception:
        pass  # some terminals do not support clear
    console.print(LOGO)
    console.print(
        Panel(
            "[bold]Supported platforms:[/] GitHub • GitLab • Reddit • YouTube • TikTok • "
            "Instagram • X • Twitch • Pinterest • Telegram • Medium • Dev.to • "
            "Hashnode • SoundCloud • Product Hunt",
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username.
    Returns (is_valid, error_message).
    """
    if not username:
        return False, "Username cannot be empty."
    if len(username) < 1 or len(username) > 39:
        return False, "Username must be between 1 and 39 characters."
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if not all(c in allowed for c in username):
        return False, "Username can only contain letters, numbers, underscores, hyphens and periods."
    if username.startswith(".") or username.endswith("."):
        return False, "Username cannot start or end with a period."
    return True, ""


def check_one(
    platform_name: str,
    username: str,
    session: requests.Session,
) -> Tuple[str, str, str, str]:
    """
    Run a single platform check with full exception protection.
    Always returns a valid 4-tuple – never raises.
    """
    try:
        info = PLATFORMS.get(platform_name)
        if not info:
            return platform_name, "unknown", "Platform not found in registry", ""

        checker = info.get("check")
        if not callable(checker):
            return platform_name, "unknown", "Invalid checker function", ""

        url_template = info.get("url_template", "")
        try:
            url = url_template.format(username=username)
        except Exception:
            url = ""

        try:
            status, message = checker(username, session)
        except Exception as e:
            status = "unknown"
            message = f"Checker crashed: {type(e).__name__}: {e}"

        # Normalize status
        if status not in ("available", "taken", "unknown"):
            status = "unknown"
            message = f"Invalid status returned: {status}"

        return platform_name, status, message, url

    except Exception as e:
        return platform_name, "unknown", f"Unexpected error: {type(e).__name__}: {e}", ""


def export_csv(username: str, results: List[Tuple[str, str, str, str]]) -> Tuple[Optional[str], str]:
    """
    Save results to a CSV file.
    Returns (filepath_or_None, error_message).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize username for filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)
    filename = f"username_check_{safe_name}_{timestamp}.csv"
    filepath = Path.cwd() / filename

    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Platform", "Status", "Details", "Profile URL"])
            for platform, status, message, url in results:
                writer.writerow([
                    platform,
                    status.capitalize() if status else "Unknown",
                    message or "",
                    url or "",
                ])
        return str(filepath), ""
    except PermissionError:
        return None, "Permission denied – cannot write file in this directory."
    except OSError as e:
        return None, f"File system error: {e}"
    except Exception as e:
        return None, f"Failed to write CSV: {type(e).__name__}: {e}"


def print_final_table(username: str, results: List[Tuple[str, str, str, str]]) -> None:
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        title=f"Results for [bold cyan]{username}[/]",
        title_style="bold",
    )
    table.add_column("Platform", style="bold", width=16)
    table.add_column("Status", width=12, justify="center")
    table.add_column("Details", width=42)
    table.add_column("Profile URL", style="dim", overflow="fold")

    available = taken = unknown = 0

    for platform, status, message, url in results:
        if status == "available":
            status_text = Text("✅ Available", style="bold green")
            available += 1
        elif status == "taken":
            status_text = Text("❌ Taken", style="bold red")
            taken += 1
        else:
            status_text = Text("❓ Unknown", style="bold yellow")
            unknown += 1
        table.add_row(platform, status_text, message or "—", url or "—")

    console.print()
    console.print(table)
    console.print()

    summary = (
        f"[green]Available: {available}[/]  |  "
        f"[red]Taken: {taken}[/]  |  "
        f"[yellow]Unknown: {unknown}[/]"
    )
    console.print(Panel(summary, title="Summary", border_style="blue"))
    console.print()


def create_session() -> requests.Session:
    """Create a requests session with sensible defaults."""
    session = requests.Session()
    # Some sites dislike missing Accept headers; already set in platforms
    return session


# ---------------------------------------------------------------------------
# Main interactive flow
# ---------------------------------------------------------------------------

def interactive_mode() -> int:
    show_logo()

    while True:
        try:
            raw = Prompt.ask(
                "[bold cyan]Enter username to check[/] [dim](or 'q' to quit)[/]"
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n\n[dim]Goodbye![/]\n")
            return 0

        username = (raw or "").strip().lstrip("@")

        if username.lower() in ("q", "quit", "exit"):
            console.print("\n[dim]Goodbye![/]\n")
            return 0

        is_valid, err_msg = validate_username(username)
        if not is_valid:
            console.print(f"[bold red]Invalid username:[/] {err_msg}\n")
            continue

        console.print(
            f"\n[bold]Checking [cyan]{username}[/cyan] across "
            f"{len(PLATFORMS)} platforms...[/]\n"
        )

        session = create_session()
        results: List[Tuple[str, str, str, str]] = []
        order = list(PLATFORMS.keys())

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Starting...", total=len(order))

                for platform_name in order:
                    progress.update(
                        task, description=f"Checking [bold]{platform_name}[/]..."
                    )

                    result = check_one(platform_name, username, session)
                    results.append(result)

                    _, status, message, _ = result
                    if status == "available":
                        icon = "[green]✅[/]"
                    elif status == "taken":
                        icon = "[red]❌[/]"
                    else:
                        icon = "[yellow]❓[/]"

                    # Truncate very long error messages for live view
                    display_msg = message if len(message) <= 60 else message[:57] + "..."
                    console.print(f"  {icon}  [bold]{platform_name:<16}[/]  {display_msg}")

                    progress.advance(task)
                    time.sleep(0.12)

        except KeyboardInterrupt:
            console.print("\n[yellow]Check interrupted by user.[/]\n")
            if results:
                print_final_table(username, results)
            continue
        except Exception as e:
            console.print(f"\n[bold red]Unexpected error during checks:[/] {e}\n")
            if results:
                console.print("[dim]Showing partial results...[/]")
                print_final_table(username, results)
            continue
        finally:
            try:
                session.close()
            except Exception:
                pass

        print_final_table(username, results)

        console.print(
            "[dim]Note: Results are best-effort. Always verify manually, "
            "especially for Instagram, TikTok and X.[/]\n"
        )

        # CSV export
        try:
            if Confirm.ask("[bold]Download results as CSV?[/]", default=True):
                path, err = export_csv(username, results)
                if path:
                    console.print(f"[green]✓ Saved to:[/] [bold]{path}[/]\n")
                else:
                    console.print(f"[bold red]Could not save CSV:[/] {err}\n")
        except (EOFError, KeyboardInterrupt):
            console.print()
        except Exception as e:
            console.print(f"[bold red]Error during CSV export:[/] {e}\n")

        # Another username?
        try:
            if not Confirm.ask("[bold]Check another username?[/]", default=True):
                console.print("\n[dim]Goodbye![/]\n")
                break
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/]\n")
            break

        console.print()

    return 0


def cli_mode(username: str) -> int:
    """Non-interactive mode for scripting."""
    username = username.strip().lstrip("@")
    is_valid, err_msg = validate_username(username)
    if not is_valid:
        console.print(f"[bold red]Error:[/] {err_msg}")
        return 1

    console.print(f"[dim]Checking '{username}'...[/]")
    session = create_session()
    results: List[Tuple[str, str, str, str]] = []

    try:
        for name in PLATFORMS:
            results.append(check_one(name, username, session))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/]")
        return 130
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/] {e}")
        return 1
    finally:
        try:
            session.close()
        except Exception:
            pass

    print_final_table(username, results)

    try:
        if Confirm.ask("[bold]Save results as CSV?[/]", default=False):
            path, err = export_csv(username, results)
            if path:
                console.print(f"[green]✓ Saved to:[/] [bold]{path}[/]")
            else:
                console.print(f"[bold red]Could not save CSV:[/] {err}")
    except Exception:
        pass

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Username Availability Checker – interactive CLI tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments for interactive mode (recommended).",
    )
    parser.add_argument(
        "username",
        nargs="?",
        help="Username to check (optional – omit for interactive mode)",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="Username Availability Checker 1.2.0",
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        return int(e.code) if e.code is not None else 0

    try:
        if args.username:
            return cli_mode(args.username)
        return interactive_mode()
    except KeyboardInterrupt:
        console.print("\n\n[dim]Interrupted. Goodbye![/]\n")
        return 130
    except Exception as e:
        console.print(f"\n[bold red]Fatal error:[/] {type(e).__name__}: {e}")
        if "--debug" in sys.argv:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
