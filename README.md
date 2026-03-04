# bb-cli

**`gh` for GitHub. `bb` for Bitbucket.** The missing command-line tool for Bitbucket Cloud pull requests.

[![PyPI](https://img.shields.io/pypi/v/bb-cli)](https://pypi.org/project/bb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/bb-cli)](https://pypi.org/project/bb-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

<!-- TODO: Add terminal screenshot/GIF here showing `bb pr list` output -->

## Why bb-cli?

GitHub has `gh`. GitLab has `glab`. **Bitbucket Cloud has nothing** — until now.

If you use Bitbucket at work, you know the pain: context-switch to the browser to check PRs, post review comments, merge branches. `bb` lets you do all of that from the terminal, in the repo you're already working in.

- **Zero config** — auto-detects workspace and repo from your git remote
- **Full PR lifecycle** — list, create, review, comment, approve, merge
- **Inline code comments** — comment on specific files and lines
- **Threaded discussions** — reply to and resolve comment threads
- **JSON output** — pipe to `jq` for scripting and automation
- **AI-ready** — ships with a Claude Code skill for AI-assisted PR reviews

## Quick Start

```bash
pip install bb-cli
bb auth login
bb pr list
```

That's it. If you're in a Bitbucket repo, `bb` auto-detects your workspace and repo.

### 60-second workflow: review a PR from your terminal

```bash
# See what's open
bb pr list

# Pick a PR and get the overview
bb pr show 42
bb pr files 42

# Read the diff
bb pr diff 42

# Leave a comment on a specific line
bb pr comment 42 --body "This should use a context manager" --file src/db.py --line 15

# Approve and merge
bb pr approve 42
bb pr merge 42 --strategy squash --close-source
```

## Installation

```bash
# pip
pip install bb-cli

# pipx (isolated install, recommended)
pipx install bb-cli

# uv
uv tool install bb-cli
```

Requires Python 3.10+.

## Authentication

`bb` uses Bitbucket [App Passwords](https://support.atlassian.com/bitbucket-cloud/docs/create-an-app-password/) (API tokens) for authentication.

### Creating an API token

1. Go to [**Atlassian API tokens**](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Give it a label (e.g. `bb-cli`)
4. Select the following permissions:

   **Read:**
   - `read:project:bitbucket`
   - `read:pullrequest:bitbucket`
   - `read:repository:bitbucket`
   - `read:runner:bitbucket`
   - `read:workspace:bitbucket`
   - `read:user:bitbucket`

   **Write:**
   - `write:pullrequest:bitbucket`
   - `write:issue:bitbucket`

5. Click **Create** and copy the generated token

```bash
bb auth login
# Prompts for your Bitbucket email + API token
```

Credentials are stored in your system keyring. If keyring is unavailable, they fall back to `~/.config/bbcli/tokens.json` (file mode `600`).

```bash
bb auth status   # Verify credentials
bb auth logout   # Clear stored credentials
```

## Configuration

In most cases, you don't need any configuration — `bb` reads your git remote.

### Config file (optional)

Create `~/.config/bbcli/config.toml` to set defaults:

```toml
[defaults]
workspace = "myworkspace"
repo = "myrepo"
dest_branch = "main"
```

### Environment variables

Override anything with env vars (highest priority):

- `BITBUCKET_WORKSPACE` — workspace slug
- `BITBUCKET_REPO` — repository slug
- `BITBUCKET_DEST_BRANCH` — default destination branch for `pr create`

**Resolution order:** env vars > config file > git remote

## Commands

### Pull Requests

```bash
bb pr list                              # List open PRs
bb pr list --state MERGED --limit 10    # Filter and limit
bb pr list --json                       # JSON output (pipe to jq)

bb pr show 42                           # PR details
bb pr show 42 --json                    # JSON output
bb pr files 42                          # Changed files with line counts
bb pr diff 42                           # Full unified diff

bb pr create -t "Add feature X"        # Create from current branch
bb pr create -t "Fix" -s feat -d main  # Explicit branches
bb pr create -t "Update" --body "..."  # With description
bb pr create -t "Fix" --reviewer alice # Add reviewers

bb pr approve 42                        # Approve a PR
bb pr merge 42                          # Merge a PR
bb pr merge 42 --strategy squash       # Squash merge
bb pr merge 42 --close-source          # Delete source branch after merge
```

### Comments

```bash
bb pr comments 42                                           # List all (threaded)
bb pr comment 42 --body "Looks good"                        # General comment
bb pr comment 42 --body "Nit" --file src/main.py --line 15  # Inline comment
bb pr reply 42 --comment-id 123 --body "Fixed"              # Reply to thread
bb pr resolve 42 --comment-id 123                           # Resolve thread
```

### Workspace/Repo Override

All `pr` subcommands accept `-w` and `-r` flags:

```bash
bb pr -w myteam -r backend list
bb pr -w myteam -r backend show 99
```

## Claude Code Integration

`bb-cli` ships with a [Claude Code](https://claude.com/claude-code) skill file for AI-assisted PR review workflows. To enable it:

```bash
cp -r skills/bb ~/.claude/skills/bb
```

Then Claude can list PRs, read diffs, post review comments, and manage threads on your behalf.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

[MIT](LICENSE)
