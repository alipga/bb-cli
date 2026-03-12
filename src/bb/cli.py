from __future__ import annotations

import importlib.resources
import json as json_mod
import os
import re
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from bb import auth
from bb.client import BitbucketClient
from bb.api import pullrequests, comments

console = Console()

# --- Config loading ---

def _load_config() -> dict:
    """Load defaults from ~/.config/bb/config.toml if it exists."""
    config_path = Path.home() / ".config" / "bb" / "config.toml"
    if not config_path.exists():
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]
    return tomllib.loads(config_path.read_text()).get("defaults", {})


def _from_git_remote() -> tuple[str, str]:
    """Try to extract workspace and repo from the current git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return "", ""
        url = result.stdout.strip()
        # SSH: git@bitbucket.org:workspace/repo.git
        m = re.match(r"git@bitbucket\.org:([^/]+)/([^/]+?)(?:\.git)?$", url)
        if m:
            return m.group(1), m.group(2)
        # HTTPS: https://bitbucket.org/workspace/repo.git
        m = re.match(r"https?://bitbucket\.org/([^/]+)/([^/]+?)(?:\.git)?$", url)
        if m:
            return m.group(1), m.group(2)
    except Exception:
        pass
    return "", ""


def _get_default(name: str) -> str:
    """Get default value from env var, config file, or git remote."""
    env_key = f"BITBUCKET_{name.upper()}"
    val = os.environ.get(env_key, "")
    if val:
        return val
    config = _load_config()
    val = config.get(name, "")
    if val:
        return val
    # Fall back to git remote
    ws, repo = _from_git_remote()
    if name == "workspace":
        return ws
    if name == "repo":
        return repo
    return ""


# --- CLI groups ---

@click.group()
@click.version_option(package_name="bb-tool")
def main():
    """Bitbucket Cloud CLI for PR review workflows."""


@main.group("auth")
def auth_cmd():
    """Manage authentication."""


@auth_cmd.command("login")
def auth_login():
    """Log in with your Bitbucket email and API token."""
    auth.login()


@auth_cmd.command("status")
def auth_status():
    """Show current authentication state."""
    creds = auth.status()
    if not creds:
        console.print("[red]Not logged in.[/red] Run: bb auth login")
        return
    if creds.get("valid"):
        console.print(f"[green]Authenticated[/green] as {creds.get('display_name', '')} ({creds['email']})")
    else:
        console.print(f"[red]Invalid credentials[/red] for {creds['email']}. Run: bb auth login")


@auth_cmd.command("logout")
def auth_logout():
    """Clear stored tokens."""
    auth.logout()


# --- Setup commands ---

SKILL_DEST = Path.home() / ".claude" / "skills" / "bb"


def _install_skill() -> Path:
    """Copy the bundled SKILL.md to ~/.claude/skills/bb/."""
    SKILL_DEST.mkdir(parents=True, exist_ok=True)
    src = importlib.resources.files("bb").joinpath("data/SKILL.md")
    dest = SKILL_DEST / "SKILL.md"
    dest.write_text(src.read_text())
    return dest


@main.command("setup-skill")
def setup_skill():
    """Install the Claude Code skill for AI-assisted PR reviews."""
    dest = _install_skill()
    console.print(f"[green]Skill installed[/green] at {dest}")


@main.command("setup")
@click.pass_context
def setup(ctx):
    """Set up bb: authenticate and install the Claude Code skill."""
    console.print("[bold]Step 1/2:[/bold] Authentication\n")
    auth.login()
    console.print()
    console.print("[bold]Step 2/2:[/bold] Claude Code skill\n")
    dest = _install_skill()
    console.print(f"[green]Skill installed[/green] at {dest}")
    console.print()
    console.print("[bold green]All set![/bold green] Try: bb pr list")


# --- PR commands ---

@main.group()
@click.option("--workspace", "-w", default="", help="Bitbucket workspace slug")
@click.option("--repo", "-r", default="", help="Repository slug")
@click.pass_context
def pr(ctx, workspace, repo):
    """Pull request commands."""
    ctx.ensure_object(dict)
    ctx.obj["workspace"] = workspace or _get_default("workspace")
    ctx.obj["repo"] = repo or _get_default("repo")
    if not ctx.obj["workspace"] or not ctx.obj["repo"]:
        raise click.UsageError(
            "Workspace and repo required. Use --workspace/--repo, "
            "BITBUCKET_WORKSPACE/BITBUCKET_REPO env vars, or ~/.config/bb/config.toml"
        )


def _client() -> BitbucketClient:
    return BitbucketClient()


def _pr_to_dict(p) -> dict:
    """Convert a PullRequest dataclass to a plain dict for JSON output."""
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "state": p.state,
        "author": p.author,
        "source_branch": p.source_branch,
        "destination_branch": p.destination_branch,
        "comment_count": p.comment_count,
        "created_on": p.created_on,
        "updated_on": p.updated_on,
        "url": p.url,
    }


@pr.command("list")
@click.option("--state", default="OPEN", help="PR state filter (OPEN, MERGED, DECLINED, SUPERSEDED)")
@click.option("--limit", default=25, help="Max PRs to show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pr_list(ctx, state, limit, as_json):
    """List pull requests."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    with _client() as client:
        prs = pullrequests.list_prs(client, ws, repo, state=state, limit=limit)

    if as_json:
        click.echo(json_mod.dumps([_pr_to_dict(p) for p in prs], indent=2))
        return

    table = Table(title=f"Pull Requests ({state})")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Title")
    table.add_column("Author", style="green")
    table.add_column("Source → Dest", style="yellow")
    table.add_column("Comments", justify="right")
    table.add_column("Updated")

    for p in prs:
        table.add_row(
            str(p.id),
            p.title,
            p.author,
            f"{p.source_branch} → {p.destination_branch}",
            str(p.comment_count),
            p.updated_on[:10],
        )
    console.print(table)


