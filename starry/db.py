from __future__ import annotations

import sqlite3
from pathlib import Path

from starry.models import Repo

DB_PATH = Path(__file__).resolve().parent.parent / "stars.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
    id              INTEGER PRIMARY KEY,
    node_id         TEXT NOT NULL,
    name            TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    owner_login     TEXT NOT NULL,
    owner_id        INTEGER NOT NULL,
    description     TEXT,
    homepage        TEXT,
    language        TEXT,
    topics          TEXT DEFAULT '[]',
    private         INTEGER DEFAULT 0,
    fork            INTEGER DEFAULT 0,
    archived        INTEGER DEFAULT 0,
    disabled        INTEGER DEFAULT 0,
    is_template     INTEGER DEFAULT 0,
    html_url        TEXT DEFAULT '',
    clone_url       TEXT DEFAULT '',
    ssh_url         TEXT DEFAULT '',
    stargazers_count    INTEGER DEFAULT 0,
    watchers_count      INTEGER DEFAULT 0,
    forks_count         INTEGER DEFAULT 0,
    open_issues_count   INTEGER DEFAULT 0,
    network_count       INTEGER DEFAULT 0,
    subscribers_count   INTEGER DEFAULT 0,
    size            INTEGER DEFAULT 0,
    default_branch  TEXT DEFAULT 'main',
    license_name    TEXT,
    license_spdx    TEXT,
    created_at      TEXT,
    updated_at      TEXT,
    pushed_at       TEXT,
    starred_at      TEXT,
    has_issues      INTEGER DEFAULT 1,
    has_projects    INTEGER DEFAULT 1,
    has_wiki        INTEGER DEFAULT 1,
    has_pages       INTEGER DEFAULT 0,
    has_downloads   INTEGER DEFAULT 1,
    has_discussions  INTEGER DEFAULT 0,
    visibility      TEXT DEFAULT 'public',
    synced_at       TEXT,
    unstarred       INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS repos_fts USING fts5(
    full_name, description, language, topics,
    content='repos',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS repos_ai AFTER INSERT ON repos BEGIN
    INSERT INTO repos_fts(rowid, full_name, description, language, topics)
    VALUES (new.id, new.full_name, new.description, new.language, new.topics);
END;

CREATE TRIGGER IF NOT EXISTS repos_ad AFTER DELETE ON repos BEGIN
    INSERT INTO repos_fts(repos_fts, rowid, full_name, description, language, topics)
    VALUES ('delete', old.id, old.full_name, old.description, old.language, old.topics);
END;

CREATE TRIGGER IF NOT EXISTS repos_au AFTER UPDATE ON repos BEGIN
    INSERT INTO repos_fts(repos_fts, rowid, full_name, description, language, topics)
    VALUES ('delete', old.id, old.full_name, old.description, old.language, old.topics);
    INSERT INTO repos_fts(rowid, full_name, description, language, topics)
    VALUES (new.id, new.full_name, new.description, new.language, new.topics);
END;
"""

COLUMNS = [
    "id", "node_id", "name", "full_name", "owner_login", "owner_id",
    "description", "homepage", "language", "topics",
    "private", "fork", "archived", "disabled", "is_template",
    "html_url", "clone_url", "ssh_url",
    "stargazers_count", "watchers_count", "forks_count",
    "open_issues_count", "network_count", "subscribers_count",
    "size", "default_branch", "license_name", "license_spdx",
    "created_at", "updated_at", "pushed_at", "starred_at",
    "has_issues", "has_projects", "has_wiki", "has_pages",
    "has_downloads", "has_discussions", "visibility", "synced_at", "unstarred",
]


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_repo(conn: sqlite3.Connection, repo: Repo) -> None:
    row = repo.to_row()
    cols = [c for c in COLUMNS if c != "unstarred"]
    placeholders = ", ".join(f":{c}" for c in cols)
    updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c != "id")
    sql = (
        f"INSERT INTO repos ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}, unstarred = 0"
    )
    conn.execute(sql, row)


def mark_unstarred(conn: sqlite3.Connection, current_ids: set[int]) -> int:
    if not current_ids:
        return 0
    placeholders = ", ".join("?" for _ in current_ids)
    cur = conn.execute(
        f"UPDATE repos SET unstarred = 1 WHERE id NOT IN ({placeholders}) AND unstarred = 0",
        list(current_ids),
    )
    return cur.rowcount


def search(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[Repo]:
    rows = conn.execute(
        "SELECT r.* FROM repos r "
        "JOIN repos_fts f ON r.id = f.rowid "
        "WHERE repos_fts MATCH ? AND r.unstarred = 0 "
        "ORDER BY rank LIMIT ?",
        (query, limit),
    ).fetchall()
    return [Repo.from_row(row) for row in rows]


def list_repos(
    conn: sqlite3.Connection,
    *,
    language: str | None = None,
    topic: str | None = None,
    sort: str = "starred_at",
    limit: int = 50,
) -> list[Repo]:
    clauses = ["unstarred = 0"]
    params: list[str] = []
    if language:
        clauses.append("LOWER(language) = LOWER(?)")
        params.append(language)
    if topic:
        clauses.append("topics LIKE ?")
        params.append(f'%"{topic}"%')
    allowed_sorts = {
        "starred_at", "stargazers_count", "updated_at",
        "pushed_at", "created_at", "forks_count", "name",
    }
    if sort not in allowed_sorts:
        sort = "starred_at"
    order_dir = "ASC" if sort == "name" else "DESC"
    where = " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT * FROM repos WHERE {where} ORDER BY {sort} {order_dir} LIMIT ?",
        [*params, limit],
    ).fetchall()
    return [Repo.from_row(row) for row in rows]


def get_repo(conn: sqlite3.Connection, full_name: str) -> Repo | None:
    row = conn.execute(
        "SELECT * FROM repos WHERE full_name = ?", (full_name,)
    ).fetchone()
    return Repo.from_row(row) if row else None


def get_stats(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) FROM repos WHERE unstarred = 0").fetchone()[0]
    by_language = conn.execute(
        "SELECT language, COUNT(*) as cnt FROM repos "
        "WHERE unstarred = 0 AND language IS NOT NULL "
        "GROUP BY language ORDER BY cnt DESC LIMIT 20"
    ).fetchall()
    return {
        "total": total,
        "by_language": [(r["language"], r["cnt"]) for r in by_language],
    }
