// First screen: states what ClauseGuard is and why it's different, then the
// input. The three value props hardcode the product thesis — keep in sync with
// README. Designed as a focused center panel, not a marketing page.

import ConfigCard, { configReady } from "./ConfigCard.jsx";

const VALUE_PROPS = [
  {
    title: "Grounded citations",
    body: "Every finding points at the exact clause that triggered it — verified against the source text, not the model's opinion.",
  },
  {
    title: "Confidence, not guesswork",
    body: "Each flag carries a confidence score and escalates to human review when the model is unsure.",
  },
  {
    title: "Actionable redlines",
    body: "Not just 'this is risky' — a suggested fix you can hand straight to legal.",
  },
];

export default function Landing({
  view,
  setView,
  text,
  setText,
  fileRef,
  onText,
  onFile,
  isLoading,
  error,
  config,
  onConfigChange,
  catalog,
}) {
  const ready = configReady(config, catalog);
  return (
    <div className="flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-8 docs-scroll">
      <div className="w-full max-w-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-white">
            Review a contract against your playbook
          </h1>
          <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-stone-400">
            Paste or upload — ClauseGuard segments the clauses, judges each
            against the buyer standard, and returns ranked deviations with
            grounded citations and redlines.
          </p>
        </div>

        <ConfigCard config={config} onChange={onConfigChange} catalog={catalog} />

        <div className="mt-4">
          <InputCard
            view={view}
            setView={setView}
            text={text}
            setText={setText}
            fileRef={fileRef}
            onText={onText}
            onFile={onFile}
            isLoading={isLoading}
            error={error}
            ready={ready}
          />
        </div>

        <div className="mt-6 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {VALUE_PROPS.map((v, i) => (
            <div
              key={i}
              className="rounded-[4px] border border-hairline bg-ink-800 p-3"
            >
              <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-300">
                {v.title}
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-stone-500">
                {v.body}
              </p>
            </div>
          ))}
        </div>

        <Disclosure />
      </div>
    </div>
  );
}

function InputCard({
  view,
  setView,
  text,
  setText,
  fileRef,
  onText,
  onFile,
  isLoading,
  error,
  ready,
}) {
  const gated = !ready;
  return (
    <div className="rounded-md border border-hairline bg-ink-900">
      <div className="flex items-center gap-1 border-b border-hairline px-4 py-2">
        <Tab active={view === "text"} onClick={() => setView("text")}>
          Paste text
        </Tab>
        <Tab active={view === "file"} onClick={() => setView("file")}>
          Upload file
        </Tab>
        {view === "file" && (
          <span className="ml-auto font-mono text-[10px] uppercase tracking-wide text-stone-600">
            PDF · DOCX · scanned rejected
          </span>
        )}
      </div>

      {view === "text" ? (
        <div className="p-4">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste a contract, or a section of it…"
            rows={7}
            autoFocus
            className="w-full resize-y rounded-[4px] border border-white/10 bg-ink-800 px-3 py-2.5 text-sm text-stone-200 placeholder:text-stone-600 focus:border-white/25 focus:outline-none"
          />
          <div className="mt-3 flex items-center justify-between">
            <span className="font-mono text-[11px] text-stone-600">
              {text.trim() ? `${text.length} chars` : "ready"}
            </span>
            <RunButton
              onClick={onText}
              disabled={isLoading || gated || !text.trim()}
              loading={isLoading}
            >
              Run audit
            </RunButton>
          </div>
        </div>
      ) : (
        <div className="p-4">
          <label
            className={`flex cursor-pointer flex-col items-center gap-2 rounded-[4px] border border-dashed px-4 py-10 text-center ${
              gated
                ? "border-white/10 bg-ink-800/50"
                : "border-white/15 bg-ink-800 hover:border-white/30"
            }`}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="hidden"
              disabled={gated}
              onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
            />
            <span className="text-sm text-stone-300">
              {isLoading
                ? "Auditing…"
                : gated
                  ? "Enter your API key above to unlock"
                  : "Drop a contract here, or click to browse"}
            </span>
            <span className="font-mono text-[11px] text-stone-600">
              .pdf · .docx — digital files only
            </span>
          </label>
        </div>
      )}

      {error && (
        <div className="border-t border-red-500/20 bg-red-500/8 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}
    </div>
  );
}

function Tab({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-[3px] px-2.5 py-1 text-xs transition-colors ${
        active
          ? "bg-white/8 text-white"
          : "text-stone-500 hover:bg-white/5 hover:text-stone-300"
      }`}
    >
      {children}
    </button>
  );
}

function RunButton({ children, onClick, disabled, loading }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="rounded-[4px] bg-amber-400 px-4 py-2 text-sm font-semibold text-amber-950 transition-colors hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {loading ? "Auditing…" : children}
    </button>
  );
}

function Disclosure() {
  return (
    <p className="mt-6 text-center font-mono text-[10px] uppercase tracking-[0.16em] text-stone-600">
      Review assistance — not legal advice
    </p>
  );
}
