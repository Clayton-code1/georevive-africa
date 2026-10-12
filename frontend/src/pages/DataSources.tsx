import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, authUrl } from "../api/client";
import type { Source } from "../api/types";
import { Icon } from "../components/Icon";
import { ErrorBox, Loading, PageHeader, STATUS_STYLES, Stat, StatusBadge, fmtBytes, fmtDate } from "../components/ui";
import { NAV } from "../nav";

const MAP_ENABLED = NAV.some((n) => n.path === "/map");

function size(s: Source): string {
  if (s.record_count != null && s.raster_size) return `${s.record_count.toLocaleString()} records · ${s.raster_size}`;
  if (s.record_count != null) return `${s.record_count.toLocaleString()} records`;
  if (s.raster_size) return s.raster_size;
  return "—";
}

export function DataSources() {
  const [data, setData] = useState<{ sources: Source[]; status_counts: Record<string, number> } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ sources: Source[]; status_counts: Record<string, number> }>("/api/sources").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-6"><ErrorBox error={error} /></div>;
  if (!data) return <Loading />;

  const c = data.status_counts;
  return (
    <div className="p-6">
      <PageHeader
        title="Data Sources"
        subtitle="The Source Registry: every dataset GeoRevive uses, where it came from, its licence, when we accessed it and what still needs action. Nothing is invented: failed sources stay failed."
        actions={
          <a className="btn-ghost" href={authUrl("/api/sources/report/markdown")} target="_blank" rel="noreferrer" title="Open the generated Data Report">
            <Icon name="report" size={16} /> Data report
          </a>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
        <Stat label="Downloaded" value={c.downloaded ?? 0} hint={STATUS_STYLES.downloaded.help} />
        <Stat label="Partial" value={c.partial ?? 0} hint={STATUS_STYLES.partial.help} />
        <Stat label="Failed" value={c.failed ?? 0} hint={STATUS_STYLES.failed.help} />
        <Stat label="Manual request" value={c.needs_manual_request ?? 0} hint={STATUS_STYLES.needs_manual_request.help} />
        <Stat label="Credentials" value={c.needs_credentials ?? 0} hint={STATUS_STYLES.needs_credentials.help} />
      </div>

      {data.sources.length === 0 ? (
        <div className="card p-6 text-sm text-brand/80">
          No sources have been ingested yet. Run <code className="bg-sand px-1">python -m georevive.ingest --all</code>{" "}
          (see README, step 4).
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="th">Dataset</th>
                <th className="th">Status</th>
                <th className="th">Licence</th>
                <th className="th">Accessed</th>
                <th className="th">Size</th>
                <th className="th">Layers</th>
              </tr>
            </thead>
            <tbody>
              {data.sources.map((s) => (
                <Fragment key={s.id}>
                  <tr className="hover:bg-sand/60 cursor-pointer" onClick={() => setOpen(open === s.id ? null : s.id)}>
                    <td className="td">
                      <div className="font-semibold text-brand">{s.name}</div>
                      <div className="text-xs text-brand/60">{s.publisher}</div>
                    </td>
                    <td className="td"><StatusBadge status={s.status} /></td>
                    <td className="td text-xs max-w-[14rem]">
                      <span className={s.licence.includes("to confirm") ? "text-amber-700 font-semibold" : ""}>{s.licence}</span>
                    </td>
                    <td className="td text-xs whitespace-nowrap">{fmtDate(s.accessed_at)}</td>
                    <td className="td text-xs">{size(s)}</td>
                    <td className="td text-xs" onClick={(e) => e.stopPropagation()}>
                      {s.layers.length === 0 && <span className="text-brand/40">—</span>}
                      {s.layers.map((l) =>
                        MAP_ENABLED ? (
                          <Link key={l.id} to={`/map?layer=${l.id}`} className="block text-ochre-dark hover:underline whitespace-nowrap">
                            View on map: {l.name}
                          </Link>
                        ) : (
                          <div key={l.id}>{l.name}</div>
                        ),
                      )}
                    </td>
                  </tr>
                  {open === s.id && (
                    <tr>
                      <td colSpan={6} className="td bg-sand/50">
                        <SourceDetail s={s} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-brand/60 mt-2">Click a row to see files, checksums, URLs tried and how to obtain missing data.</p>
    </div>
  );
}

function SourceDetail({ s }: { s: Source }) {
  return (
    <div className="grid md:grid-cols-2 gap-4 text-sm">
      <div className="space-y-2">
        <div><span className="label">What it is / how we use it</span>{s.note} {s.usage && <em className="block text-brand/70">{s.usage}</em>}</div>
        <div>
          <span className="label">Source URL</span>
          <a href={s.url} target="_blank" rel="noreferrer" className="text-ochre-dark hover:underline break-all">{s.url}</a>
        </div>
        {s.attribution && <div><span className="label">Attribution</span>{s.attribution}</div>}
        {s.bbox && <div><span className="label">Coverage (lon/lat)</span>{s.bbox.map((v) => v.toFixed(3)).join(", ")}</div>}
        {s.error && <div><span className="label">What failed and why</span><span className="text-red-800">{s.error}</span></div>}
        {s.how_to_obtain && <div><span className="label">How to obtain</span><span className="whitespace-pre-line">{s.how_to_obtain}</span></div>}
      </div>
      <div className="space-y-2">
        {s.urls_tried.length > 0 && (
          <div>
            <span className="label">URLs tried</span>
            <ul className="text-xs space-y-1">
              {s.urls_tried.map((u, i) => (
                <li key={i} className="break-all"><span className="font-mono">{u.url}</span> → {u.result}</li>
              ))}
            </ul>
          </div>
        )}
        <div>
          <span className="label">Files (SHA-256)</span>
          {s.files.length === 0 ? (
            <span className="text-brand/50 text-xs">No files downloaded.</span>
          ) : (
            <ul className="text-xs space-y-1">
              {s.files.map((f) => (
                <li key={f.path} className="break-all">
                  <span className="font-mono">{f.path}</span> ({fmtBytes(f.bytes)})<br />
                  <span className="font-mono text-brand/50">{f.sha256}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
