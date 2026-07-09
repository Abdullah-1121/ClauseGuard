"""Load playbooks from YAML into validated Playbook models."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.models.schemas import Playbook

_DIR = Path(__file__).parent


def list_playbooks() -> list[str]:
    return sorted(p.stem for p in _DIR.glob("*.yaml"))


@lru_cache
def load_playbook(playbook_id: str) -> Playbook:
    path = _DIR / f"{playbook_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown playbook: {playbook_id}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Playbook(**data)
