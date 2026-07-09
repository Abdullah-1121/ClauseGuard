"""Test configuration.

Sets a dummy provider key and forbids real network model calls, so the whole
suite runs deterministically and offline. Tests that need model output override
the agents with pydantic-ai's TestModel/FunctionModel.
"""

from __future__ import annotations

import os

# Must be set before app modules build their agents at import time.
os.environ.setdefault("CLAUSEGUARD_PROVIDER", "groq")
os.environ.setdefault("GROQ_API_KEY", "test-key-not-real")

from pydantic_ai import models  # noqa: E402

# Any accidental real request will raise instead of hitting the network.
models.ALLOW_MODEL_REQUESTS = False
