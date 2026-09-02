// Thin wrapper around the ClauseGuard backend. Reviews are async: POST queues
// a job (returns a review_id), then we poll GET /v1/reviews/{id} until it is
// completed or failed. In dev the Vite proxy forwards /v1/* to FastAPI.

const X_API_KEY = "dev-local-key";

export async function reviewText(text, playbookId = "vendor_saas_buyer") {
  const json = await submit("/v1/reviews", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": X_API_KEY },
    body: JSON.stringify({ text, playbook_id: playbookId }),
  });
  return poll(json.review_id);
}

export async function reviewFile(file, playbookId = "vendor_saas_buyer") {
  const body = new FormData();
  body.append("file", file);
  body.append("playbook_id", playbookId);
  const json = await submit("/v1/reviews/file", {
    method: "POST",
    headers: { "X-API-Key": X_API_KEY },
    body,
  });
  return poll(json.review_id);
}

async function submit(url, options) {
  const res = await fetch(url, options);
  return unwrap(res);
}

async function poll(reviewId) {
  for (;;) {
    const res = await fetch(`/v1/reviews/${reviewId}`, {
      headers: { "X-API-Key": X_API_KEY },
    });
    const body = await unwrap(res);
    if (body.status === "completed") return body.result;
    if (body.status === "failed") throw new Error(body.error || "Review failed");
    await new Promise((r) => setTimeout(r, 500));
  }
}

async function unwrap(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data;
}