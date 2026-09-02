"""ReviewStore tests — real SQLite files in tmp_path, no infra required."""

from __future__ import annotations

from app.store import ReviewStore


async def test_lifecycle_round_trip(tmp_path):
    store = ReviewStore(str(tmp_path / "jobs.db"))
    await store.create("job-1", "vendor_saas_buyer")

    row = await store.get("job-1")
    assert row["status"] == "pending"
    assert row["playbook_id"] == "vendor_saas_buyer"
    assert row["result"] is None

    await store.transition("job-1", "running")
    assert (await store.get("job-1"))["status"] == "running"

    await store.transition("job-1", "completed", result='{"findings": []}')
    row = await store.get("job-1")
    assert row["status"] == "completed"
    assert row["result"] == '{"findings": []}'


async def test_failed_job_stores_error(tmp_path):
    store = ReviewStore(str(tmp_path / "jobs.db"))
    await store.create("job-2", "vendor_saas_buyer")
    await store.transition("job-2", "failed", error="boom")
    row = await store.get("job-2")
    assert row["status"] == "failed"
    assert row["error"] == "boom"
    assert row["result"] is None


async def test_get_missing_job_returns_none(tmp_path):
    store = ReviewStore(str(tmp_path / "jobs.db"))
    assert await store.get("nope") is None


async def test_schema_create_is_idempotent(tmp_path):
    path = str(tmp_path / "jobs.db")
    ReviewStore(path)
    ReviewStore(path)  # second init must not raise


async def test_jobs_survive_a_new_store_on_same_file(tmp_path):
    path = str(tmp_path / "jobs.db")
    await ReviewStore(path).create("job-3", "vendor_saas_buyer")
    reloaded = await ReviewStore(path).get("job-3")
    assert reloaded is not None
    assert reloaded["status"] == "pending"


async def test_token_budget_accumulates_per_day(tmp_path):
    store = ReviewStore(str(tmp_path / "jobs.db"))
    assert await store.tokens_spent("2026-09-02") == 0
    await store.add_token_spend("2026-09-02", 100)
    await store.add_token_spend("2026-09-02", 50)
    assert await store.tokens_spent("2026-09-02") == 150
    assert await store.tokens_spent("2026-09-03") == 0
