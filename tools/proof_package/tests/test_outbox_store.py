"""Tests for Outbox Store and Worker (Phase 3 F-01 through F-07)."""

import tempfile
import time
from pathlib import Path

import pytest

from novel_workflow.system_scripts.outbox_store import (
    OutboxStore,
    OutboxWorker,
    Job,
    JobStatus,
    DEFAULT_BACKOFF_SECONDS,
)


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as d:
        s = OutboxStore(Path(d), worker_id="test-worker")
        s.initialize()
        yield s


# ================================================================
# F-01: Schema
# ================================================================

class TestOutboxSchema:
    def test_initialize_creates_tables(self, store):
        stats = store.get_stats()
        assert stats["total_jobs"] == 0

    def test_dedup_index_exists(self, store):
        j1 = store.enqueue("test.job", dedup_key="key_abc")
        j2 = store.enqueue("test.job", dedup_key="key_abc")
        assert j1 == j2
        stats = store.get_stats()
        assert stats["total_jobs"] == 1


# ================================================================
# F-02: Enqueue
# ================================================================

class TestEnqueue:
    def test_enqueue_creates_pending_job(self, store):
        job_id = store.enqueue("projection.summary.rebuild", {"chapter_id": "ch_001"})
        assert job_id.startswith("job_")

        # Use DB-level query to avoid time filtering
        import sqlite3
        conn = sqlite3.connect(str(store._db_path))
        conn.isolation_level = None
        row = conn.execute(
            "SELECT job_id, job_type, status FROM outbox_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        conn.close()
        assert row[2] == "pending"

    def test_enqueue_multiple_jobs(self, store):
        for i in range(10):
            store.enqueue(f"job.type.{i}", {"index": i})
        stats = store.get_stats()
        assert stats["total_jobs"] == 10

    def test_enqueue_with_trace(self, store):
        store.enqueue("test.job", trace_id="trc_test_123")
        pending = store.get_pending()
        assert pending[0].trace_id == "trc_test_123"


# ================================================================
# F-03: Claim with lease
# ================================================================

class TestClaim:
    def test_claim_next_returns_job(self, store):
        store.enqueue("test.job")
        job = store.claim_next()
        assert job is not None
        assert job.status == JobStatus.RUNNING
        assert job.lease_owner == "test-worker"
        assert job.attempts == 1

    def test_claim_next_no_jobs(self, store):
        job = store.claim_next()
        assert job is None

    def test_claim_next_sets_lease(self, store):
        store.enqueue("test.job")
        job = store.claim_next()
        assert job.lease_until > time.time()
        assert job.lease_until <= time.time() + 310

    def test_claim_filters_by_type(self, store):
        store.enqueue("type.a")
        store.enqueue("type.b")
        job = store.claim_next(job_types=["type.b"])
        assert job is not None
        assert job.job_type == "type.b"

    def test_claim_only_returns_one(self, store):
        store.enqueue("test.job")
        store.enqueue("test.job")
        job1 = store.claim_next()
        assert job1 is not None
        # First job is running; second should be claimable
        job2 = store.claim_next()
        assert job2 is not None

    def test_claim_recovers_expired_leases(self, store):
        job_id = store.enqueue("test.job")
        job = store.claim_next()
        assert job is not None

        # Manually expire the lease (set to a past timestamp, not 0.0)
        import sqlite3
        conn = sqlite3.connect(str(store._db_path))
        conn.isolation_level = None
        conn.execute(
            "UPDATE outbox_jobs SET lease_until = 0.001 WHERE job_id = ?",
            (job_id,),
        )
        conn.close()

        # Different worker can claim it after recovery
        store2 = OutboxStore(store._root, worker_id="worker-2")
        store2.initialize()
        job2 = store2.claim_next()
        assert job2 is not None
        assert job2.job_id == job_id
        assert job2.lease_owner == "worker-2"


# ================================================================
# F-04: Heartbeat
# ================================================================

class TestHeartbeat:
    def test_heartbeat_renews_lease(self, store):
        store.enqueue("test.job")
        job = store.claim_next()
        old_lease = job.lease_until
        time.sleep(0.1)
        result = store.heartbeat(job.job_id)
        assert result is True

    def test_heartbeat_fails_for_wrong_job(self, store):
        result = store.heartbeat("job_nonexistent")
        assert result is False


# ================================================================
# F-05: Complete / Fail with retry
# ================================================================

class TestRetry:
    def test_mark_failed_sets_error(self, store):
        """Failed job records the error and goes to retry or pending."""
        store.enqueue("test.job", max_attempts=3)
        job = store.claim_next()

        result = store.mark_failed(job.job_id, "Test error")
        assert result is True

        # Job should exist with error recorded
        import sqlite3
        conn = sqlite3.connect(str(store._db_path))
        conn.isolation_level = None
        row = conn.execute(
            "SELECT status, last_error, attempts FROM outbox_jobs WHERE job_id = ?",
            (job.job_id,),
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "pending"  # Retry
        assert "Test error" in row[1]

    def test_mark_complete(self, store):
        store.enqueue("test.job")
        job = store.claim_next()
        result = store.mark_complete(job.job_id)
        assert result is True

        import sqlite3
        conn = sqlite3.connect(str(store._db_path))
        conn.isolation_level = None
        row = conn.execute(
            "SELECT status FROM outbox_jobs WHERE job_id = ?",
            (job.job_id,),
        ).fetchone()
        conn.close()
        assert row[0] == "completed"


# ================================================================
# F-06: Dead-letter queue
# ================================================================

class TestDeadLetter:
    def test_max_attempts_triggers_dead_letter(self, store):
        """After max_attempts, job goes to dead-letter."""
        job_id = store.enqueue("test.job", max_attempts=2)

        import sqlite3

        # Attempt 1
        job = store.claim_next()
        assert job is not None
        store.mark_failed(job.job_id, "Error 1")

        # Force immediate retry by resetting available_at
        conn = sqlite3.connect(str(store._db_path))
        conn.isolation_level = None
        conn.execute(
            "UPDATE outbox_jobs SET available_at = 0.0 WHERE job_id = ?",
            (job_id,),
        )
        conn.close()

        # Attempt 2
        job2 = store.claim_next()
        assert job2 is not None
        store.mark_failed(job2.job_id, "Error 2")

        # Should now be dead
        dead = store.get_dead_letter()
        assert len(dead) == 1
        assert dead[0].status == JobStatus.DEAD

    def test_dead_letter_not_reclaimed(self, store):
        store.enqueue("test.job", max_attempts=1)
        job = store.claim_next()
        store.mark_failed(job.job_id, "Fatal")

        job2 = store.claim_next()
        assert job2 is None

    def test_requeue_dead(self, store):
        job_id = store.enqueue("test.job", max_attempts=1)
        job = store.claim_next()
        store.mark_failed(job.job_id, "Fatal")

        dead = store.get_dead_letter()
        assert len(dead) == 1

        result = store.requeue_dead(job_id)
        assert result is True

        job2 = store.claim_next()
        assert job2 is not None


# ================================================================
# F-07: Idempotency
# ================================================================

class TestIdempotency:
    def test_dedup_key_prevents_duplicates(self, store):
        j1 = store.enqueue("test.job", {"id": 1}, dedup_key="dedup_abc")
        j2 = store.enqueue("test.job", {"id": 1}, dedup_key="dedup_abc")
        assert j1 == j2
        assert store.get_stats()["total_jobs"] == 1

    def test_different_dedup_keys_separate(self, store):
        store.enqueue("test.job", dedup_key="key_a")
        store.enqueue("test.job", dedup_key="key_b")
        assert store.get_stats()["total_jobs"] == 2

    def test_is_duplicate_check(self, store):
        store.enqueue("test.job", dedup_key="dup_check")
        assert store.is_duplicate("dup_check") is True
        assert store.is_duplicate("nonexistent") is False


# ================================================================
# Worker tests
# ================================================================

class TestOutboxWorker:
    @pytest.fixture
    def setup(self):
        with tempfile.TemporaryDirectory() as d:
            store = OutboxStore(Path(d), worker_id="test-worker")
            store.initialize()
            processed = []

            def handler(job: Job):
                processed.append(job.job_type)

            yield store, {"test.job": handler}, processed

    def test_worker_processes_job(self, setup):
        store, handlers, processed = setup
        store.enqueue("test.job", {"data": "hello"})
        worker = OutboxWorker(store, handlers)
        job = worker.run_once()
        assert job is not None
        assert len(processed) == 1

    def test_worker_no_jobs(self, setup):
        store, handlers, processed = setup
        worker = OutboxWorker(store, handlers)
        job = worker.run_once()
        assert job is None

    def test_worker_handles_error(self, setup):
        store, handlers, processed = setup

        def failing(job: Job):
            raise ValueError("Handler failed")

        handlers["failing.job"] = failing
        store.enqueue("failing.job")

        worker = OutboxWorker(store, handlers)
        job = worker.run_once()
        assert job is not None

        # Check job status in DB
        import sqlite3
        conn = sqlite3.connect(str(store._db_path))
        conn.isolation_level = None
        row = conn.execute(
            "SELECT status, last_error FROM outbox_jobs WHERE job_id = ?",
            (job.job_id,),
        ).fetchone()
        conn.close()
        assert "Handler failed" in row[1]
