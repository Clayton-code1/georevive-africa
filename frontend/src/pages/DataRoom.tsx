import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, authUrl } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { ErrorBox, Loading, PageHeader, StatusBadge, fmtDate } from "../components/ui";
import type { LayerInfo } from "../map/layerStyle";

interface Dataset extends LayerInfo {
  licence_check: { ok: boolean; reason: string };
  shares?: { id: number; username: string; note: string; created_at: string }[];
  formats: string[];
}
interface Activity { at: string; username: string; role: string; action: string; object_id: string; details: Record<string, unknown> }

export function DataRoom() {
  const { can, user } = useAuth();
  const [data, setData] = useState<Dataset[] | null>(null);
  const [users, setUsers] = useState<{ username: string; display_name: string; role: string }[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const admin = can("dataroom.share");

  const load = () => {
    api.get<{ datasets: Dataset[] }>("/api/dataroom/datasets").then((r) => setData(r.datasets)).catch((e) => setError(e.message));
    if (admin) {
      api.get<{ users: typeof users }>("/api/dataroom/users").then((r) => setUsers(r.users)).catch(() => undefined);
      api.get<{ entries: Activity[] }>("/api/dataroom/activity").then((r) => setActivity(r.entries)).catch(() => undefined);
    }
  };
  useEffect(load, [admin]);

  async function share(layerId: string, username: string, ack: boolean) {
    setError(null);
    try {
      await api.post("/api/dataroom/shares", { layer_id: layerId, username, acknowledge_licence: ack });
      setMsg(`Shared with ${username}.`);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function unshare(id: number) {
    await api.del(`/api/dataroom/shares/${id}`).catch((e) => setError(e.message));
    load();
  }

  if (error && !data) return <div className="p-6"><ErrorBox error={error} /></div>;
  if (!data) return <Loading />;
  const investors = users.filter((u) => u.role === "investor");

  return (
    <div className="p-6">
      <PageHeader
        title="Secure Data Room"
        subtitle={admin
          ? "Share selected datasets with named investors or explorers. Every view and download is logged, and every download is watermarked with the user and time."
          : `Datasets shared with ${user?.organisation || "you"}. Downloads are watermarked with your name and the time, and logged.`}
        actions={admin ? <Link to="/audit" className="btn-ghost"><Icon name="list" size={14} /> Full audit log</Link> : undefined}
      />
      <ErrorBox error={error} />
      {msg && <div className="text-sm text-emerald-700 mb-2">{msg}</div>}
      {data.length === 0 && <div className="card p-4 text-sm text-brand/70">No datasets have been shared with you yet. Please contact the GeoRevive team.</div>}
      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead><tr><th className="th">Dataset</th><th className="th">Source & licence</th><th className="th">Download (watermarked)</th>{admin && <th className="th">Shared with</th>}</tr></thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.id} className="align-top">
                <td className="td">
                  <div className="font-semibold text-brand">{d.name}</div>
                  <div className="text-[11px] text-brand/60">{d.description}</div>
                  <Link to={`/map?layer=${d.id}`} className="text-[11px] text-ochre-dark hover:underline">View on map</Link>
                </td>
                <td className="td text-xs max-w-xs">
                  <div>{d.source.name}</div>
                  <div className="text-brand/60">{d.source.licence}</div>
                  <StatusBadge status={d.source_status} />
                  {admin && <div className={`mt-1 ${d.licence_check.ok ? "text-emerald-700" : "text-amber-700"}`}>{d.licence_check.reason}</div>}
                </td>
                <td className="td text-xs">
                  <div className="flex flex-wrap gap-1">
                    {d.formats.map((f) => (
                      <a key={f} className="btn-ghost py-0.5 px-2 text-xs" href={authUrl(`/api/dataroom/datasets/${d.id}/download?format=${f}`)}>
                        <Icon name="download" size={12} /> {f.toUpperCase()}
                      </a>
                    ))}
                  </div>
                </td>
                {admin && (
                  <td className="td text-xs">
                    {(d.shares || []).map((s) => (
                      <div key={s.id} className="flex items-center gap-1">
                        <span>{s.username}</span>
                        <button className="text-red-700 hover:underline" onClick={() => unshare(s.id)} title="Stop sharing">remove</button>
                      </div>
                    ))}
                    <select className="input py-0.5 text-xs mt-1" value="" onChange={(e) => {
                      const u = e.target.value;
                      if (!u) return;
                      if (!d.licence_check.ok && !window.confirm(`${d.licence_check.reason}\n\nLicence: ${d.source.licence}\n\nShare anyway? (This is logged.)`)) return;
                      share(d.id, u, !d.licence_check.ok);
                    }}>
                      <option value="">Share with…</option>
                      {investors.filter((u) => !(d.shares || []).some((s) => s.username === u.username)).map((u) => (
                        <option key={u.username} value={u.username}>{u.display_name} ({u.username})</option>
                      ))}
                    </select>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {admin && (
        <div className="mt-6">
          <h2 className="font-semibold text-brand mb-2">Recent data-room activity</h2>
          <div className="card overflow-x-auto">
            <table className="w-full">
              <thead><tr><th className="th">When</th><th className="th">Who</th><th className="th">Action</th><th className="th">Dataset</th></tr></thead>
              <tbody>
                {activity.slice(0, 15).map((a, i) => (
                  <tr key={i}><td className="td text-xs whitespace-nowrap">{fmtDate(a.at)}</td><td className="td text-xs">{a.username} ({a.role})</td>
                    <td className="td text-xs font-semibold">{a.action}{a.details.format ? ` (${String(a.details.format)})` : ""}{a.details.with ? ` → ${String(a.details.with)}` : ""}</td><td className="td text-xs">{a.object_id}</td></tr>
                ))}
                {activity.length === 0 && <tr><td className="td text-xs text-brand/60" colSpan={4}>No activity yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
