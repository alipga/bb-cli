---
name: bb
description: Interact with Bitbucket Cloud PRs — list, view, create, approve, merge PRs, and manage comments. Use when the user asks about pull requests, code reviews, or PR comments on Bitbucket.
argument-hint: [command]
---

# Bitbucket Cloud CLI (`bb`)

You have access to the `bb` CLI tool for interacting with Bitbucket Cloud pull requests. The tool auto-detects workspace and repo from the current git remote (bitbucket.org).

## Prerequisites

- The user must have run `bb setup` (or `bb auth login`) once to store credentials.
- The current directory must be a git repo cloned from Bitbucket, OR use `-w`/`-r` flags.

## Available Commands

### Setup
```bash
bb setup          # Full setup: authenticate + install Claude Code skill
bb setup-skill    # Install/update just the Claude Code skill
```

### Authentication
```bash
bb auth status    # Check if authenticated (verifies against API)
bb auth login     # Interactive — opens browser, prompts for email + API token
bb auth logout    # Clear stored credentials
```

### List PRs
```bash
bb pr list                          # Open PRs (default)
bb pr list --state MERGED           # Merged PRs
bb pr list --state DECLINED         # Declined PRs
bb pr list --limit 10               # Limit results
bb pr list --json                   # JSON output
```

### View PR Details
```bash
bb pr show <PR_ID>                  # Title, author, branches, description
bb pr show <PR_ID> --json           # JSON output
bb pr files <PR_ID>                 # Changed files with +/- line counts
bb pr diff <PR_ID>                  # Full unified diff
```

### Create a PR
```bash
bb pr create --title "Add feature X"                          # Minimal (source=current branch, dest=master)
bb pr create -t "Fix bug" --source feature --dest main        # Explicit branches
bb pr create -t "Update" --body "Description here"            # With description
bb pr create -t "Refactor" --reviewer alice --reviewer bob    # With reviewers
bb pr create -t "Cleanup" --close-source                      # Close source branch on merge
```

### Approve and Merge
```bash
bb pr approve <PR_ID>                                          # Approve a PR
bb pr merge <PR_ID>                                            # Merge a PR
bb pr merge <PR_ID> --strategy squash                          # Squash merge
bb pr merge <PR_ID> --strategy fast_forward                    # Fast-forward merge
bb pr merge <PR_ID> --close-source                             # Delete source branch after merge
```

### Comments
```bash
bb pr comments <PR_ID>                                          # List all comments (threaded)
bb pr comment <PR_ID> --body "comment text"                     # Post general comment
bb pr comment <PR_ID> --body "text" --file path/to/file --line 42  # Inline comment
bb pr reply <PR_ID> --comment-id <CID> --body "reply text"      # Reply to a comment
bb pr resolve <PR_ID> --comment-id <CID>                        # Resolve a comment
```

### Workspace/Repo Override
If not in a Bitbucket git repo, specify explicitly:
```bash
bb pr -w <workspace> -r <repo> list
```

## Guidelines

- Always run `bb auth status` first if unsure whether the user is authenticated.
- When reviewing a PR, start with `bb pr show <id>` and `bb pr files <id>` to get context, then `bb pr comments <id>` to see existing discussion.
- When the user asks to review a PR, read the diff with `bb pr diff <id>` and provide feedback.
- Comment IDs are shown as `#<id>` in the `bb pr comments` output.
- If the user says $ARGUMENTS, interpret it as a bb subcommand and run it directly.

### Confirmation required for write operations

Read-only commands (`auth status`, `pr list`, `pr show`, `pr files`, `pr diff`, `pr comments`) can be run freely. **All write operations require explicit user confirmation before execution.** This includes:

- `bb pr create` — creating a pull request
- `bb pr approve` — approving a pull request
- `bb pr merge` — merging a pull request
- `bb pr comment` — posting a comment
- `bb pr reply` — replying to a comment
- `bb pr resolve` — resolving a comment
- `bb auth login` / `bb auth logout` — changing authentication state

Always show the user what you intend to do (command, arguments, body text) and ask for confirmation before running any of these commands.
