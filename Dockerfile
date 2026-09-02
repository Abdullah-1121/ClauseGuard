# Single-container deploy: build the frontend, then serve it from FastAPI.
# Works on Railway, Fly.io, and Render (all auto-detect a root Dockerfile).
#
# Runtime needs only the env vars: GROQ_API_KEY, CLAUSEGUARD_API_KEYS
# (must include the key the UI sends), optionally CLAUSEGUARD_DB_PATH.

# ── Stage 1: build the frontend ─────────────────────────────────────────────
FROM node:22-slim AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: backend + static ───────────────────────────────────────────────
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv /uv /uv/bin/uv
ENV UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
# pyproject's readme is "../README.md" — resolved to /README.md.
COPY README.md /README.md
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY --from=frontend /src/dist ./static
ENV PATH="/app/.venv/bin:$PATH"
# HF Spaces expects the app on 7860 and injects PORT there; keep a sane default.
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]