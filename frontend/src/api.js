// Thin wrapper around the ClauseGuard backend. Reviews are async: POST queues
// a job (returns a review_id), then we poll GET /v1/reviews/{id} until it is
// completed or failed.
//
// Bring-your-own-key: the caller's provider/api_key/model travel in the POST
// body and are held in localStorage (never the server's key). In dev the Vite
// proxy forwards /v1/* to FastAPI; for a deployed backend set VITE_API_BASE_URL.

const CONFIG_KEY = "clauseguard-config";

export function loadConfig() {
  try {
    return JSON.parse(localStorage.getItem(CONFIG_KEY) || "{}");
  } catch {
    return {};
  }
}

export function saveConfig(config) {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
}

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchModels() {
  const res = await fetch(`${BASE}/v1/models`);
  return unwrap(res);
}

export async function reviewText(text, cfg, playbookId = "vendor_saas_buyer") {
  const body = { text, playbook_id: playbookId };
  Object.assign(body, byokFields(cfg));
  const json = await submit(`${BASE}/v1/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return poll(json.review_id);
}

export async function reviewFile(file, cfg, playbookId = "vendor_saas_buyer") {
  const body = new FormData();
  body.append("file", file);
  body.append("playbook_id", playbookId);
  for (const [k, v] of Object.entries(byokFields(cfg))) {
    if (v) body.append(k, v);
  }
  const json = await submit(`${BASE}/v1/reviews/file`, {
    method: "POST",
    body,
  });
  return poll(json.review_id);
}

function byokFields(cfg) {
  return {
    provider: cfg.provider || undefined,
    api_key: cfg.api_key || undefined,
    model: cfg.model || undefined,
  };
}

async function submit(url, options) {
  const res = await fetch(url, options);
  return unwrap(res);
}

async function poll(reviewId) {
  for (;;) {
    const res = await fetch(`${BASE}/v1/reviews/${reviewId}`);
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