@pr.command("show")
@click.argument("pr_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pr_show(ctx, pr_id, as_json):
    """Show PR details."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    with _client() as client:
        p = pullrequests.get_pr(client, ws, repo, pr_id)

    if as_json:
        click.echo(json_mod.dumps(_pr_to_dict(p), indent=2))
        return

    console.print(f"[bold cyan]#{p.id}[/bold cyan] {p.title}")
    console.print(f"  State: [bold]{p.state}[/bold]")
    console.print(f"  Author: {p.author}")
    console.print(f"  Branch: {p.source_branch} → {p.destination_branch}")
    console.print(f"  Comments: {p.comment_count}")
    console.print(f"  Created: {p.created_on[:10]}  Updated: {p.updated_on[:10]}")
    console.print(f"  URL: {p.url}")
    if p.description:
        console.print()
        console.print(p.description)


@pr.command("diff")
@click.argument("pr_id", type=int)
@click.pass_context
def pr_diff(ctx, pr_id):
    """Show PR diff."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    with _client() as client:
        diff_text = pullrequests.get_diff(client, ws, repo, pr_id)
    console.print(diff_text)


@pr.command("files")
@click.argument("pr_id", type=int)
@click.pass_context
def pr_files(ctx, pr_id):
    """Show changed files in a PR."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    with _client() as client:
        stats = pullrequests.get_diffstat(client, ws, repo, pr_id)

    table = Table(title="Changed Files")
    table.add_column("Status", style="bold")
    table.add_column("File")
    table.add_column("+", style="green", justify="right")
    table.add_column("-", style="red", justify="right")

    for s in stats:
        table.add_row(s.status, s.path, str(s.lines_added), str(s.lines_removed))
    console.print(table)


@pr.command("comments")
@click.argument("pr_id", type=int)
@click.pass_context
def pr_comments(ctx, pr_id):
    """List all comments on a PR (threaded)."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    with _client() as client:
        all_comments = comments.list_comments(client, ws, repo, pr_id)

    # Build tree
    by_id = {c.id: c for c in all_comments}
    roots = []
    for c in all_comments:
        if c.parent_id and c.parent_id in by_id:
            by_id[c.parent_id].children.append(c)
        else:
            roots.append(c)

    def _print_comment(c, indent=0):
        prefix = "  " * indent
        resolved_tag = " [dim](resolved)[/dim]" if c.resolved else ""
        location = ""
        if c.inline:
            line = c.inline.to_line or c.inline.from_line or ""
            location = f" [dim]{c.inline.path}:{line}[/dim]"

        console.print(
            f"{prefix}[bold cyan]#{c.id}[/bold cyan] [green]{c.user}[/green]"
            f" [dim]{c.created_on[:10]}[/dim]{location}{resolved_tag}"
        )
        for line in c.content.splitlines():
            console.print(f"{prefix}  {line}")
        for child in c.children:
            _print_comment(child, indent + 1)

    if not roots:
        console.print("[dim]No comments.[/dim]")
        return

    for c in roots:
        _print_comment(c)
        console.print()


def _current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, timeout=5,
    )
    if result.returncode != 0:
        raise click.UsageError("Could not detect current git branch. Use --source to specify it.")
    return result.stdout.strip()


