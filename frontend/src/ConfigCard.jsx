// Bring-your-own-key setup: provider, model, API key. The key never leaves the
// browser except inside the one review POST (the vendor receives it directly and
// charges the caller's quota). Held in localStorage via src/api.js so a
// refresh keeps the session's choice only if that browser chooses to.
//
// Rendered as an "engine bar": a machined hairline row that collapses to a
// one-line status readout once a key is in place, and expands to the three
// fields while it isn't. Connected reads "your model, your quota".

import { useState } from "react";

export const DEFAULT_CATALOG = {
  groq: {
    label: "Groq",
    base_url: "",
    models: [
      "llama-3.3-70b-versatile",
      "openai/gpt-oss-120b",
      "openai/gpt-oss-20b",
      "meta-llama/llama-3.1-8b-instant",
    ],
  },
  openrouter: {
    label: "OpenRouter",
    base_url: "https://openrouter.ai/api/v1",
    models: [
      "openai/gpt-4o-mini",
      "openai/gpt-4.1-mini",
      "google/gemini-2.0-flash-001",
      "meta-llama/llama-3.3-70b-instruct",
      "deepseek/deepseek-chat-v3-0324:free",
    ],
  },
};

export function configReady(config, catalog) {
  const def = catalog[config.provider] || catalog[Object.keys(catalog)[0]];
  return Boolean(config.api_key && config.api_key.trim() && def);
}

function maskKey(key) {
  const k = key.trim();
  return k.length > 8 ? `…${k.slice(-4)}` : "…";
}

export default function ConfigCard({ config, onChange, catalog }) {
  const provider = catalog[config.provider] ? config.provider : Object.keys(catalog)[0];
  const providerDef = catalog[provider];
  const model = providerDef.models.includes(config.model)
    ? config.model
    : providerDef.models[0];
  const hasKey = Boolean(config.api_key && config.api_key.trim());
  const [open, setOpen] = useState(!hasKey);

  return (
    <div className="machined rounded-[4px] border border-hairline bg-ink-900">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-4 py-2.5 text-left"
        aria-expanded={open}
      >
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${
            hasKey ? "bg-emerald-500" : "bg-stone-400"
          }`}
        />
        <span className="flex min-w-0 items-center gap-2 text-xs">
          <span className={`font-medium ${hasKey ? "text-stone-800" : "text-stone-600"}`}>
            {hasKey ? "Connected" : "Bring your own API key"}
          </span>
          {hasKey && (
            <span className="truncate font-mono text-[11px] text-stone-500">
              {providerDef.label} · {model} · {maskKey(config.api_key)}
            </span>
          )}
        </span>
        <span className="ml-auto hidden font-mono text-[10px] uppercase tracking-[0.16em] text-stone-500 sm:block">
          your model · your quota
        </span>
        <svg
          viewBox="0 0 12 12"
          className={`h-3 w-3 shrink-0 text-stone-500 transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div className="grid gap-3 border-t border-hairline p-4 sm:grid-cols-[minmax(0,5fr)_minmax(0,7fr)_minmax(0,9fr)]">
          <Field label="Provider">
            <select
              value={provider}
              onChange={(e) => {
                const p = e.target.value;
                onChange({ provider: p, model: catalog[p].models[0] });
              }}
              className={selectCls}
            >
              {Object.entries(catalog).map(([key, def]) => (
                <option key={key} value={key}>
                  {def.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Model">
            <select
              value={model}
              onChange={(e) => onChange({ model: e.target.value })}
              className={selectCls}
            >
              {providerDef.models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </Field>

          <Field label="API key">
            <input
              type="password"
              value={config.api_key || ""}
              onChange={(e) => onChange({ api_key: e.target.value })}
              placeholder={
                provider === "groq"
                  ? "gsk_… (console.groq.com)"
                  : "sk-or-… (openrouter.ai)"
              }
              autoComplete="off"
              spellCheck={false}
              className={selectCls}
            />
          </Field>
        </div>
      )}
    </div>
  );
}

const selectCls =
  "w-full rounded-[4px] border border-black/10 bg-ink-800 px-3 py-2 text-sm text-stone-800 placeholder:text-stone-400 focus:border-black/25 focus:outline-none";

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1 flex font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500">
        {label}
      </span>
      {children}
    </label>
  );
}