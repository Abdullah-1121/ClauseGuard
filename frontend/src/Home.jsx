// SaaS-style marketing landing for ClauseGuard. It sells the ONE idea that
// makes the product defensible: a probabilistic LLM judge confined inside a
// deterministic, tested, measured system.
//
// Art direction (design skill): Minimalist + Bold Typography — one focal
// element per section, whitespace dominant, a single accent used only for
// risk/determinism. Motion is a restrained 8px rise on scroll.

import { useEffect, useRef, useState } from "react";

const STAGES = [
  {
    n: "01",
    title: "Segment",
    deterministic: true,
    body: "A deterministic splitter cuts the contract at blank-line boundaries and records the exact character offset of every clause — the LLM never sees raw location.",
  },
  {
    n: "02",
    title: "Classify",
    deterministic: false,
    body: "A cheap model assigns one of twelve categories — batched up to eight clauses per request to cut API calls ~15x.",
  },
  {
    n: "03",
    title: "Match rule",
    deterministic: false,
    body: "Each category is mapped to the buyer-side playbook rule: its risk weight and the redline you actually want.",
  },
  {
    n: "04",
    title: "Evaluate",
    deterministic: false,
    body: "A stronger model judges status, risk level, rationale, and a suggested redline — higher stakes, stronger model.",
  },
  {
    n: "05",
    title: "Guard",
    deterministic: true,
    body: "Every citation is re-verified against the source offsets. Low-confidence findings escalate to a human instead of overclaiming.",
  },
  {
    n: "06",
    title: "Rank",
    deterministic: false,
    body: "Findings are sorted by risk, then confidence. You get a triage stack, not a dump.",
  },
];

const RIGOR = [
  {
    title: "Citations that cannot be faked",
    body: "The LLM judges clauses — it never locates them. Citations come from the segmenter's character offsets and are re-verified against the source before they are emitted. A hallucinated quote is structurally impossible, then double-checked.",
  },
  {
    title: "Confidence is a gate, not a guess",
    body: "When the model is unsure, the finding is flagged for human review rather than presented as fact. Prefer an explicit 'I don't know' over a confident error.",
  },
  {
    title: "Evals over vibes",
    body: "Detection accuracy is scored against 2,387 human-labeled CUAD clauses — deterministically, never by asking another LLM whether the answer looks right.",
  },
];

const NUMBERS = [
  { metric: "Precision", detection: "0.714", full: "0.667" },
  { metric: "Recall", detection: "0.385", full: "0.462" },
  { metric: "F1", detection: "0.500", full: "0.545" },
  { metric: "Risk accuracy", detection: "—", full: "0.333" },
  { metric: "LLM vs rules agreement", detection: "—", full: "0.722", highlight: true },
];

export default function Home({ onStart }) {
  return (
    <div className="docs-scroll min-h-0 flex-1 overflow-y-auto">
      <SiteHeader onStart={onStart} />
      <Hero onStart={onStart} />
      <Problem />
      <HowItWorks />
      <Reliability />
      <Results />
      <BringYourOwnKey />
      <FinalCta onStart={onStart} />
      <footer className="border-t border-hairline px-6 py-6 text-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-stone-500">
          Review assistance — not legal advice · MIT licensed
        </p>
      </footer>
    </div>
  );
}

// One-shot intersection observation for scroll-reveal. Elements fade up once
// and the observer disconnects — no re-triggering, no drift.
function useInView(threshold = 0.12) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return undefined;
    }
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          obs.disconnect();
        }
      },
      { threshold },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return [ref, inView];
}

