from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

from starry.models import Repo

API = "https://api.github.com"


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    return datetime.fromisoformat(val.replace("Z", "+00:00"))


def _starred_repos(token: str | None = None) -> list[Repo]:
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit(
            "No GitHub token found. Set GITHUB_TOKEN or GH_TOKEN environment variable."
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.star+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    now = datetime.now(timezone.utc)
    repos: list[Repo] = []
    url: str | None = f"{API}/user/starred?per_page=100"

    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        items = resp.json()

        for item in items:
            starred_at = _parse_dt(item.get("starred_at"))
            r = item["repo"]
            license_obj = r.get("license") or {}

            repos.append(
                Repo(
                    id=r["id"],
                    node_id=r["node_id"],
                    name=r["name"],
                    full_name=r["full_name"],
                    owner_login=r["owner"]["login"],
                    owner_id=r["owner"]["id"],
                    description=r.get("description"),
                    homepage=r.get("homepage"),
                    language=r.get("language"),
                    topics=r.get("topics", []),
                    private=r.get("private", False),
                    fork=r.get("fork", False),
                    archived=r.get("archived", False),
                    disabled=r.get("disabled", False),
                    is_template=r.get("is_template", False),
                    html_url=r.get("html_url", ""),
                    clone_url=r.get("clone_url", ""),
                    ssh_url=r.get("ssh_url", ""),
                    stargazers_count=r.get("stargazers_count", 0),
                    watchers_count=r.get("watchers_count", 0),
                    forks_count=r.get("forks_count", 0),
                    open_issues_count=r.get("open_issues_count", 0),
                    network_count=r.get("network_count", 0),
                    subscribers_count=r.get("subscribers_count", 0),
                    size=r.get("size", 0),
                    default_branch=r.get("default_branch", "main"),
                    license_name=license_obj.get("name"),
                    license_spdx=license_obj.get("spdx_id"),
                    created_at=_parse_dt(r.get("created_at")),
                    updated_at=_parse_dt(r.get("updated_at")),
                    pushed_at=_parse_dt(r.get("pushed_at")),
                    starred_at=starred_at,
                    has_issues=r.get("has_issues", True),
                    has_projects=r.get("has_projects", True),
                    has_wiki=r.get("has_wiki", True),
                    has_pages=r.get("has_pages", False),
                    has_downloads=r.get("has_downloads", True),
                    has_discussions=r.get("has_discussions", False),
                    visibility=r.get("visibility", "public"),
                    synced_at=now,
                )
            )

        # Follow pagination via Link header
        url = None
        link = resp.headers.get("Link", "")
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
                break

    return repos


def sync(token: str | None = None, db_path=None) -> int:
    from starry.db import get_connection, init_db, upsert_repo, mark_unstarred

    kwargs = {"db_path": db_path} if db_path else {}
    conn = get_connection(**kwargs)
    init_db(conn)

    repos = _starred_repos(token)
    for repo in repos:
        upsert_repo(conn, repo)

    current_ids = {r.id for r in repos}
    mark_unstarred(conn, current_ids)

    conn.commit()
    conn.close()
    return len(repos)
