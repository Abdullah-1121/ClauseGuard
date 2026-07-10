"""Download + normalize the CUAD dataset into an eval-ready form.

CUAD (https://www.atticusprojectai.org/cuad, CC BY 4.0) ships as a SQuAD-style
JSON: 510 contracts, each with 41 questions (one per clause category). A category
is *present* in a contract when its question has a non-empty answer span. The
category name is encoded in each question id after the '__' separator.

This script:
  1. downloads CUAD_v1.zip from Zenodo (canonical host) and extracts CUAD_v1.json
  2. maps CUAD's 41 categories -> our 12 playbook categories
  3. writes a normalized JSONL: {id, text, gold_categories}
  4. writes deterministic train/dev/test id splits (committed, for reproducibility)

Run:  uv run python -m evals.cuad_ingest
Large artifacts land under evals/datasets/cuad/ (gitignored); only the small
split files under evals/splits/ are committed.
"""

from __future__ import annotations

import json
import random
import urllib.request
import zipfile
from pathlib import Path

from app.models.enums import ClauseCategory

ZENODO_URL = "https://zenodo.org/records/4595826/files/CUAD_v1.zip"
SEED = 42

_DATA_DIR = Path(__file__).parent / "datasets" / "cuad"
_SPLITS_DIR = Path(__file__).parent / "splits"
_ZIP_PATH = _DATA_DIR / "CUAD_v1.zip"
_JSON_PATH = _DATA_DIR / "CUAD_v1.json"
_NORMALIZED = _DATA_DIR / "contracts.jsonl"

# CUAD category name (as it appears after '__' in the qa id) -> our category.
# Categories not listed are outside our buyer-side playbook and ignored.
CUAD_TO_OURS: dict[str, ClauseCategory] = {
    "Cap On Liability": ClauseCategory.CAP_ON_LIABILITY,
    "Uncapped Liability": ClauseCategory.UNCAPPED_LIABILITY,
    "Anti-Assignment": ClauseCategory.ANTI_ASSIGNMENT,
    "Termination For Convenience": ClauseCategory.TERMINATION_FOR_CONVENIENCE,
    "Renewal Term": ClauseCategory.RENEWAL_TERM,
    "Governing Law": ClauseCategory.GOVERNING_LAW,
    "Non-Compete": ClauseCategory.NON_COMPETE,
    "Exclusivity": ClauseCategory.EXCLUSIVITY,
    "Most Favored Nation": ClauseCategory.MOST_FAVORED_NATION,
    "Ip Ownership Assignment": ClauseCategory.IP_OWNERSHIP_ASSIGNMENT,
    "Audit Rights": ClauseCategory.AUDIT_RIGHTS,
    "Insurance": ClauseCategory.INSURANCE,
}


def _report_progress(block: int, block_size: int, total: int) -> None:
    done = block * block_size
    pct = min(100, done * 100 // total) if total else 0
    print(f"\r  downloading CUAD_v1.zip ... {pct}% ({done // 1_000_000} MB)", end="")


def download() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _JSON_PATH.exists():
        print(f"[ok]{_JSON_PATH.name} already present, skipping download")
        return
    if not _ZIP_PATH.exists():
        urllib.request.urlretrieve(ZENODO_URL, _ZIP_PATH, _report_progress)
        print()
    print("  extracting CUAD_v1.json ...")
    with zipfile.ZipFile(_ZIP_PATH) as zf:
        member = next(n for n in zf.namelist() if n.endswith("CUAD_v1.json"))
        with zf.open(member) as src, open(_JSON_PATH, "wb") as dst:
            dst.write(src.read())
    print(f"[ok]extracted {_JSON_PATH}")


def _category_from_qa_id(qa_id: str) -> str:
    return qa_id.rsplit("__", 1)[-1].strip()


def normalize() -> list[dict]:
    raw = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
    records: list[dict] = []
    for entry in raw["data"]:
        title = entry["title"]
        para = entry["paragraphs"][0]
        text = para["context"]
        present: set[str] = set()
        for qa in para["qas"]:
            if qa.get("is_impossible") or not qa.get("answers"):
                continue
            ours = CUAD_TO_OURS.get(_category_from_qa_id(qa["id"]))
            if ours is not None:
                present.add(ours.value)
        records.append({"id": title, "text": text, "gold_categories": sorted(present)})
    return records


def write_splits(records: list[dict]) -> dict[str, int]:
    _SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    ids = sorted(r["id"] for r in records)
    random.Random(SEED).shuffle(ids)
    n = len(ids)
    train, dev, test = ids[: int(n * 0.7)], ids[int(n * 0.7) : int(n * 0.85)], ids[int(n * 0.85) :]
    for name, split in (("train", train), ("dev", dev), ("test", test)):
        (_SPLITS_DIR / f"{name}.txt").write_text("\n".join(split) + "\n", encoding="utf-8")
    return {"train": len(train), "dev": len(dev), "test": len(test)}


def main() -> None:
    download()
    records = normalize()
    with open(_NORMALIZED, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    sizes = write_splits(records)

    with_labels = sum(1 for r in records if r["gold_categories"])
    total_labels = sum(len(r["gold_categories"]) for r in records)
    print(f"[ok]normalized {len(records)} contracts -> {_NORMALIZED}")
    print(f"  {with_labels} have >=1 playbook-relevant clause; {total_labels} gold labels total")
    print(f"  splits: {sizes}")


if __name__ == "__main__":
    main()