function Reveal({ children, delay = 0, className = "" }) {
  const [ref, inView] = useInView();
  return (
    <div
      ref={ref}
      className={`reveal ${className} ${inView ? "visible" : ""}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}

function SiteHeader({ onStart }) {
  const go = (id) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  return (
    <header className="sticky top-0 z-10 border-b border-hairline bg-ink/95 px-6 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-6 w-6 items-center justify-center rounded-[3px] border border-black/15 bg-black/5">
            <span className="font-mono text-[11px] font-bold leading-none text-amber-600">
              ¶
            </span>
          </div>
          <span className="text-[15px] font-semibold tracking-tight text-stone-900">
            ClauseGuard
          </span>
        </div>
        <nav className="hidden items-center gap-6 md:flex">
          <NavLink onClick={() => go("how")}>How it works</NavLink>
          <NavLink onClick={() => go("rigor")}>The engineering</NavLink>
          <NavLink onClick={() => go("numbers")}>Results</NavLink>
          <button
            onClick={onStart}
            className="rounded-[4px] bg-amber-400 px-3.5 py-1.5 text-xs font-semibold text-amber-950 transition-colors hover:bg-amber-500"
          >
            Run an audit
          </button>
        </nav>
      </div>
    </header>
  );
}

function NavLink({ onClick, children }) {
  return (
    <button
      onClick={onClick}
      className="text-xs font-medium text-stone-600 transition-colors hover:text-stone-900"
    >
      {children}
    </button>
  );
}

function Hero({ onStart }) {
  return (
    <section className="border-b border-hairline px-6 pb-20 pt-20">
      <div className="mx-auto max-w-3xl text-center">
        <p className="mx-auto mb-6 w-fit rounded-full border border-hairline bg-ink-800 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-stone-500">
          AI contract risk audit · built on evals, not vibes
        </p>
        <h1 className="text-[44px] font-semibold leading-[1.08] tracking-tight text-stone-900 sm:text-6xl">
          The AI reviewer that can only cite{" "}
          <span className="text-amber-600">what it actually read</span>
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-stone-500">
          ClauseGuard turns a contract into ranked, citation-grounded risk
          findings — a probabilistic LLM confined inside a deterministic system
          that is measured, not hoped about.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={onStart}
            className="rounded-[4px] bg-amber-400 px-7 py-3.5 text-sm font-semibold text-amber-950 transition-colors hover:bg-amber-500"
          >
            Audit your first contract
          </button>
          <button
            onClick={() =>
              document.getElementById("how")?.scrollIntoView({ behavior: "smooth" })
            }
            className="rounded-[4px] border border-black/15 px-7 py-3.5 text-sm font-medium text-stone-700 transition-colors hover:border-black/30 hover:text-stone-900"
          >
            See how it works
          </button>
        </div>

        <Reveal delay={120}>
          <PipelineDiagram className="mt-16" />
        </Reveal>
      </div>
    </section>
  );
}

// The hero's focal element: the pipeline rendered as machined instrument cards.
// The two deterministic seams carry the accent — the whole thesis in one frame.
function PipelineDiagram({ className = "" }) {
  return (
    <div className={`machined mx-auto w-full max-w-4xl rounded-[4px] border border-hairline bg-ink-900 ${className}`}>
      <div className="flex items-center justify-between border-b border-hairline px-4 py-2.5 font-mono text-[10px] uppercase tracking-[0.16em] text-stone-500">
        <span>The pipeline · one pass, six seams</span>
        <span className="hidden items-center gap-1.5 sm:flex">
          <span className="h-1 w-1 rounded-full bg-amber-400" />
          deterministic seams
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 p-4 sm:grid-cols-3 lg:grid-cols-6">
        {STAGES.map((s) => (
          <div
            key={s.n}
            className={`rounded-[4px] border px-3 py-2.5 text-left ${
              s.deterministic
                ? "border-amber-500/40 bg-amber-500/[0.07] machined"
                : "border-hairline bg-ink-800"
            }`}
          >
            <span
              className={`font-mono text-[12px] font-semibold ${
                s.deterministic ? "text-amber-700" : "text-stone-500"
              }`}
            >
              {s.n}
            </span>
            <p className="mt-1 text-[12px] font-semibold text-stone-900">{s.title}</p>
          </div>
        ))}
      </div>
      <p className="border-t border-hairline px-4 py-2 text-center font-mono text-[10px] uppercase tracking-[0.16em] text-stone-500">
        two seams are deterministic · four are an LLM call · the output is a triage
      </p>
    </div>
  );
}

function Problem() {
  return (
    <section className="border-b border-hairline px-6 py-24">
      <Reveal>
        <div className="mx-auto max-w-3xl">
          <SectionLabel>Why this exists</SectionLabel>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-stone-900">
            Not another chat box.
          </h2>
          <p className="mt-5 text-base leading-relaxed text-stone-500">
            Most "AI contract review" is a prompt, a prayer, and a confident
            paragraph of blobs — nothing between the model's imagination and
            your legal team. ClauseGuard is engineered the other way around:
            the model is one component inside a pipeline whose boundaries are
            deterministic and tested.
          </p>
          <p className="mt-6 border-l-2 border-amber-400/50 pl-4 font-mono text-[12px] uppercase tracking-[0.16em] text-stone-500">
            the LLM judges content · determinism owns everything else
          </p>
        </div>
      </Reveal>
    </section>
  );
}

function HowItWorks() {
  return (
    <section id="how" className="border-b border-hairline px-6 py-24">
      <Reveal>
        <div className="mx-auto max-w-5xl">
          <SectionLabel>How it works</SectionLabel>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-stone-900">
            Six deterministic seams, one probabilistic judge
          </h2>
          <div className="mt-10 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            {STAGES.map((s, i) => (
              <div
                key={s.n}
                className="machined rounded-[4px] border border-hairline bg-ink-900 p-5"
                style={{ transitionDelay: `${i * 40}ms` }}
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-lg font-semibold text-stone-500">
                    {s.n}
                  </span>
                  <span className="text-sm font-semibold text-stone-900">{s.title}</span>
                  {s.deterministic && (
                    <span className="ml-auto rounded-[2px] border border-amber-500/40 bg-amber-500/[0.08] px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wide text-amber-800">
                      deterministic
                    </span>
                  )}
                </div>
                <p className="mt-3 text-[13px] leading-relaxed text-stone-500">
                  {s.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </Reveal>
    </section>
  );
}

function Reliability() {
  return (
    <section id="rigor" className="border-b border-hairline px-6 py-24">
      <Reveal>
        <div className="mx-auto max-w-5xl">
          <SectionLabel>The reliability engineering</SectionLabel>
          <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight text-stone-900">
            The part a demo never shows you
          </h2>
          <div className="mt-10 grid grid-cols-1 gap-2.5 lg:grid-cols-3">
            {RIGOR.map((r) => (
              <div key={r.title} className="machined rounded-[4px] border border-hairline bg-ink-900 p-6">
                <p className="text-sm font-semibold text-stone-900">{r.title}</p>
                <p className="mt-2.5 text-[13px] leading-relaxed text-stone-500">{r.body}</p>
              </div>
            ))}
          </div>
        </div>
      </Reveal>
    </section>
  );
}

function Results() {
  return (
    <section id="numbers" className="border-b border-hairline px-6 py-24">
      <Reveal>
        <div className="mx-auto max-w-3xl">
          <SectionLabel>Real numbers</SectionLabel>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-stone-900">
            Scored against humans, not another model
          </h2>
          <div className="machined mt-10 overflow-hidden rounded-[4px] border border-hairline bg-ink-900">
            <div className="flex items-center justify-between border-b border-hairline bg-ink-800 px-4 py-2.5 font-mono text-[10px] uppercase tracking-[0.16em] text-stone-500">
              <span>Metric</span>
              <span className="flex gap-6">
                <span className="w-16 text-right">Detection</span>
                <span className="w-16 text-right">Full eval</span>
              </span>
            </div>
            {NUMBERS.map((n) => (
              <div
                key={n.metric}
                className={`flex items-center justify-between gap-3 px-4 py-3 ${
                  n.highlight ? "bg-amber-500/[0.08]" : ""
                }`}
              >
                <span className={`text-sm ${n.highlight ? "font-medium text-amber-800" : "text-stone-700"}`}>
                  {n.metric}
                </span>
                <span className="flex items-center gap-6 font-mono text-sm">
                  <span className="w-16 text-right text-stone-500">{n.detection}</span>
                  <span className={`w-16 text-right ${n.highlight ? "font-semibold text-amber-700" : "text-stone-700"}`}>
                    {n.full}
                  </span>
                </span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-[13px] leading-relaxed text-stone-500">
            Directional, not a benchmark — the free-tier quota caps runs to a
            few contracts a day. Read them honestly: recall on diverse legal
            prose is the hard, unsolved part; the 72% rule-vs-LLM agreement is
            the signal we trust.
          </p>
        </div>
      </Reveal>
    </section>
  );
}

function BringYourOwnKey() {
  return (
    <section className="border-b border-hairline px-6 py-24">
      <Reveal>
        <div className="mx-auto max-w-3xl">
          <SectionLabel>The product</SectionLabel>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-stone-900">
            Your key. Your model. Your quota.
          </h2>
          <p className="mt-5 text-base leading-relaxed text-stone-500">
            No account, no credit card, no lock-in. Bring any Groq or OpenRouter
            key, pick a model from the menu, and the review runs on{" "}
            <em>your</em> wallet — the server never sees your key past the
            single request, and your runs can't touch the demo's quota.
          </p>
          <div className="mt-6 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500">
            {["FastAPI", "Pydantic AI", "SQLite", "Groq", "OpenRouter"].map((t) => (
              <span key={t} className="rounded-[3px] border border-hairline bg-ink-800 px-2 py-1">
                {t}
              </span>
            ))}
          </div>
        </div>
      </Reveal>
    </section>
  );
}

function FinalCta({ onStart }) {
  return (
    <section className="px-6 py-24 text-center">
      <Reveal>
        <div className="mx-auto max-w-xl">
          <h2 className="text-3xl font-semibold tracking-tight text-stone-900">
            Paste a contract. Watch it get eviscerated.
          </h2>
          <p className="mt-3 text-sm text-stone-600">
            Two minutes, one free key, one honest review.
          </p>
          <button
            onClick={onStart}
            className="mt-8 rounded-[4px] bg-amber-400 px-8 py-3.5 text-sm font-semibold text-amber-950 transition-colors hover:bg-amber-500"
          >
            Open the review tool
          </button>
        </div>
      </Reveal>
    </section>
  );
}

function SectionLabel({ children }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-stone-500">
      {children}
    </p>
  );
}