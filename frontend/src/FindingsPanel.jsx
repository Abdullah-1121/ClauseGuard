import { statusConfig, riskConfig } from "./risk.js";

// Ranked finding list.
export default function FindingsPanel({ findings, activeIndex, onSelect }) {
  if (findings.length === 0) {
    return (
      <aside className="border-r border-hairline bg-ink-900 p-6">
        <p className="font-mono text-xs text-stone-500">No deviations flagged.</p>
        <p className="mt-1.5 text-xs leading-relaxed text-stone-600">
          Every clause was checked against the playbook — nothing needed a redline.
        </p>
      </aside>
    );
  }

  return (
    <aside className="flex flex-col overflow-hidden border-r border-hairline bg-ink-900">
      <div className="border-b border-hairline px-4 py-2.5 font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500">
        Findings · ranked by risk
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto docs-scroll">
        {findings.map((f, i) => (
          <FindingRow
            key={i}
            finding={f}
            index={i}
            active={i === activeIndex}
            onSelect={() => onSelect(i)}
          />
        ))}
      </div>
    </aside>
  );
}

function FindingRow({ finding, index, active, onSelect }) {
  const r = riskConfig(finding.risk_level);
  const s = statusConfig(finding.status);
  const pct = Math.round((finding.confidence ?? 0) * 100);

  return (
    <button
      onClick={onSelect}
      className={`block w-full border-b border-hairline/70 border-l-2 px-4 py-3 text-left transition-colors ${
        active ? r.border + " bg-white/[0.03]" : "border-l-transparent hover:bg-white/[0.015]"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full ${r.dot}`} />
        <span className="flex-1 font-mono text-[11px] uppercase tracking-wide text-stone-400">
          #{index + 1} · {finding.category}
        </span>
        <span className={`rounded-[2px] border px-1.5 py-0.5 font-mono text-[9px] uppercase ${r.badge}`}>
          {r.label}
        </span>
      </div>

      <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-stone-400">
        {finding.rationale}
      </p>

      <div className="mt-2 flex items-center gap-3">
        <Confidence pct={pct} />
        <span className={`rounded-[2px] px-1.5 py-0.5 font-mono text-[9px] uppercase ${s.badge}`}>
          {s.label}
        </span>
        {finding.needs_human_review && <HumanReview />}
      </div>
    </button>
  );
}

function Confidence({ pct }) {
  return (
    <span className="flex items-center gap-1.5 font-mono text-[10px] text-stone-500">
      <span className="tabular-nums">{pct}%</span>
      <span className="inline-block h-1 w-12 overflow-hidden rounded-full bg-white/10">
        <span
          className={`block h-full ${pct >= 70 ? "bg-emerald-400/70" : pct >= 50 ? "bg-amber-400/70" : "bg-red-400/70"}`}
          style={{ width: `${pct}%` }}
        />
      </span>
    </span>
  );
}

function HumanReview() {
  return (
    <span className="ml-auto rounded-[2px] border border-amber-400/30 bg-amber-400/10 px-1.5 py-0.5 font-mono text-[9px] uppercase text-amber-300">
      human review
    </span>
  );
}
