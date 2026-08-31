"""Full eval run against the real configured model.

Requires a provider key (e.g. GROQ_API_KEY). Not run in CI — CI exercises the
metric math and pipeline wiring deterministically. Run locally:

    uv run python -m evals.runners.run_evals

Emits a JSON + Markdown report under evals/reports/.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.models.enums import FindingStatus
from app.orchestrator.pipeline import review_contract
from app.playbooks.loader import load_playbook
from evals.metrics import aggregate

_DATASET = Path(__file__).parents[1] / "datasets" / "sample" / "contracts.jsonl"
_REPORTS = Path(__file__).parents[1] / "reports"


def _load_dataset() -> list[dict]:
    lines = _DATASET.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


async def run() -> dict:
    playbook = load_playbook("vendor_saas_buyer")
    settings = get_settings()
    pairs: list[tuple[set[str], set[str]]] = []

    for example in _load_dataset():
        result = await review_contract(example["text"], playbook, settings)
        predicted = {
            f.category.value
            for f in result.findings
            if f.status == FindingStatus.DEVIATION
        }
        gold = set(example["gold_deviations"])
        pairs.append((predicted, gold))

    metrics = {
        **aggregate(pairs),
        "provider": settings.provider,
        "model_strong": settings.model_strong,
        "model_cheap": settings.model_cheap,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return metrics


def main() -> None:
    metrics = asyncio.run(run())
    _REPORTS.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    (_REPORTS / f"eval-{stamp}.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
