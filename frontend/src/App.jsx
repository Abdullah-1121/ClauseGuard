import { useEffect, useRef, useState } from "react";
import { fetchModels, loadConfig, reviewFile, reviewText, saveConfig } from "./api.js";
import ConfigCard, { DEFAULT_CATALOG } from "./ConfigCard.jsx";
import Landing from "./Landing.jsx";
import Workspace from "./Workspace.jsx";

export default function App() {
  const [view, setView] = useState("text");
  const [text, setText] = useState("");
  const [source, setSource] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [runId, setRunId] = useState(0);
  const [config, setConfig] = useState(loadConfig);
  const [catalog, setCatalog] = useState(DEFAULT_CATALOG);
  const fileRef = useRef(null);

  useEffect(() => {
    // Best-effort: replace the built-in catalog when the backend exposes one.
    // Any failure (offline, older deploy) gracefully falls back to the default.
    fetchModels()
      .then((res) => res.providers && setCatalog(res.providers))
      .catch(() => {});
  }, []);

  function updateConfig(patch) {
    setConfig((prev) => {
      const next = { ...prev, ...patch };
      saveConfig(next);
      return next;
    });
  }

  async function runText() {
    if (!text.trim()) return;
    await run(() => reviewText(text, config), text);
  }

  async function runFile(file) {
    if (!file) return;
    await run(() => reviewFile(file, config), "");
  }

  async function run(call, sourceText) {
    setError("");
    setResult(null);
    setIsLoading(true);
    try {
      const res = await call();
      setResult(res);
      setSource(sourceText);
      setActiveIndex(0);
      setRunId((n) => n + 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-ink text-stone-200">
      <Header />
      {!result || isLoading ? (
        <Landing
          key={runId}
          view={view}
          setView={setView}
          text={text}
          setText={setText}
          fileRef={fileRef}
          onText={runText}
          onFile={runFile}
          isLoading={isLoading}
          error={error}
          config={config}
          onConfigChange={updateConfig}
          catalog={catalog}
        />
      ) : (
        <Workspace
          result={result}
          source={source}
          activeIndex={activeIndex}
          setActiveIndex={setActiveIndex}
          onReset={() => {
            setText("");
            setActiveIndex(0);
            setResult(null);
          }}
        />
      )}
    </div>
  );
}

function Header() {
  return (
    <header className="flex items-center justify-between border-b border-hairline px-6 py-3">
      <div className="flex items-center gap-2.5">
        <div className="flex h-6 w-6 items-center justify-center rounded-[3px] border border-white/15 bg-white/5">
          <span className="font-mono text-[11px] font-bold leading-none text-amber-300">¶</span>
        </div>
        <span className="text-[15px] font-semibold tracking-tight text-white">ClauseGuard</span>
        <span className="ml-1 hidden rounded-[2px] border border-white/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-stone-500 sm:inline">
          v0.1
        </span>
      </div>
      <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-stone-500">
        Contract risk audit
      </span>
    </header>
  );
}
