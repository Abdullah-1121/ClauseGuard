// Thin wrapper around the ClauseGuard backend. In dev the Vite proxy forwards
// /v1/* to the FastAPI server, so no origin is hardcoded here.

const X_API_KEY = "dev-local-key";

export async function reviewText(text, playbookId = "vendor_saas_buyer") {
  const res = await fetch("/v1/reviews", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": X_API_KEY,
    },
    body: JSON.stringify({ text, playbook_id: playbookId }),
  });
  return unwrap(res);
}

export async function reviewFile(file, playbookId = "vendor_saas_buyer") {
  const body = new FormData();
  body.append("file", file);
  body.append("playbook_id", playbookId);
  const res = await fetch("/v1/reviews/file", {
    method: "POST",
    headers: { "X-API-Key": X_API_KEY },
    body,
  });
  return unwrap(res);
}

async function unwrap(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data.result;
}
