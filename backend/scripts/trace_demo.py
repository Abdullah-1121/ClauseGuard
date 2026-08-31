"""Token-safe Langfuse tracing demo.

Runs a tiny 2-clause contract through the pipeline with tracing enabled, then
flushes so traces land in Langfuse before this short-lived process exits.

Usage:
    LANGFUSE_PUBLIC_KEY=... LANGFUSE_SECRET_KEY=... \
        uv run python -m scripts.trace_demo

Without keys this is a harmless no-op run (decorators pass through).
"""

from __future__ import annotations

import asyncio

from app.obs.langfuse import flush, is_enabled
from app.orchestrator.pipeline import review_contract
from app.playbooks.loader import load_playbook

TINY_CONTRACT = (
    "1. Limitation of Liability. Vendor's liability shall be unlimited.\n"
    "\n"
    "2. Assignment. Customer shall not assign without prior written consent."
)


async def main() -> None:
    playbook = load_playbook("vendor_saas_buyer")
    result = await review_contract(TINY_CONTRACT, playbook)
    print(f"clause_count={result.clause_count} findings={len(result.findings)}")
    for f in result.findings:
        print(f"  [{f.category}] {f.status} risk={f.risk_level}")
    if is_enabled():
        flush()
        print("traces flushed to Langfuse")
    else:
        print("Langfuse not configured — no traces sent")


if __name__ == "__main__":
    asyncio.run(main())
