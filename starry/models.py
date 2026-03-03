from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Repo:
    id: int
    node_id: str
    name: str
    full_name: str
    owner_login: str
    owner_id: int
    description: str | None = None
    homepage: str | None = None
    language: str | None = None
    topics: list[str] = field(default_factory=list)
    private: bool = False
    fork: bool = False
    archived: bool = False
    disabled: bool = False
    is_template: bool = False
    html_url: str = ""
    clone_url: str = ""
    ssh_url: str = ""
    stargazers_count: int = 0
    watchers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    network_count: int = 0
    subscribers_count: int = 0
    size: int = 0
    default_branch: str = "main"
    license_name: str | None = None
    license_spdx: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    pushed_at: datetime | None = None
    starred_at: datetime | None = None
    has_issues: bool = True
    has_projects: bool = True
    has_wiki: bool = True
    has_pages: bool = False
    has_downloads: bool = True
    has_discussions: bool = False
    visibility: str = "public"
    synced_at: datetime | None = None

    def to_row(self) -> dict:
        d = asdict(self)
        d["topics"] = json.dumps(d["topics"])
        for k in ("created_at", "updated_at", "pushed_at", "starred_at", "synced_at"):
            v = d[k]
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d

    @classmethod
    def from_row(cls, row: dict) -> Repo:
        row = dict(row)
        row.pop("unstarred", None)
        row["topics"] = json.loads(row.get("topics") or "[]")
        for k in ("created_at", "updated_at", "pushed_at", "starred_at", "synced_at"):
            v = row.get(k)
            if v and isinstance(v, str):
                row[k] = datetime.fromisoformat(v)
        return cls(**row)
