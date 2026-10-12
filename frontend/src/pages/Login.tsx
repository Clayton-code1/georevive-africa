import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { User } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorBox } from "../components/ui";
import { Wordmark } from "../components/Wordmark";

const ROLE_HINTS: Record<string, string> = {
  admin: "Everything, incl. sharing, audit log and demo reset",
  geologist: "Reviews extracted facts, edits model weights",
  analyst: "Data, map, rescue uploads and model runs",
  investor: "Sees only datasets shared in the data room",
  miner: "Claim check reports only",
};

export function Login() {
  const { login, demoLogin, meta } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [demo, setDemo] = useState<{ enabled: boolean; accounts: User[] }>({ enabled: false, accounts: [] });

  useEffect(() => {
    api
      .get<{ enabled: boolean; accounts: User[] }>("/api/auth/demo-accounts")
      .then(setDemo)
      .catch(() => setDemo({ enabled: false, accounts: [] }));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login(username, password);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function quick(u: string) {
    setError(null);
    try {
      await demoLogin(u);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center bg-brand p-6">
      <div className="w-full max-w-3xl grid md:grid-cols-2 gap-0 rounded-xl overflow-hidden shadow-2xl">
        <div className="bg-brand-dark p-8 text-sand flex flex-col">
          <Wordmark />
          <h1 className="mt-8 text-2xl font-bold leading-snug">
            Rescuing Africa&rsquo;s geological records. Ranking targets you can explain.
          </h1>
          <p className="mt-4 text-sm text-sand/75">
            Pilot area: {meta?.pilot_area.name ?? "Harare 1:100 000 sheet"}
          </p>
          <p className="mt-auto pt-8 text-xs text-sand/60">
            Prototype for the timbuktoo MineTech Hub / UNDP Pan-African Mine-Tech Pre-Incubation Programme 2026.
          </p>
        </div>
        <div className="bg-sand p-8">
          <form onSubmit={submit} className="space-y-3">
            <h2 className="text-lg font-bold text-brand">Sign in</h2>
            <div>
              <label className="label" htmlFor="u">Username</label>
              <input id="u" className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
            </div>
            <div>
              <label className="label" htmlFor="p">Password</label>
              <input id="p" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </div>
            <ErrorBox error={error} />
            <button className="btn-primary w-full" disabled={!username || !password}>Sign in</button>
          </form>
          {demo.enabled && demo.accounts.length > 0 && (
            <div className="mt-6">
              <div className="label">Demo accounts (this computer only)</div>
              <div className="grid gap-1.5">
                {demo.accounts.map((a) => (
                  <button key={a.username} onClick={() => quick(a.username)} className="btn-ghost justify-start text-left" title={ROLE_HINTS[a.role]}>
                    <span className="font-semibold w-20">{a.role_label}</span>
                    <span className="text-xs text-brand/60 truncate">{ROLE_HINTS[a.role]}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