@pr.command("create")
@click.option("--title", "-t", required=True, help="PR title")
@click.option("--source", "-s", default=None, help="Source branch (defaults to current git branch)")
@click.option("--dest", "-d", default=None, help="Destination branch (defaults to master)")
@click.option("--body", "-b", default="", help="PR description")
@click.option("--close-source/--no-close-source", default=False, help="Close source branch on merge")
@click.option("--reviewer", multiple=True, help="Reviewer username or {uuid} (repeatable)")
@click.pass_context
def pr_create(ctx, title, source, dest, body, close_source, reviewer):
    """Create a new pull request."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    source = source or _current_branch()
    dest = dest or _get_default("dest_branch") or "master"

    with _client() as client:
        p = pullrequests.create_pr(
            client, ws, repo, title, source, dest,
            description=body,
            close_source_branch=close_source,
            reviewers=list(reviewer) if reviewer else None,
        )
    console.print(f"[green]Created PR #{p.id}[/green]: {p.url}")


@pr.command("approve")
@click.argument("pr_id", type=int)
@click.pass_context
def pr_approve(ctx, pr_id):
    """Approve a pull request."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    with _client() as client:
        pullrequests.approve_pr(client, ws, repo, pr_id)
    console.print(f"[green]PR #{pr_id} approved.[/green]")


@pr.command("merge")
@click.argument("pr_id", type=int)
@click.option("--strategy", type=click.Choice(["merge_commit", "squash", "fast_forward"]),
              default=None, help="Merge strategy")
@click.option("--close-source/--no-close-source", default=False, help="Close source branch after merge")
@click.pass_context
def pr_merge(ctx, pr_id, strategy, close_source):
    """Merge a pull request."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    with _client() as client:
        p = pullrequests.merge_pr(client, ws, repo, pr_id,
                                  merge_strategy=strategy,
                                  close_source_branch=close_source)
    console.print(f"[green]PR #{p.id} merged.[/green] {p.url}")


@pr.command("comment")
@click.argument("pr_id", type=int)
@click.option("--body", "-b", required=True, help="Comment body text")
@click.option("--file", "-f", "file_path", default=None, help="File path for inline comment")
@click.option("--line", "-l", default=None, type=int, help="Line number for inline comment")
@click.pass_context
def pr_comment(ctx, pr_id, body, file_path, line):
    """Post a comment on a PR."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    inline = None
    if file_path:
        inline = {"path": file_path}
        if line:
            inline["to"] = line

    with _client() as client:
        c = comments.create_comment(client, ws, repo, pr_id, body, inline=inline)
    console.print(f"[green]Comment #{c.id} posted.[/green]")


@pr.command("reply")
@click.argument("pr_id", type=int)
@click.option("--comment-id", "-c", required=True, type=int, help="Parent comment ID")
@click.option("--body", "-b", required=True, help="Reply body text")
@click.pass_context
def pr_reply(ctx, pr_id, comment_id, body):
    """Reply to a comment on a PR."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    with _client() as client:
        c = comments.create_comment(client, ws, repo, pr_id, body, parent_id=comment_id)
    console.print(f"[green]Reply #{c.id} posted.[/green]")


@pr.command("resolve")
@click.argument("pr_id", type=int)
@click.option("--comment-id", "-c", required=True, type=int, help="Comment ID to resolve")
@click.pass_context
def pr_resolve(ctx, pr_id, comment_id):
    """Resolve a comment on a PR."""
    ws, repo = ctx.obj["workspace"], ctx.obj["repo"]
    with _client() as client:
        comments.resolve_comment(client, ws, repo, pr_id, comment_id)
    console.print(f"[green]Comment #{comment_id} resolved.[/green]")


if __name__ == "__main__":
    main()
