# ClauseGuard — Frontend

A minimal Vite + React + Tailwind single-page app for uploading a contract and
viewing risk-flagged findings inline over the document text.

## What it does

- Paste contract text **or** upload a file (digital PDF / DOCX).
- Renders the source with each finding's citation highlighted, color-coded by risk.
- Findings panel: risk level, status, rationale, suggested redline, "needs human
  review" badge, and a summary (clauses / deviations / compliant, latency, tokens).

## Stack

Vite · React 18 · Tailwind CSS. No router, no state library, no build of extra
deps. The dev server proxies `/v1/*` to the FastAPI backend.

## Run it

```bash
# terminal 1 — backend (from backend/)
uv run uvicorn app.main:app --reload

# terminal 2 — frontend
cd frontend
npm install
npm run dev      # → http://localhost:5173
```

The UI calls the backend with the `dev-local-key` API key via the Vite proxy, so
no origin/CORS config is needed in development.

## Layout

```
src/
  api.js            # fetch wrappers for /v1/reviews and /v1/reviews/file
  App.jsx           # page shell + input + results wiring
  DocumentPane.jsx  # source text with citation highlights
  FindingsPanel.jsx # summary + per-finding cards
  risk.js           # risk/status → style mapping (single source)
```

## Note (honest)

Risk levels come from the live model. On the free tier an open-weight model can
occasionally assign `risk_level: none` while writing a high-risk rationale. The
backend's `confidence` gate and `needs_human_review` flag are the mechanisms that
surface this to a human — the UI badges it accordingly.
