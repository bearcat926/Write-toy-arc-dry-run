"""Reliable Task Outbox — Phase 3 F-01 through F-07.

SQLite-backed outbox with lease-based worker coordination, retry backoff,
dead-letter queue, and idempotency keys.

Architecture:
    Enqueue job → claim_with_lease → execute → mark_complete
    On failure → retry with backoff → dead-letter after max attempts
    Idempotency: same dedup_key → no duplicate processing

Uses SQLite WAL mode for concurrent reader safety.
"""

import hashlib
import json
import sqlite3
import time as _time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


OUTBOX_DB_PATH = "workspace/outbox/jobs.db"

# Default retry backoff: [5s, 10s, 20s, 40s, 80s]
DEFAULT_BACKOFF_SECONDS = [5, 10, 20, 40, 80]
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_LEASE_SECONDS = 300  # 5 minutes


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"  # Exceeded max attempts


@dataclass
class Job:
    """A single outbox job."""
    job_id: str
    job_type: str
    payload: dict = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    dedup_key: str = ""
    lease_owner: str = ""
    lease_until: float = 0.0
    available_at: float = 0.0
    last_error: str = ""
    trace_id: str = ""
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "payload": self.payload,
            "status": self.status.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "dedup_key": self.dedup_key,
            "lease_owner": self.lease_owner,
            "lease_until": self.lease_until,
            "available_at": self.available_at,
            "last_error": self.last_error,
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_row(cls, row: tuple) -> "Job":
        return cls(
            job_id=row[0],
            job_type=row[1],
            payload=json.loads(row[2]) if row[2] else {},
            status=JobStatus(row[3]),
            attempts=row[4],
            max_attempts=row[5],
            dedup_key=row[6] or "",
            lease_owner=row[7] or "",
            lease_until=row[8] or 0.0,
            available_at=row[9] or 0.0,
            last_error=row[10] or "",
            trace_id=row[11] or "",
            created_at=row[12] or "",
            completed_at=row[13] or "",
        )


# SQL schema
CREATE_OUTBOX_TABLE = """
CREATE TABLE IF NOT EXISTS outbox_jobs (
    job_id          TEXT PRIMARY KEY,
    job_type        TEXT NOT NULL,
    payload_json    TEXT DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'pending',
    attempts        INTEGER NOT NULL DEFAULT 0,
    max_attempts    INTEGER NOT NULL DEFAULT 5,
    dedup_key       TEXT DEFAULT '',
    lease_owner     TEXT DEFAULT '',
    lease_until     REAL DEFAULT 0.0,
    available_at    REAL DEFAULT 0.0,
    last_error      TEXT DEFAULT '',
    trace_id        TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    completed_at    TEXT DEFAULT ''
);
"""

CREATE_DEDUP_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_dedup_key ON outbox_jobs(dedup_key)
    WHERE dedup_key != '';
"""

CREATE_STATUS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_status ON outbox_jobs(status, available_at);
"""


