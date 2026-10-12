import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, authUrl } from "../api/client";
import type { DocumentInfo, Sample } from "../api/rescueTypes";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { ErrorBox, Loading, PageHeader, StatusBadge, fmtDate } from "../components/ui";

export function Rescue() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const [docs, setDocs] = useState<DocumentInfo[] | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    api.get<{ documents: DocumentInfo[] }>("/api/rescue/documents").then((r) => setDocs(r.documents)).catch((e) => setError(e.message));
    api.get<{ samples: Sample[] }>("/api/rescue/samples").then((r) => setSamples(r.samples)).catch(() => setSamples([]));
  };
  useEffect(load, []);

  async function loadSample(id: string) {
    setBusy(`Enhancing and reading sample page…`);
    setError(null);
    try {
      const d = await api.post<DocumentInfo>(`/api/rescue/samples/${id}/load`);
      navigate(`/rescue/${d.id}?page=1`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="p-6">
      <PageHeader
        title="Data Rescue"
        subtitle="Upload a scanned page from a historical bulletin, map or report. GeoRevive cleans the scan, reads it, and extracts geological facts for the geologist to review. Every fact links back to its place on the page."
      />
      <ErrorBox error={error} />
      {busy && <div className="card p-3 mb-3 text-sm text-brand animate-pulse">{busy} (usually 5-20 seconds)</div>}

      <div className="grid lg:grid-cols-2 gap-4 mb-6">
        {can("rescue.upload") && <UploadForm onDone={(id) => navigate(`/rescue/${id}?page=1`)} setBusy={setBusy} setError={setError} />}
        <div className="card p-4">
          <h2 className="font-semibold text-brand mb-1">Open sample pages</h2>
          <p className="text-xs text-brand/70 mb-3">
            Single pages from openly licensed historical documents already recorded in the Source Registry.
          </p>
          {samples.length === 0 && <p className="text-sm text-brand/60">No sample pages prepared yet (run <code>python -m georevive.rescue.samples</code> after ingestion).</p>}
          <div className="space-y-2">
            {samples.map((s) => (
              <div key={s.id} className="flex items-center gap-3 border border-sand-line rounded-md p-2">
                <img src={authUrl(`/api/rescue/samples/${s.id}/file`)} alt="" className="w-12 h-16 object-cover rounded border border-sand-line bg-sand" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-brand truncate" title={s.title}>{s.title}</div>
                  <div className="text-[11px] text-brand/60 truncate">{s.source_name} · page {s.page} · {s.licence}</div>
                </div>
                <div className="flex flex-col gap-1">
                  {can("rescue.upload") && (
                    <button className="btn-accent" disabled={!!busy} onClick={() => loadSample(s.id)}>Rescue this page</button>
                  )}
                  <a className="text-[11px] text-ochre-dark hover:underline text-center" href={authUrl(`/api/rescue/samples/${s.id}/file`)} download>
                    Download image
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <h2 className="font-semibold text-brand mb-2">Documents</h2>
      {!docs ? <Loading /> : docs.length === 0 ? (
        <div className="card p-4 text-sm text-brand/70">No documents yet.</div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full">
            <thead><tr><th className="th">Document</th><th className="th">Source & licence</th><th className="th">Pages</th><th className="th">Facts</th><th className="th">Added</th></tr></thead>
            <tbody>
              {docs.map((d) => {
                const counts = d.pages.reduce((a, p) => {
                  for (const [k, v] of Object.entries(p.fact_counts)) a[k] = (a[k] || 0) + v;
                  return a;
                }, {} as Record<string, number>);
                const first = d.pages.find((p) => p.processed)?.page_no ?? 1;
                return (
                  <tr key={d.id} className="hover:bg-sand/50">
                    <td className="td"><Link className="font-semibold text-brand hover:text-ochre" to={`/rescue/${d.id}?page=${first}`}>{d.title}</Link>
                      <div className="text-[11px] text-brand/50">{d.original_filename}</div></td>
                    <td className="td text-xs">{d.source && <><div>{d.source.name}</div><div className="text-brand/60">{d.source.licence}</div><StatusBadge status={d.source.status} /></>}</td>
                    <td className="td text-xs">{d.pages.filter((p) => p.processed).length} processed / {d.page_count}</td>
                    <td className="td text-xs">{counts.pending || 0} to review · {(counts.approved || 0) + (counts.edited || 0)} approved · {counts.rejected || 0} rejected</td>
                    <td className="td text-xs whitespace-nowrap">{fmtDate(d.created_at)}<div className="text-brand/50">by {d.uploaded_by}</div></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function UploadForm({ onDone, setBusy, setError }: { onDone: (id: string) => void; setBusy: (s: string | null) => void; setError: (s: string | null) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [f, setF] = useState({ source_name: "", publisher: "", url: "", licence: "", permission: false, notes: "", pages: "1" });
  const ready = file && f.source_name && f.publisher && f.licence && f.permission;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    for (const [k, v] of Object.entries(f)) form.append(k, k === "permission" ? (v ? "yes" : "no") : String(v));
    setBusy(`Uploading ${file.name}, enhancing and reading it…`);
    setError(null);
    try {
      const d = await api.upload<{ id: string }>("/api/rescue/upload", form);
      onDone(d.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  return (
    <form onSubmit={submit} className="card p-4 space-y-2">
      <h2 className="font-semibold text-brand flex items-center gap-2"><Icon name="upload" /> Upload a scan</h2>
      <p className="text-xs text-brand/70">PDF, PNG, JPG or TIFF. Every upload is added to the Source Registry, so tell us where it came from.</p>
      <input type="file" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff" className="text-sm" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <div className="grid grid-cols-2 gap-2">
        <div className="col-span-2"><label className="label">Title of the document *</label><input className="input" value={f.source_name} onChange={set("source_name")} placeholder="e.g. ZGS Bulletin 94, page 37" /></div>
        <div><label className="label">Publisher / holder *</label><input className="input" value={f.publisher} onChange={set("publisher")} placeholder="e.g. Zimbabwe Geological Survey" /></div>
        <div><label className="label">Where it came from</label><input className="input" value={f.url} onChange={set("url")} placeholder="URL or library reference" /></div>
        <div><label className="label">Licence / terms *</label><input className="input" value={f.licence} onChange={set("licence")} placeholder="e.g. public domain; permission by email" /></div>
        <div><label className="label">Pages to process</label><input className="input" value={f.pages} onChange={set("pages")} placeholder="1 or 1-3" /></div>
        <div className="col-span-2"><label className="label">Notes</label><input className="input" value={f.notes} onChange={set("notes")} /></div>
      </div>
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" className="mt-1 accent-ochre" checked={f.permission} onChange={(e) => setF({ ...f, permission: e.target.checked })} />
        <span>I confirm we are allowed to use this document in GeoRevive (open licence, public domain or written permission).</span>
      </label>
      <button className="btn-primary" disabled={!ready}>Upload and rescue</button>
    </form>
  );
}
