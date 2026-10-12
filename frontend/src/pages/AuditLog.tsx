import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AuditEntry } from "../api/types";
import { ErrorBox, Loading, PageHeader, fmtDate } from "../components/ui";

const ACTIONS = ["", "login", "view", "download", "upload", "approve", "edit", "reject", "model_run", "weights_edit", "share", "unshare", "claim_report", "reset", "scenario"];

export function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState("");
  const [username, setUsername] = useState("");

  useEffect(() => {
    const q = new URLSearchParams();
    if (action) q.set("action", action);
    if (username) q.set("username", username);
    api.get<{ entries: AuditEntry[] }>(`/api/audit?${q}`).then((r) => setEntries(r.entries)).catch((e) => setError(e.message));
  }, [action, username]);

  return (
    <div className="p-6">
      <PageHeader title="Audit Log" subtitle="Every sign-in, view, download, approval, share and model run, newest first." />
      <div className="flex gap-3 mb-3">
        <div>
          <label className="label" htmlFor="act">Action</label>
          <select id="act" className="input" value={action} onChange={(e) => setAction(e.target.value)}>
            {ACTIONS.map((a) => <option key={a} value={a}>{a || "All actions"}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="usr">User</label>
          <select id="usr" className="input" value={username} onChange={(e) => setUsername(e.target.value)}>
            {["", "admin", "geologist", "analyst", "investor", "miner"].map((u) => <option key={u} value={u}>{u || "All users"}</option>)}
          </select>
        </div>
      </div>
      <ErrorBox error={error} />
      {!entries ? <Loading /> : (
        <div className="card overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr><th className="th">When</th><th className="th">User</th><th className="th">Action</th><th className="th">Object</th><th className="th">Details</th></tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td className="td whitespace-nowrap text-xs">{fmtDate(e.at)}</td>
                  <td className="td text-xs"><strong>{e.username}</strong> <span className="text-brand/60">({e.role})</span></td>
                  <td className="td text-xs font-semibold">{e.action}</td>
                  <td className="td text-xs">{e.object_type}: {e.object_id}</td>
                  <td className="td text-xs font-mono text-brand/70 break-all">{Object.keys(e.details).length ? JSON.stringify(e.details) : ""}</td>
                </tr>
              ))}
              {entries.length === 0 && <tr><td className="td text-brand/60" colSpan={5}>No entries match.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
