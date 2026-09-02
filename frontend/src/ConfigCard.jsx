// Bring-your-own-key setup: provider, model, API key. The key never leaves the
// browser except inside the one review POST (the vendor receives it directly and
// charges the caller's quota). Held in localStorage via src/api.js so a
// refresh keeps the session's choice only if that browser chooses to.

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

export default function ConfigCard({ config, onChange, catalog }) {
  const provider = catalog[config.provider] ? config.provider : Object.keys(catalog)[0];
  const providerDef = catalog[provider];
  const model = providerDef.models.includes(config.model)
    ? config.model
    : providerDef.models[0];
  const hasKey = Boolean(config.api_key && config.api_key.trim());

  return (
    <div className="rounded-md border border-hairline bg-ink-900">
      <div className="flex items-center gap-2 border-b border-hairline px-4 py-2">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            hasKey ? "bg-emerald-400" : "bg-stone-700"
          }`}
        />
        <span className="text-xs font-medium text-stone-300">
          {hasKey ? "Connected — your model, your quota" : "Bring your own API key"}
        </span>
        <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.16em] text-stone-600">
          stored in this browser only
        </span>
      </div>

      <div className="grid gap-3 p-4 sm:grid-cols-[minmax(0,5fr)_minmax(0,7fr)_minmax(0,9fr)]">
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
    </div>
  );
}

const selectCls =
  "w-full rounded-[4px] border border-white/10 bg-ink-800 px-3 py-2 text-sm text-stone-200 placeholder:text-stone-600 focus:border-white/25 focus:outline-none";

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1 flex font-mono text-[10px] uppercase tracking-[0.14em] text-stone-600">
        {label}
      </span>
      {children}
    </label>
  );
}