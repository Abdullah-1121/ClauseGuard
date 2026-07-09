# ClauseGuard — Frontend (planned)

Next.js + Tailwind UI for uploading a contract and viewing the risk-flagged
findings inline over the document text.

Scaffolded in a later milestone (SPEC §14, week 5). Planned:

- Upload / paste a contract, pick a playbook.
- Rendered contract with clause highlights color-coded by risk level.
- Findings panel: rationale, suggested redline, "needs human review" badges.
- Calls the backend `POST /v1/reviews` endpoint.
