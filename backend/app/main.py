"""FastAPI application entrypoint.

Run locally:  uv run uvicorn app.main:app --reload

In production the image mounts the built frontend (`frontend/dist`) at
`/app/static` and FastAPI serves it, so one container runs API + UI. The mount
is skipped when no static dir exists (local dev uses the Vite server instead).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.store import ReviewStore

STATIC_DIR = os.environ.get("CLAUSEGUARD_STATIC_DIR", "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = ReviewStore(get_settings().db_path)
    yield


app = FastAPI(
    title="ClauseGuard",
    version="0.1.0",
    description="Reliability-engineered AI contract review agent.",
    lifespan=lifespan,
)

# CORS is not a security boundary here: the API is stateless and BYOK (every
# POST carries its own key), so allow any origin by default and let callers
# tighten via CLAUSEGUARD_CORS_ORIGINS if they proxy it behind auth.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip()
        for o in os.environ.get("CLAUSEGUARD_CORS_ORIGINS", "*").split(",")
        if o.strip()
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# API routes are registered before the catch-all static mount, so /v1/* and
# /healthz always win. html=True serves index.html at "/".
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
