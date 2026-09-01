import { useEffect, useMemo, useRef } from "react";

// The grounded-citations story, made visible:
//   - the ACTIVE finding's cited clause is highlighted while others are subtle,
//     so the reader sees exactly which clause the selected finding refers to.
//   - selecting a finding auto-scrolls the document to that clause.
//   - the "clause map" dots (top) reflect each clause's risk and jump to it.

export default function DocumentPane({ text, findings, activeIndex }) {
  const markRefs = useRef([]);

  const clauses = useMemo(() => buildClauses(text, findings), [text, findings]);

  useEffect(() => {
    const el = markRefs.current[activeIndex];
    if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [activeIndex, text]);

  return (
    <section className="docs-scroll flex min-h-0 flex-col overflow-y-auto bg-ink-900/40">
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-hairline bg-ink-900/95 px-6 py-2.5 backdrop-blur">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500">
          Clause map
        </span>
        <div className="flex items-center gap-1.5">
          {clauses.filter((c) => c.kind === "clause").map((c, i) => (
            <button
              key={c.findIdx}
              onClick={() => markRefs.current[c.findIdx]?.scrollIntoView({ block: "center", behavior: "smooth" })}
              className={`flex items-center gap-1 rounded-[2px] border px-1.5 py-0.5 transition-colors ${
                c.findIdx === activeIndex ? c.badge + " ring-1 ring-white/30" : "border-transparent opacity-70 hover:opacity-100"
              }`}
              title={`Clause ${c.num}: ${c.riskLabel}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
              <span className="font-mono text-[9px] text-stone-400">{c.num}</span>
            </button>
          ))}
          {clauses.length === 0 && (
            <span className="font-mono text-[10px] text-stone-600">no clauses</span>
          )}
        </div>
      </div>

      <div className="flex-1 px-6 py-6">
        {clauses.map((c, i) =>
          c.kind === "filler" ? (
            <p key={i} className="mb-3 whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-stone-600">
              {c.textContent}
            </p>
          ) : (
            <div
              key={i}
              ref={(el) => (c.kind === "clause" ? (markRefs.current[c.findIdx] = el) : null)}
              className={`mb-3 rounded-[4px] border-l-2 py-3 pl-3 pr-2 ${
                c.findIdx === activeIndex ? c.activeCard : "border-l-transparent"
              }`}
            >
              <div className="mb-1 flex items-center gap-2">
                <span className={`font-mono text-[10px] uppercase tracking-wide ${c.text}`}>
                  Clause {c.num}
                </span>
                <span className={`rounded-[2px] border px-1.5 py-0.5 font-mono text-[9px] uppercase ${c.badge}`}>
                  {c.riskLabel}
                </span>
              </div>
              <p className="font-mono text-[13px] leading-relaxed text-stone-300">{c.textContent}</p>
            </div>
          )
        )}
        {clauses.length === 0 && (
          <p className="py-10 text-center font-mono text-xs text-stone-600">
            {text ? "No cited clauses to map." : "Source text available only for pasted input."}
          </p>
        )}
      </div>
    </section>
  );
}

// Group the source text into "clauses" — one per finding citation, in document
// order — so each citation maps to a labelled, jumpable block. Text before the
// first citation / between citations is carried as un-cited filler.
function buildClauses(text, findings) {
  const ranges = findings
    .map((f, idx) => ({ idx, start: f.citation?.start, end: f.citation?.end, finding: f }))
    .filter((r) => Number.isInteger(r.start) && Number.isInteger(r.end))
    .sort((a, b) => a.start - b.start);

  const out = [];
  let cursor = 0;
  let num = 0;
  for (const r of ranges) {
    if (r.start > cursor) {
      const filler = text.slice(cursor, r.start);
      if (filler.trim()) out.push({ kind: "filler", content: filler });
    }
    num += 1;
    out.push({
      kind: "clause",
      num,
      content: text.slice(r.start, r.end),
      findIdx: r.idx,
      finding: r.finding,
      risk: r.finding?.risk_level,
    });
    cursor = Math.max(cursor, r.end);
  }
  if (cursor < text.length) {
    const filler = text.slice(cursor);
    if (filler.trim()) out.push({ kind: "filler", content: filler });
  }

  return out.map((c) => decorate(c));
}

const RISK_STYLE = {
  HIGH: { label: "High", dot: "bg-red-500", text: "text-red-300", badge: "border-red-500/40 bg-red-500/10 text-red-300", card: "bg-red-500/[0.06] border-l-red-500" },
  MEDIUM: { label: "Medium", dot: "bg-amber-400", text: "text-amber-300", badge: "border-amber-400/40 bg-amber-400/10 text-amber-200", card: "bg-amber-400/[0.05] border-l-amber-400" },
  LOW: { label: "Low", dot: "bg-yellow-300", text: "text-yellow-200", badge: "border-yellow-300/30 bg-yellow-300/8 text-yellow-100", card: "bg-yellow-300/[0.04] border-l-yellow-300" },
  NONE: { label: "None", dot: "bg-stone-500", text: "text-stone-400", badge: "border-stone-500/30 bg-stone-500/10 text-stone-300", card: "bg-stone-500/[0.04] border-l-stone-500" },
};

function decorate(c) {
  if (c.kind === "filler") {
    return { ...c, textContent: c.content.trim(), text: "text-stone-500", dot: "bg-stone-700", badge: "", activeCard: "", riskLabel: "" };
  }
  const s = RISK_STYLE[c.risk] || RISK_STYLE.NONE;
  return {
    ...c,
    textContent: c.content.trim(),
    riskLabel: s.label,
    dot: s.dot,
    text: s.text,
    badge: s.badge,
    activeCard: s.card,
  };
}
