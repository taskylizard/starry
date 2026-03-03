# Starry ⭐

Your GitHub starred repos, exported to SQLite and searchable from the CLI.

A GitHub Actions workflow syncs your stars every 5 days, committing the database back to this repo.

## Setup

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the project
uv sync
```

Set a GitHub token (needs `read:user` and `repo` scopes for private star visibility):

```bash
export GITHUB_TOKEN="ghp_..."
```

## Usage

```bash
# Sync starred repos to the local database
uv run starry sync

# Full-text search
uv run starry search "machine learning"

# List with filters
uv run starry list --language rust --sort stargazers_count -n 20

# Show full repo details
uv run starry show owner/repo

# Summary stats
uv run starry stats
```

## GitHub Actions

The included workflow (`.github/workflows/sync.yml`) runs every 5 days and on manual trigger.

Add a **`STARS_TOKEN`** repository secret with a personal access token that has `read:user` scope.
