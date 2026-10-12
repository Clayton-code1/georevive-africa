import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { STEPS } from "./steps";

interface PresenterState {
  on: boolean;
  toggle: () => void;
}
const Ctx = createContext<PresenterState>({ on: false, toggle: () => undefined });
export const usePresenter = () => useContext(Ctx);

const KEY = "georevive.presenter";

function readOn(): boolean {
  try {
    return sessionStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function PresenterProvider({ children }: { children: ReactNode }) {
  const [on, setOn] = useState(readOn);
  useEffect(() => {
    document.documentElement.classList.toggle("presenter", on);
    try {
      sessionStorage.setItem(KEY, on ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [on]);
  return (
    <Ctx.Provider value={{ on, toggle: () => setOn((v) => !v) }}>
      {children}
      {on && <PresenterPanel onClose={() => setOn(false)} />}
    </Ctx.Provider>
  );
}

function isTyping(): boolean {
  const el = document.activeElement as HTMLElement | null;
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable);
}

function PresenterPanel({ onClose }: { onClose: () => void }) {
  const { user, demoLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [i, setI] = useState(() => {
    try {
      return Number(sessionStorage.getItem(`${KEY}.step`) || 0);
    } catch {
      return 0;
    }
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [mini, setMini] = useState(false);
  const step = STEPS[i];

  useEffect(() => {
    try {
      sessionStorage.setItem(`${KEY}.step`, String(i));
    } catch {
      /* ignore */
    }
  }, [i]);

  const go = useCallback(async (n: number) => {
    const s = STEPS[Math.max(0, Math.min(STEPS.length - 1, n))];
    setI(STEPS.indexOf(s));
    setMsg(null);
    try {
      if (user?.role !== s.role) await demoLogin(s.role);
      if (s.path) navigate(s.path);
    } catch (e) {
      setMsg(`Could not switch to the ${s.role} account: ${(e as Error).message}`);
    }
  }, [user, demoLogin, navigate]);

  const control = useCallback(async (what: "reset" | "scenario") => {
    setBusy(what === "reset" ? "Resetting to the clean state…" : "Loading the complete scenario…");
    setMsg(null);
    try {
      if (user?.role !== "admin") await demoLogin("admin");
      await api.post(`/api/demo/${what === "reset" ? "reset" : "scenario"}`);
      setMsg(what === "reset" ? "Reset done - clean state after ingestion." : "Complete scenario loaded.");
      if (what === "reset") {
        await go(0);
      } else {
        navigate(location.pathname + location.search);
        window.location.reload();
      }
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(null);
    }
  }, [user, demoLogin, go, navigate, location]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTyping() || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        go(i + 1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        go(i - 1);
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        if (window.confirm("Reset the demo to the clean state after ingestion?")) control("reset");
      } else if (e.key === "Escape") {
        setMini((m) => !m);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [i, go, control]);

  if (mini) {
    return (
      <button onClick={() => setMini(false)} className="fixed bottom-4 right-4 z-50 btn-accent shadow-lg" title="Show presenter guide (Esc)">
        <Icon name="present" /> Step {i + 1}/{STEPS.length}
      </button>
    );
  }
  return (
    <div className="fixed bottom-4 right-4 z-50 w-[23rem] rounded-xl bg-brand text-sand shadow-2xl border border-ochre/60">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
        <div className="text-xs uppercase tracking-widest text-ochre-light">Presenter · {step.minutes}</div>
        <div className="flex gap-1">
          <button className="text-sand/70 hover:text-white px-1" onClick={() => setMini(true)} title="Minimise (Esc)"><Icon name="chevronRight" size={16} /></button>
          <button className="text-sand/70 hover:text-white px-1" onClick={onClose} title="Exit Presenter Mode"><Icon name="x" size={16} /></button>
        </div>
      </div>
      <div className="px-3 py-2">
        <div className="text-lg font-bold">{step.title}</div>
        <div className="text-[11px] text-sand/60 mb-1">Signed in as: {user?.role_label} {user?.role !== step.role ? `(this step uses ${step.role})` : ""}</div>
        <ul className="text-sm list-disc pl-4 space-y-0.5">{step.do.map((d) => <li key={d}>{d}</li>)}</ul>
        <p className="text-sm italic text-sand/85 mt-2">“{step.say}”</p>
        {busy && <p className="text-xs text-ochre-light mt-2 animate-pulse">{busy}</p>}
        {msg && <p className="text-xs text-ochre-light mt-2">{msg}</p>}
      </div>
      <div className="flex items-center gap-1 px-3 py-2 border-t border-white/10">
        <button className="btn bg-white/10 hover:bg-white/20 text-sand px-2" onClick={() => go(i - 1)} disabled={i === 0} title="Previous (←)"><Icon name="chevronLeft" size={14} /></button>
        <button className="btn bg-ochre hover:bg-ochre-dark text-white flex-1" onClick={() => go(i + 1)} disabled={i === STEPS.length - 1} title="Next (→)">Next step <Icon name="chevronRight" size={14} /></button>
        <button className="btn bg-white/10 hover:bg-white/20 text-sand px-2 text-xs" onClick={() => window.confirm("Reset the demo to the clean state?") && control("reset")} disabled={!!busy} title="Reset demo (R)"><Icon name="reset" size={14} /> R</button>
        <button className="btn bg-white/10 hover:bg-white/20 text-sand px-2 text-xs" onClick={() => control("scenario")} disabled={!!busy} title="Jump to the finished end state">Load complete</button>
      </div>
      <div className="flex gap-1 px-3 pb-2">
        {STEPS.map((s, n) => (
          <button key={s.title} onClick={() => go(n)} title={s.title} className={`h-1.5 flex-1 rounded ${n === i ? "bg-ochre" : n < i ? "bg-sand/60" : "bg-white/15"}`} />
        ))}
      </div>
    </div>
  );
}
