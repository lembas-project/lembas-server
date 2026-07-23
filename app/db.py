import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.models import (
    CaseRun,
    CaseStatus,
    CaseStatusUpdate,
    Study,
    StudyCreate,
)

# Use /data for persistent storage on Fly, fallback to local for dev
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
if not DATA_DIR.exists():
    DATA_DIR = Path(".")
DB_PATH = DATA_DIR / "lembas.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS studies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            tags TEXT,
            plugins_declared TEXT,
            handlers TEXT,
            created_at TEXT,
            pushed_by TEXT
        );

        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            handler_fqn TEXT NOT NULL,
            inputs TEXT,
            status TEXT DEFAULT 'pending',
            started_at TEXT,
            completed_at TEXT,
            duration_seconds REAL,
            results TEXT,
            error_message TEXT,
            environment TEXT,
            FOREIGN KEY (study_id) REFERENCES studies(id),
            UNIQUE(study_id, case_id)
        );
    """)
    # Add handlers column if it doesn't exist (migration for existing DBs)
    try:
        conn.execute("ALTER TABLE studies ADD COLUMN handlers TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.close()


# Initialize on module load
init_db()


async def create_study(payload: StudyCreate, pushed_by: str | None = None) -> Study:
    study_id = str(uuid4())
    created_at = datetime.now(UTC)

    # Build handlers dict keyed by fingerprint
    handlers_dict = {h.schema_fingerprint: h.schema_ for h in payload.handlers}

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO studies
            (id, name, description, tags, plugins_declared, handlers, created_at, pushed_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            study_id,
            payload.name,
            payload.description,
            json.dumps(payload.tags),
            json.dumps(payload.plugins_declared),
            json.dumps(handlers_dict),
            created_at.isoformat(),
            pushed_by,
        ),
    )

    for c in payload.cases:
        conn.execute(
            """
            INSERT INTO cases (study_id, case_id, handler_fqn, inputs, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (study_id, c.case_id, c.handler_fqn, json.dumps(c.inputs), "pending"),
        )

    conn.commit()
    conn.close()

    return await get_study(study_id)  # type: ignore


def _row_to_study(row: sqlite3.Row, cases: dict[str, CaseRun]) -> Study:
    return Study(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        plugins_declared=json.loads(row["plugins_declared"]) if row["plugins_declared"] else [],
        handlers=json.loads(row["handlers"]) if row["handlers"] else {},
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        pushed_by=row["pushed_by"],
        cases=cases,
    )


def _row_to_case(row: sqlite3.Row) -> CaseRun:
    return CaseRun(
        case_id=row["case_id"],
        handler_fqn=row["handler_fqn"],
        inputs=json.loads(row["inputs"]) if row["inputs"] else {},
        status=CaseStatus(row["status"]) if row["status"] else CaseStatus.pending,
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        duration_seconds=row["duration_seconds"],
        results=json.loads(row["results"]) if row["results"] else {},
        error_message=row["error_message"],
        environment=json.loads(row["environment"]) if row["environment"] else {},
    )


async def get_study(study_id: str) -> Study | None:
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM studies WHERE id = ?", (study_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    case_cursor = conn.execute("SELECT * FROM cases WHERE study_id = ?", (study_id,))
    cases = {r["case_id"]: _row_to_case(r) for r in case_cursor.fetchall()}
    conn.close()

    return _row_to_study(row, cases)


async def get_all_studies() -> list[Study]:
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM studies ORDER BY created_at DESC")
    studies = []
    for row in cursor.fetchall():
        case_cursor = conn.execute("SELECT * FROM cases WHERE study_id = ?", (row["id"],))
        cases = {r["case_id"]: _row_to_case(r) for r in case_cursor.fetchall()}
        studies.append(_row_to_study(row, cases))
    conn.close()
    return studies


async def update_study(study_id: str, payload: StudyCreate) -> Study | None:
    """Update an existing study, upserting cases."""
    conn = get_connection()

    # Check if study exists
    cursor = conn.execute("SELECT * FROM studies WHERE id = ?", (study_id,))
    if not cursor.fetchone():
        conn.close()
        return None

    # Build handlers dict keyed by fingerprint
    handlers_dict = {h.schema_fingerprint: h.schema_ for h in payload.handlers}

    # Update study metadata
    conn.execute(
        """
        UPDATE studies
        SET name = ?, description = ?, tags = ?, plugins_declared = ?, handlers = ?
        WHERE id = ?
        """,
        (
            payload.name,
            payload.description,
            json.dumps(payload.tags),
            json.dumps(payload.plugins_declared),
            json.dumps(handlers_dict),
            study_id,
        ),
    )

    # Upsert cases - insert new ones, ignore existing (they keep their status)
    for c in payload.cases:
        conn.execute(
            """
            INSERT INTO cases (study_id, case_id, handler_fqn, inputs, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(study_id, case_id) DO UPDATE SET
                handler_fqn = excluded.handler_fqn,
                inputs = excluded.inputs
            """,
            (study_id, c.case_id, c.handler_fqn, json.dumps(c.inputs), "pending"),
        )

    conn.commit()
    conn.close()

    return await get_study(study_id)


async def delete_study(study_id: str) -> bool:
    """Delete a study and all its cases."""
    conn = get_connection()
    cursor = conn.execute("SELECT id FROM studies WHERE id = ?", (study_id,))
    if not cursor.fetchone():
        conn.close()
        return False

    conn.execute("DELETE FROM cases WHERE study_id = ?", (study_id,))
    conn.execute("DELETE FROM studies WHERE id = ?", (study_id,))
    conn.commit()
    conn.close()
    return True


async def update_case_status(
    study_id: str, case_id: str, update: CaseStatusUpdate
) -> CaseRun | None:
    conn = get_connection()

    # Check if case exists
    cursor = conn.execute(
        "SELECT * FROM cases WHERE study_id = ? AND case_id = ?", (study_id, case_id)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    now = datetime.now(UTC)
    updates = []
    params = []

    # Status
    updates.append("status = ?")
    params.append(update.status.value)

    # Timestamps
    if update.status == CaseStatus.running and row["started_at"] is None:
        updates.append("started_at = ?")
        params.append(now.isoformat())
    elif update.status in (CaseStatus.complete, CaseStatus.failed):
        updates.append("completed_at = ?")
        params.append(now.isoformat())

    # Optional fields
    if update.error_message is not None:
        updates.append("error_message = ?")
        params.append(update.error_message)
    if update.duration_seconds is not None:
        updates.append("duration_seconds = ?")
        params.append(update.duration_seconds)
    if update.results is not None:
        updates.append("results = ?")
        params.append(json.dumps(update.results))
    if update.environment is not None:
        updates.append("environment = ?")
        params.append(json.dumps(update.environment))

    params.extend([study_id, case_id])
    conn.execute(
        f"UPDATE cases SET {', '.join(updates)} WHERE study_id = ? AND case_id = ?",
        params,
    )
    conn.commit()

    # Fetch updated case
    cursor = conn.execute(
        "SELECT * FROM cases WHERE study_id = ? AND case_id = ?", (study_id, case_id)
    )
    row = cursor.fetchone()
    conn.close()

    return _row_to_case(row) if row else None
