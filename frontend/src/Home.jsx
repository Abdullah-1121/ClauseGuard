// SaaS-style marketing landing for ClauseGuard. It sells the ONE idea that
// makes the product defensible: a probabilistic LLM judge confined inside a
// deterministic, tested, measured system. All sections are static; the only
// interactive element is the CTA into the review tool.

const STAGES = [
  {
    n: "01",
    title: "Segment",
    body: "A deterministic splitter cuts the contract at blank-line boundaries and records the exact character offset of every clause.",
  },
  {
    n: "02",
    title: "Classify",
    body: "A cheap model assigns one of twelve categories — batched up to eight clauses per request to cut API calls ~15x.",
  },
  {
    n: "03",
    title: "Match rule",
    body: "Each category is mapped to the buyer-side playbook rule: its risk weight and the redline you actually want.",
  },
  {
    n: "04",
    title: "Evaluate",
    body: "A stronger model judges status, risk level, rationale, and a suggested redline — higher stakes, stronger model.",
  },
  {
    n: "05",
    title: "Guard",
    body: "Every citation is re-verified against the source offsets. Low-confidence findings escalate to a human instead of overclaiming.",
  },
  {
    n: "06",
    title: "Rank",
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
  { metric: "LLM vs rules agreement", detection: "—", full: "0.722" },
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
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-stone-600">
          Review assistance — not legal advice · MIT licensed
        </p>
      </footer>
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
          <div className="flex h-6 w-6 items-center justify-center rounded-[3px] border border-white/15 bg-white/5">
            <span className="font-mono text-[11px] font-bold leading-none text-amber-300">
              ¶
            </span>
          </div>
          <span className="text-[15px] font-semibold tracking-tight text-white">
            ClauseGuard
          </span>
        </div>
        <nav className="hidden items-center gap-6 md:flex">
          <NavLink onClick={() => go("how")}>How it works</NavLink>
          <NavLink onClick={() => go("rigor")}>The engineering</NavLink>
          <NavLink onClick={() => go("numbers")}>Results</NavLink>
          <button
            onClick={onStart}
            className="rounded-[4px] bg-amber-400 px-3.5 py-1.5 text-xs font-semibold text-amber-950 transition-colors hover:bg-amber-300"
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
      className="text-xs font-medium text-stone-400 transition-colors hover:text-white"
    >
      {children}
    </button>
  );
}