class OutboxStore:
    """Persistent outbox job store backed by SQLite."""

    def __init__(self, root: Path, worker_id: str = "worker-default"):
        self._root = root
        self._db_path = root / OUTBOX_DB_PATH
        self._worker_id = worker_id

    def _connect(self) -> sqlite3.Connection:
        """Create a connection in autocommit mode for explicit transaction control."""
        conn = sqlite3.connect(str(self._db_path))
        conn.isolation_level = None  # Disable Python's implicit transactions
        return conn

    # ================================================================
    # F-01: Schema initialization
    # ================================================================

    def initialize(self) -> None:
        """Create outbox tables and indexes if they don't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(CREATE_OUTBOX_TABLE)
            conn.execute(CREATE_DEDUP_INDEX)
            conn.execute(CREATE_STATUS_INDEX)
        finally:
            conn.close()

    # ================================================================
    # F-02: Enqueue
    # ================================================================

    def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any] | None = None,
        dedup_key: str = "",
        trace_id: str = "",
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        available_at: float | None = None,
    ) -> str:
        """Enqueue a job. Returns the job_id.

        Args:
            job_type: Type of job (e.g., "projection.summary.rebuild")
            payload: Job-specific data
            dedup_key: If set, duplicate keys are silently ignored
            trace_id: Trace ID for observability
            max_attempts: Max retry attempts before dead-letter
            available_at: Unix timestamp when job becomes available (default: now)

        Returns:
            job_id string
        """
        self.initialize()

        job_id = self._generate_job_id(job_type, payload or {})
        now_ts = _time.time()
        avail_ts = available_at if available_at is not None else now_ts
        now_iso = datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat()

        conn = self._connect()
        try:
            # F-07: Check dedup_key before insert
            if dedup_key:
                existing = conn.execute(
                    "SELECT job_id FROM outbox_jobs WHERE dedup_key = ?",
                    (dedup_key,),
                ).fetchone()
                if existing:
                    return existing[0]

            conn.execute(
                """
                INSERT INTO outbox_jobs(job_id, job_type, payload_json, status,
                                         attempts, max_attempts, dedup_key,
                                         available_at, trace_id, created_at)
                VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
                """,
                (
                    job_id, job_type, json.dumps(payload or {}),
                    JobStatus.PENDING.value, max_attempts, dedup_key,
                    avail_ts, trace_id, now_iso,
                ),
            )
        except sqlite3.IntegrityError:
            # Dedup key collision (race condition after check)
            if dedup_key:
                existing = conn.execute(
                    "SELECT job_id FROM outbox_jobs WHERE dedup_key = ?",
                    (dedup_key,),
                ).fetchone()
                if existing:
                    return existing[0]
            raise
        finally:
            conn.close()

        return job_id

    # ================================================================
    # F-03: Claim with lease
    # ================================================================

    def claim_next(self, job_types: list[str] | None = None) -> Job | None:
        """Claim the next available job with a lease (F-03).

        Args:
            job_types: Optional filter by job type(s)

        Returns:
            Job if one was claimed, None otherwise.
        """
        self.initialize()
        now = _time.time()

        conn = self._connect()
        try:
            # Find next available job AND atomically claim it
            type_clause = ""
            params: list = [now]
            if job_types:
                placeholders = ",".join("?" for _ in job_types)
                type_clause = f"AND job_type IN ({placeholders})"
                params = [now] + list(job_types)

            # Recover expired leases first
            conn.execute(
                """
                UPDATE outbox_jobs
                SET status = 'pending', lease_owner = '', lease_until = 0.0
                WHERE status = 'running' AND lease_until > 0 AND lease_until < ?
                """,
                (now,),
            )

            # Claim one job atomically
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                f"""
                SELECT job_id, job_type, payload_json, status, attempts, max_attempts,
                       dedup_key, lease_owner, lease_until, available_at,
                       last_error, trace_id, created_at, completed_at
                FROM outbox_jobs
                WHERE status = 'pending' AND available_at <= ?
                {type_clause}
                ORDER BY available_at ASC
                LIMIT 1
                """,
                params,
            ).fetchone()

            if row is None:
                conn.execute("ROLLBACK")
                return None

            job = Job.from_row(row)
            lease_until = now + DEFAULT_LEASE_SECONDS

            conn.execute(
                """
                UPDATE outbox_jobs
                SET status = 'running', lease_owner = ?, lease_until = ?,
                    attempts = attempts + 1
                WHERE job_id = ? AND status = 'pending'
                """,
                (self._worker_id, lease_until, job.job_id),
            )

            if conn.total_changes == 0:
                # Another worker claimed it
                conn.execute("ROLLBACK")
                return None

            conn.execute("COMMIT")

            job.status = JobStatus.RUNNING
            job.lease_owner = self._worker_id
            job.lease_until = lease_until
            job.attempts += 1
            return job
        finally:
            conn.close()

    # ================================================================
    # F-04: Heartbeat (lease renewal)
    # ================================================================

    def heartbeat(self, job_id: str) -> bool:
        """Renew the lease on a running job (F-04).

        Returns True if renewal succeeded.
        """
        now = _time.time()
        new_lease = now + DEFAULT_LEASE_SECONDS

        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE outbox_jobs
                SET lease_until = ?
                WHERE job_id = ? AND status = 'running' AND lease_owner = ?
                """,
                (new_lease, job_id, self._worker_id),
            )
            return conn.total_changes > 0
        finally:
            conn.close()

    # ================================================================
    # F-05: Complete / Fail with retry
    # ================================================================

    def mark_complete(self, job_id: str) -> bool:
        """Mark a job as completed (F-05 success path)."""
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE outbox_jobs
                SET status = 'completed', completed_at = ?, lease_owner = ''
                WHERE job_id = ? AND status = 'running'
                """,
                (now_iso, job_id),
            )
            return conn.total_changes > 0
        finally:
            conn.close()

    def mark_failed(self, job_id: str, error: str) -> bool:
        """Mark a job as failed, with automatic retry or dead-letter (F-05/F-06).

        If attempts < max_attempts: job goes back to pending with backoff delay
        If attempts >= max_attempts: job goes to dead-letter (F-06)
        """
        conn = self._connect()
        try:
            # Read current state
            row = conn.execute(
                "SELECT attempts, max_attempts FROM outbox_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()

            if row is None:
                return False

            attempts, max_attempts = row

            if attempts >= max_attempts:
                # F-06: Dead-letter
                conn.execute(
                    """
                    UPDATE outbox_jobs
                    SET status = 'dead', last_error = ?, lease_owner = ''
                    WHERE job_id = ?
                    """,
                    (error[:1000], job_id),
                )
            else:
                # Retry with backoff
                backoff_idx = min(attempts - 1, len(DEFAULT_BACKOFF_SECONDS) - 1)
                delay = DEFAULT_BACKOFF_SECONDS[max(0, backoff_idx)]
                next_available = _time.time() + delay

                conn.execute(
                    """
                    UPDATE outbox_jobs
                    SET status = 'pending', last_error = ?, lease_owner = '',
                        lease_until = 0.0, available_at = ?
                    WHERE job_id = ?
                    """,
                    (error[:1000], next_available, job_id),
                )

            return True
        finally:
            conn.close()

    # ================================================================
    # F-06: Dead-letter queries
    # ================================================================

    def get_dead_letter(self, limit: int = 20) -> list[Job]:
        """Get jobs in dead-letter queue."""
        return self._query_by_status(JobStatus.DEAD, limit)

    def get_failed(self, limit: int = 20) -> list[Job]:
        """Get jobs that failed but may retry."""
        return self._query_by_status(JobStatus.FAILED, limit)

    def get_pending(self, limit: int = 50) -> list[Job]:
        """Get pending jobs."""
        conn = self._connect()
        try:
            now = _time.time()
            rows = conn.execute(
                """
                SELECT * FROM outbox_jobs
                WHERE status = 'pending' AND available_at <= ?
                ORDER BY available_at ASC
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
            return [Job.from_row(r) for r in rows]
        finally:
            conn.close()

    def get_running(self) -> list[Job]:
        """Get currently running jobs."""
        return self._query_by_status(JobStatus.RUNNING, 50)

    def requeue_dead(self, job_id: str) -> bool:
        """Requeue a dead-letter job back to pending."""
        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE outbox_jobs
                SET status = 'pending', attempts = 0, last_error = '',
                    available_at = ?
                WHERE job_id = ? AND status = 'dead'
                """,
                (_time.time(), job_id),
            )
            return conn.total_changes > 0
        finally:
            conn.close()

    # ================================================================
    # F-07: Idempotency utilities
    # ================================================================

    def is_duplicate(self, dedup_key: str) -> bool:
        """Check if a job with this dedup_key already exists (F-07)."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT 1 FROM outbox_jobs WHERE dedup_key = ?",
                (dedup_key,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    # ================================================================
    # Stats
    # ================================================================

    def get_stats(self) -> dict:
        """Get outbox statistics."""
        conn = self._connect()
        try:
            by_status = conn.execute(
                "SELECT status, COUNT(*) FROM outbox_jobs GROUP BY status"
            ).fetchall()
            total = sum(c for _, c in by_status)
            return {
                "total_jobs": total,
                "by_status": dict(by_status),
                "db_path": str(self._db_path),
            }
        finally:
            conn.close()

    # ================================================================
    # Internal helpers
    # ================================================================

    def _query_by_status(self, status: JobStatus, limit: int) -> list[Job]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM outbox_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status.value, limit),
            ).fetchall()
            return [Job.from_row(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def _generate_job_id(job_type: str, payload: dict) -> str:
        """Generate a deterministic job_id."""
        raw = f"{job_type}|{json.dumps(payload, sort_keys=True)}|{_time.time()}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:12]
        return f"job_{h}"


class OutboxWorker:
    """Simple worker that processes outbox jobs in a loop.

    Usage:
        worker = OutboxWorker(store, handlers={"summary.rebuild": my_handler})
        worker.run_once()  # Process one job
        worker.run_loop(poll_interval=5)  # Continuous loop
    """

    def __init__(self, store: OutboxStore, handlers: dict[str, callable]):
        self._store = store
        self._handlers = handlers

    def run_once(self, job_types: list[str] | None = None) -> Job | None:
        """Claim and process one job. Returns the job or None."""
        job = self._store.claim_next(job_types=job_types)
        if job is None:
            return None

        handler = self._handlers.get(job.job_type)
        if handler is None:
            self._store.mark_failed(job.job_id, f"No handler for job_type: {job.job_type}")
            return job

        try:
            handler(job)
            self._store.mark_complete(job.job_id)
        except Exception as e:
            self._store.mark_failed(job.job_id, str(e))

        return job

    def run_loop(self, poll_interval: float = 5.0, max_jobs: int = -1):
        """Run a continuous processing loop."""
        processed = 0
        while max_jobs < 0 or processed < max_jobs:
            job = self.run_once()
            if job is None:
                _time.sleep(poll_interval)
            else:
                processed += 1
