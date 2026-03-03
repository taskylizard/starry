from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from starry.db import DB_PATH, get_connection, init_db, search, list_repos, get_repo, get_stats

console = Console()


@click.group()
def cli() -> None:
    """Starry — your GitHub stars, searchable locally."""


@cli.command()
@click.option("--token", envvar="GITHUB_TOKEN", help="GitHub personal access token.")
def sync(token: str | None) -> None:
    """Fetch starred repos from GitHub and update the local database."""
    from starry.fetch import sync as do_sync

    console.print("[bold]Syncing starred repos…[/bold]")
    count = do_sync(token)
    console.print(f"[green]✓[/green] Synced {count} repos to {DB_PATH}")


@cli.command(name="search")
@click.argument("query")
@click.option("--limit", "-n", default=50, help="Max results.")
def search_cmd(query: str, limit: int) -> None:
    """Full-text search across repo name, description, language, and topics."""
    conn = get_connection()
    init_db(conn)
    results = search(conn, query, limit=limit)
    conn.close()
    if not results:
        console.print("[yellow]No results.[/yellow]")
        return
    _print_table(results)


@cli.command(name="list")
@click.option("--language", "-l", help="Filter by language.")
@click.option("--topic", "-t", help="Filter by topic.")
@click.option(
    "--sort", "-s",
    type=click.Choice(
        ["starred_at", "stargazers_count", "updated_at", "pushed_at", "created_at", "forks_count", "name"],
        case_sensitive=False,
    ),
    default="starred_at",
    help="Sort field.",
)
@click.option("--limit", "-n", default=50, help="Max results.")
def list_cmd(language: str | None, topic: str | None, sort: str, limit: int) -> None:
    """List starred repos with optional filters."""
    conn = get_connection()
    init_db(conn)
    results = list_repos(conn, language=language, topic=topic, sort=sort, limit=limit)
    conn.close()
    if not results:
        console.print("[yellow]No repos found.[/yellow]")
        return
    _print_table(results)


@cli.command()
@click.argument("full_name")
def show(full_name: str) -> None:
    """Show full details for a repo (e.g. starry show owner/repo)."""
    conn = get_connection()
    init_db(conn)
    repo = get_repo(conn, full_name)
    conn.close()
    if not repo:
        console.print(f"[red]Repo '{full_name}' not found.[/red]")
        raise SystemExit(1)

    table = Table(title=repo.full_name, show_header=False, border_style="dim")
    table.add_column("Field", style="bold cyan", width=20)
    table.add_column("Value")

    row = repo.to_row()
    row["topics"] = ", ".join(json.loads(row["topics"])) if row["topics"] else ""
    for k, v in row.items():
        table.add_row(k, str(v) if v is not None else "—")

    console.print(table)


@cli.command()
def stats() -> None:
    """Show summary statistics about your starred repos."""
    conn = get_connection()
    init_db(conn)
    s = get_stats(conn)
    conn.close()

    console.print(f"\n[bold]Total starred repos:[/bold] {s['total']}\n")

    if s["by_language"]:
        table = Table(title="Top Languages", border_style="dim")
        table.add_column("Language", style="cyan")
        table.add_column("Count", justify="right", style="green")
        for lang, cnt in s["by_language"]:
            table.add_row(lang, str(cnt))
        console.print(table)


def _print_table(repos) -> None:
    table = Table(border_style="dim")
    table.add_column("Repo", style="bold cyan")
    table.add_column("Language", style="yellow")
    table.add_column("★", justify="right", style="green")
    table.add_column("Description", max_width=60)

    for r in repos:
        table.add_row(
            r.full_name,
            r.language or "—",
            str(r.stargazers_count),
            (r.description or "")[:60],
        )

    console.print(table)
