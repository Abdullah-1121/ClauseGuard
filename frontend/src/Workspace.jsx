import DocumentPane from "./DocumentPane.jsx";
import FindingsPanel from "./FindingsPanel.jsx";

// Two-pane audit workspace:
//   left  — findings ranked by risk, clickable
//   right — the source document, with the active finding's citation
//           highlighted and scrolled into view (grounded-citations story)
// The top strip is a compact summary + controls.
export default function Workspace({ result, source, activeIndex, setActiveIndex, onReset }) {
  const findings = result.findings || [];
  const deviations = findings.filter((f) => f.status === "DEVIATION").length;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Strip
        result={result}
        deviations={deviations}
        onReset={onReset}
        onSelect={(i) => setActiveIndex(i)}
        count={findings.length}
      />

      <div className="grid min-h-0 flex-1 grid-cols-[340px_1fr] border-t border-hairline">
        <FindingsPanel
          findings={findings}
          activeIndex={activeIndex}
          onSelect={setActiveIndex}
        />
        {source ? (
          <DocumentPane
            text={source}
            findings={findings}
            activeIndex={activeIndex}
            onSelect={setActiveIndex}
          />
        ) : (
          <EmptyDoc note="Uploaded file — source text unavailable to highlight." />
        )}
      </div>
    </div>
  );
}

function Strip({ result, deviations, onReset, count }) {
  return (
    <div className="flex items-center gap-5 border-b border-hairline bg-ink-900 px-6 py-3">
      <Metric label="Clauses" value={result.clause_count} />
      <Metric label="Deviations" value={deviations} accent=" text-red-600" />
      <Metric label="Compliant" value={(result.clause_count || 0) - deviations} />
      <div className="ml-auto flex items-center gap-4">
        <span className="font-mono text-[11px] text-stone-500">
          {result.usage?.input_tokens + result.usage?.output_tokens
            ? `${result.usage.input_tokens + result.usage.output_tokens} tok`
            : "--"}
        </span>
        <span className="font-mono text-[11px] text-stone-500">
          {result.usage?.latency_ms ? `${Math.round(result.usage.latency_ms)} ms` : "--"}
        </span>
        <span className="font-mono text-[11px] text-stone-500">
          {count} finding{count === 1 ? "" : "s"}
        </span>
        <button
          onClick={onReset}
          className="rounded-[4px] border border-black/12 px-3 py-1.5 text-xs text-stone-600 transition-colors hover:border-black/25 hover:text-stone-900"
        >
          New audit
        </button>
      </div>
    </div>
  );
}

function Metric({ label, value, accent = "" }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className={`text-xl font-semibold tabular-nums text-stone-900` + accent}>
        {value}
      </span>
      <span className="font-mono text-[10px] uppercase tracking-wide text-stone-500">
        {label}
      </span>
    </div>
  );
}

function EmptyDoc({ note }) {
  return (
    <div className="flex items-center justify-center bg-ink-900/40 p-8">
      <p className="font-mono text-xs text-stone-500">{note}</p>
    </div>
  );
}
