import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class WorkspaceStore:
    """SQLite-backed workspace store for artifacts and events."""

    def __init__(self, db_path: str = "data/workspaces.sqlite") -> None:
        self.db_path = Path(db_path).resolve()
        self.lock = threading.RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    project_id TEXT,
                    owner_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT,
                    latest_version_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifact_versions (
                    id TEXT PRIMARY KEY,
                    artifact_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT,
                    FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    artifact_id TEXT,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_workspace ON artifacts(workspace_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_artifact ON artifact_versions(artifact_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_workspace ON events(workspace_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_workspace ON messages(workspace_id);")
            conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        return dict(row)

    def create_workspace(self, title: str, project_id: Optional[str], owner_id: Optional[str]) -> Dict[str, Any]:
        workspace_id = str(uuid4())
        now = self._now()
        with self.lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workspaces (id, title, project_id, owner_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, title, project_id, owner_id, now, now),
            )
            conn.commit()
        return {
            "id": workspace_id,
            "title": title,
            "project_id": project_id,
            "owner_id": owner_id,
            "created_at": now,
            "updated_at": now,
        }

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def list_workspaces(self, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            if owner_id is None:
                rows = conn.execute(
                    "SELECT * FROM workspaces ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM workspaces WHERE owner_id = ? ORDER BY created_at DESC",
                    (owner_id,),
                ).fetchall()
        return [dict(row) for row in rows]

    def create_artifact(
        self,
        workspace_id: str,
        artifact_type: str,
        title: Optional[str],
        content: str,
        created_by: Optional[str],
    ) -> Dict[str, Any]:
        artifact_id = str(uuid4())
        version_id = str(uuid4())
        now = self._now()
        with self.lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (id, workspace_id, type, title, latest_version_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (artifact_id, workspace_id, artifact_type, title, version_id, now, now),
            )
            conn.execute(
                """
                INSERT INTO artifact_versions (id, artifact_id, content, created_at, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (version_id, artifact_id, content, now, created_by),
            )
            conn.commit()
        return {
            "id": artifact_id,
            "workspace_id": workspace_id,
            "type": artifact_type,
            "title": title,
            "content": content,
            "version_id": version_id,
            "created_at": now,
            "updated_at": now,
        }

    def update_artifact(self, artifact_id: str, content: str, created_by: Optional[str]) -> Optional[Dict[str, Any]]:
        now = self._now()
        version_id = str(uuid4())
        with self.lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
            if not existing:
                return None
            conn.execute(
                """
                INSERT INTO artifact_versions (id, artifact_id, content, created_at, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (version_id, artifact_id, content, now, created_by),
            )
            conn.execute(
                """
                UPDATE artifacts
                SET latest_version_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (version_id, now, artifact_id),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT a.id, a.workspace_id, a.type, a.title, a.created_at, a.updated_at,
                       a.latest_version_id AS version_id, v.content
                FROM artifacts a
                JOIN artifact_versions v ON v.id = a.latest_version_id
                WHERE a.id = ?
                """,
                (artifact_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def list_artifacts(self, workspace_id: str) -> List[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, workspace_id, type, title, created_at, updated_at, latest_version_id
                FROM artifacts
                WHERE workspace_id = ?
                ORDER BY updated_at DESC
                """,
                (workspace_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT a.id, a.workspace_id, a.type, a.title, a.created_at, a.updated_at,
                       a.latest_version_id AS version_id, v.content
                FROM artifacts a
                JOIN artifact_versions v ON v.id = a.latest_version_id
                WHERE a.id = ?
                """,
                (artifact_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def delete_artifact(self, artifact_id: str) -> bool:
        with self.lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()
            if not existing:
                return False
            conn.execute("DELETE FROM artifact_versions WHERE artifact_id = ?", (artifact_id,))
            conn.execute("DELETE FROM artifacts WHERE id = ?", (artifact_id,))
            conn.commit()
        return True

    def create_event(
        self,
        workspace_id: str,
        event_type: str,
        payload: Dict[str, Any],
        artifact_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = self._now()
        payload_json = json.dumps(payload or {})
        with self.lock, self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (workspace_id, type, artifact_id, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (workspace_id, event_type, artifact_id, payload_json, now),
            )
            conn.commit()
            event_id = cursor.lastrowid
        return {
            "id": event_id,
            "workspace_id": workspace_id,
            "type": event_type,
            "artifact_id": artifact_id,
            "payload": json.loads(payload_json),
            "created_at": now,
        }

    def list_events(self, workspace_id: str, since_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        capped_limit = max(1, min(limit, 500))
        with self.lock, self._connect() as conn:
            if since_id is not None:
                rows = conn.execute(
                    """
                    SELECT id, workspace_id, type, artifact_id, payload, created_at
                    FROM events
                    WHERE workspace_id = ? AND id > ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (workspace_id, since_id, capped_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, workspace_id, type, artifact_id, payload, created_at
                    FROM events
                    WHERE workspace_id = ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (workspace_id, capped_limit),
                ).fetchall()
        events: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["payload"] = json.loads(item.get("payload") or "{}")
            except json.JSONDecodeError:
                item["payload"] = {}
            events.append(item)
        return events

    def add_message(
        self,
        workspace_id: str,
        role: str,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        message_id = str(uuid4())
        now = self._now()
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        with self.lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, workspace_id, role, content, tool_calls, tool_call_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, workspace_id, role, content, tool_calls_json, tool_call_id, now),
            )
            conn.commit()
        return {
            "id": message_id,
            "workspace_id": workspace_id,
            "role": role,
            "content": content,
            "tool_calls": tool_calls,
            "tool_call_id": tool_call_id,
            "created_at": now,
        }

    def list_messages(self, workspace_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self.lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, workspace_id, role, content, tool_calls, tool_call_id, created_at
                FROM messages
                WHERE workspace_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (workspace_id, limit),
            ).fetchall()
        messages: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            if item.get("tool_calls"):
                try:
                    item["tool_calls"] = json.loads(item["tool_calls"])
                except json.JSONDecodeError:
                    item["tool_calls"] = None
            messages.append(item)
        return messages

    def clear_messages(self, workspace_id: str) -> int:
        with self.lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE workspace_id = ?",
                (workspace_id,),
            )
            conn.commit()
            return cursor.rowcount