function Hero({ onStart }) {
  return (
    <section className="border-b border-hairline px-6 pb-16 pt-20">
      <div className="mx-auto max-w-3xl text-center">
        <p className="mx-auto mb-6 w-fit rounded-full border border-hairline bg-ink-800 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-stone-400">
          AI contract risk audit · built on evals, not vibes
        </p>
        <h1 className="text-4xl font-semibold leading-tight tracking-tight text-white sm:text-5xl">
          The AI reviewer that can only cite
          <span className="text-amber-300"> what it actually read</span>
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-sm leading-relaxed text-stone-400 sm:text-base">
          ClauseGuard turns a contract into ranked, citation-grounded risk
          findings — a probabilistic LLM confined inside a deterministic system
          that is measured, not hoped about.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={onStart}
            className="rounded-[4px] bg-amber-400 px-6 py-3 text-sm font-semibold text-amber-950 transition-colors hover:bg-amber-300"
          >
            Audit your first contract
          </button>
          <button
            onClick={() =>
              document.getElementById("how")?.scrollIntoView({ behavior: "smooth" })
            }
            className="rounded-[4px] border border-white/15 px-6 py-3 text-sm font-medium text-stone-300 transition-colors hover:border-white/30 hover:text-white"
          >
            See how it works
          </button>
        </div>
        <div className="mx-auto mt-12 grid max-w-2xl grid-cols-1 gap-2 sm:grid-cols-3">
          {[
            "Grounded by construction",
            "Scored on 2,387 real labels",
            "Bring your own key, zero lock-in",
          ].map((t) => (
            <div
              key={t}
              className="rounded-[4px] border border-hairline bg-ink-800 px-3 py-2.5 text-center font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500"
            >
              {t}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Problem() {
  return (
    <section className="border-b border-hairline px-6 py-16">
      <div className="mx-auto max-w-3xl">
        <SectionLabel>Why this exists</SectionLabel>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          Not another chat box.
        </h2>
        <div className="mt-4 space-y-4 text-sm leading-relaxed text-stone-400 sm:text-base">
          <p>
            Most "AI contract review" is a prompt, a prayer, and a confident
            paragraph of blobs. The model writes what it thinks the document
            says — and there is nothing between its imagination and your legal
            team.
          </p>
          <p>
            ClauseGuard is engineered the other way around. The model is one
            component inside a pipeline whose boundaries are <em>deterministic
            and tested</em>: the segmenter decides what counts as a clause, the
            playbook decides what risk means, the guardrail decides what may be
            shown to you. The LLM's only job is to judge content. Everything
            that can be verified, is.
          </p>
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section id="how" className="border-b border-hairline px-6 py-16">
      <div className="mx-auto max-w-5xl">
        <SectionLabel>How it works</SectionLabel>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          Six deterministic seams, one probabilistic judge
        </h2>
        <div className="mt-8 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {STAGES.map((s) => (
            <div key={s.n} className="rounded-[4px] border border-hairline bg-ink-900 p-4">
              <div className="flex items-center gap-3">
                <span className="font-mono text-lg font-semibold text-amber-300/80">
                  {s.n}
                </span>
                <span className="text-sm font-semibold text-white">{s.title}</span>
              </div>
              <p className="mt-2.5 text-xs leading-relaxed text-stone-500">{s.body}</p>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center font-mono text-[11px] tracking-wide text-stone-600">
          LLM judges content · determinism owns everything else
        </p>
      </div>
    </section>
  );
}

function Reliability() {
  return (
    <section id="rigor" className="border-b border-hairline px-6 py-16">
      <div className="mx-auto max-w-5xl">
        <SectionLabel>The reliability engineering</SectionLabel>
        <h2 className="mt-3 max-w-2xl text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          The part a demo never shows you
        </h2>
        <div className="mt-8 grid grid-cols-1 gap-2 lg:grid-cols-3">
          {RIGOR.map((r) => (
            <div key={r.title} className="rounded-[4px] border border-hairline bg-ink-900 p-5">
              <p className="text-sm font-semibold text-white">{r.title}</p>
              <p className="mt-2 text-xs leading-relaxed text-stone-500">{r.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Results() {
  return (
    <section id="numbers" className="border-b border-hairline px-6 py-16">
      <div className="mx-auto max-w-3xl">
        <SectionLabel>Real numbers</SectionLabel>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          Scored against humans, not another model
        </h2>
        <div className="mt-8 overflow-hidden rounded-[4px] border border-hairline">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-hairline bg-ink-800 font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500">
                <th className="px-4 py-2.5 font-medium">Metric</th>
                <th className="px-4 py-2.5 font-medium">Detection-only</th>
                <th className="px-4 py-2.5 font-medium">Full eval</th>
              </tr>
            </thead>
            <tbody>
              {NUMBERS.map((n) => (
                <tr key={n.metric} className="border-b border-hairline last:border-0">
                  <td className="px-4 py-2.5 text-stone-300">{n.metric}</td>
                  <td className="px-4 py-2.5 font-mono text-stone-400">{n.detection}</td>
                  <td className="px-4 py-2.5 font-mono text-amber-300">{n.full}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs leading-relaxed text-stone-600">
          Directional, not a benchmark — the free-tier quota caps runs to a few
          contracts a day. Read them honestly: recall on diverse legal prose is
          the hard, unsolved part; the 72% rule-vs-LLM agreement is the signal
          we trust. Everything else in the repo is reproducible with one command.
        </p>
      </div>
    </section>
  );
}

function BringYourOwnKey() {
  return (
    <section className="border-b border-hairline px-6 py-16">
      <div className="mx-auto max-w-3xl">
        <SectionLabel>The product</SectionLabel>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          Your key. Your model. Your quota.
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-stone-400 sm:text-base">
          No account, no credit card, no lock-in. Bring any Groq or OpenRouter
          key, pick a model from the menu, and the review runs on{" "}
          <em>your</em> wallet — the server never sees or stores your key
          beyond the single request, and your runs can't touch the demo's
          quota. Open-source, MIT licensed, deployable anywhere.
        </p>
        <div className="mt-6 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-stone-500">
          {["FastAPI", "Pydantic AI", "SQLite", "Groq", "OpenRouter"].map((t) => (
            <span key={t} className="rounded-[3px] border border-hairline bg-ink-800 px-2 py-1">
              {t}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCta({ onStart }) {
  return (
    <section className="px-6 py-20 text-center">
      <div className="mx-auto max-w-xl">
        <h2 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          Paste a contract. Watch it get eviscerated.
        </h2>
        <p className="mt-3 text-sm text-stone-400">
          Two minutes, one free key, one honest review.
        </p>
        <button
          onClick={onStart}
          className="mt-7 rounded-[4px] bg-amber-400 px-7 py-3 text-sm font-semibold text-amber-950 transition-colors hover:bg-amber-300"
        >
          Open the review tool
        </button>
      </div>
    </section>
  );
}

function SectionLabel({ children }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-amber-300/70">
      {children}
    </p>
  );
}