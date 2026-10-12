import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, authUrl } from "../api/client";
import { FACT_TYPE_COLOUR, FACT_TYPE_LABEL, type DocumentInfo, type Fact, type PageDetail, type Quality } from "../api/rescueTypes";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { ErrorBox, Loading, StatusBadge } from "../components/ui";

const STEP_LABEL: Record<string, string> = {
  original: "Original scan",
  stain_reduction: "1 Stain reduction",
  deskew: "2 Deskew",
  denoise: "3 Denoise",
  illumination: "4 Illumination correction",
  clahe: "5 Contrast (CLAHE)",
  binarize: "6 Binarised for OCR",
};

type Mode = "compare" | "after" | "before" | "step";

export function RescuePage() {
  const { docId } = useParams();
  const [params, setParams] = useSearchParams();
  const pageNo = Number(params.get("page") || 1);
  const focusFact = Number(params.get("fact") || 0) || null;
  const { can } = useAuth();
  const [doc, setDoc] = useState<DocumentInfo | null>(null);
  const [page, setPage] = useState<PageDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<Mode>("compare");
  const [step, setStep] = useState("illumination");
  const [selected, setSelected] = useState<number | null>(focusFact);
  const [filter, setFilter] = useState<string>("all");

  const loadDoc = useCallback(() => {
    api.get<DocumentInfo>(`/api/rescue/documents/${docId}`).then(setDoc).catch((e) => setError(e.message));
  }, [docId]);
  useEffect(loadDoc, [loadDoc]);

  const pageSummary = doc?.pages.find((p) => p.page_no === pageNo);
  useEffect(() => {
    setPage(null);
    if (pageSummary?.processed) {
      api.get<PageDetail>(`/api/rescue/pages/${pageSummary.id}`).then(setPage).catch((e) => setError(e.message));
    }
  }, [pageSummary?.id, pageSummary?.processed]);

  async function processPage() {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/api/rescue/documents/${docId}/pages/${pageNo}/process`);
      loadDoc();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const onReviewed = (f: Fact) => setPage((p) => (p ? { ...p, facts: p.facts.map((x) => (x.id === f.id ? f : x)) } : p));

  if (error && !doc) return <div className="p-6"><ErrorBox error={error} /></div>;
  if (!doc) return <Loading />;

  const facts = (page?.facts || []).filter((f) => filter === "all" || f.status === filter || f.type === filter);
  const sel = page?.facts.find((f) => f.id === selected) || null;

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 bg-white border-b border-sand-line flex items-center gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="font-bold text-brand truncate">{doc.title}</div>
          <div className="text-[11px] text-brand/60 truncate">
            {doc.source?.name} · {doc.source?.licence} {doc.source && <StatusBadge status={doc.source.status} />}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2 text-sm">
          <button className="btn-ghost px-2" disabled={pageNo <= 1} onClick={() => setParams({ page: String(pageNo - 1) })}><Icon name="chevronLeft" size={14} /></button>
          <span>Page {pageNo} of {doc.page_count}</span>
          <button className="btn-ghost px-2" disabled={pageNo >= doc.page_count} onClick={() => setParams({ page: String(pageNo + 1) })}><Icon name="chevronRight" size={14} /></button>
        </div>
      </div>
      <ErrorBox error={error} />
      {!pageSummary?.processed ? (
        <div className="p-6">
          <div className="card p-4 max-w-md">
            <p className="text-sm text-brand mb-3">Page {pageNo} has not been processed yet.</p>
            {can("rescue.upload") ? (
              <button className="btn-primary" disabled={busy} onClick={processPage}>{busy ? "Processing…" : "Enhance and read this page"}</button>
            ) : <p className="text-xs text-brand/60">Ask an analyst or geologist to process it.</p>}
          </div>
        </div>
      ) : !page ? <Loading label="Loading page…" /> : (
        <div className="flex-1 flex min-h-0">
          {/* image side */}
          <div className="flex-1 flex flex-col min-w-0 border-r border-sand-line">
            <div className="flex items-center gap-1 px-3 py-1.5 bg-sand border-b border-sand-line flex-wrap">
              {(["compare", "before", "after", "step"] as Mode[]).map((m) => (
                <button key={m} onClick={() => setMode(m)} className={`btn px-2 py-1 text-xs ${mode === m ? "bg-brand text-white" : "bg-white border border-sand-line text-brand"}`}>
                  {m === "compare" ? "Before / after" : m === "before" ? "Original" : m === "after" ? "Enhanced" : "Each step"}
                </button>
              ))}
              {mode === "step" && (
                <select className="input w-auto py-0.5 text-xs ml-2" value={step} onChange={(e) => setStep(e.target.value)}>
                  {page.steps.map((s) => <option key={s.name} value={s.name}>{STEP_LABEL[s.name] || s.name}</option>)}
                </select>
              )}
              <QualityBadges before={page.quality_before} after={page.quality_after} engine={page.ocr_engine} />
            </div>
            <div className="flex-1 overflow-auto bg-[#d9d2c2] p-2">
              {mode === "compare" ? (
                <div className="grid grid-cols-2 gap-2">
                  <PageImage page={page} step="original" label="Before: original scan" />
                  <PageImage page={page} step="clahe" label="After: enhanced (illumination-corrected)" highlight={sel} facts={page.facts} onPick={setSelected} />
                </div>
              ) : (
                <PageImage
                  page={page}
                  step={mode === "before" ? "original" : mode === "after" ? "clahe" : step}
                  label={mode === "before" ? "Original scan (unchanged)" : mode === "after" ? "Enhanced" : STEP_LABEL[step]}
                  highlight={mode === "before" ? null : sel}
                  facts={mode === "before" ? [] : page.facts}
                  onPick={setSelected}
                />
              )}
            </div>
            {sel && (
              <div className="px-3 py-1.5 text-xs bg-white border-t border-sand-line">
                <span className="font-semibold">Text around this fact:</span> <span className="italic">“{sel.context}”</span>
              </div>
            )}
          </div>

          {/* facts side */}
          <div className="w-[26rem] flex-shrink-0 flex flex-col min-h-0 bg-white">
            <div className="px-3 py-2 border-b border-sand-line">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-brand">Extracted facts ({page.facts.length})</h2>
                {can("facts.review") ? <span className="text-[11px] text-emerald-700 font-semibold">You can approve, edit or reject</span>
                  : <span className="text-[11px] text-brand/60">Read-only (geologists review)</span>}
              </div>
              <select className="input mt-1 py-1 text-xs" value={filter} onChange={(e) => setFilter(e.target.value)}>
                <option value="all">All facts</option>
                <option value="pending">To review</option>
                <option value="approved">Approved</option>
                <option value="edited">Edited</option>
                <option value="rejected">Rejected</option>
                {[...new Set(page.facts.map((f) => f.type))].map((t) => <option key={t} value={t}>{FACT_TYPE_LABEL[t] || t}</option>)}
              </select>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
              {facts.length === 0 && <p className="text-sm text-brand/60 p-2">No facts match.</p>}
              {facts.map((f) => (
                <FactCard key={f.id} f={f} selected={f.id === selected} onSelect={() => setSelected(f.id === selected ? null : f.id)}
                  canReview={can("facts.review")} onReviewed={onReviewed} />
              ))}
            </div>
            <div className="px-3 py-1.5 border-t border-sand-line text-[11px] text-brand/60">
              Only approved or edited facts with a location enter the geodatabase and the <Link to="/map?layer=rescued_facts" className="text-ochre-dark hover:underline">Rescued facts map layer</Link>.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function QualityBadges({ before, after, engine }: { before: Quality; after: Quality; engine: string | null }) {
  const conf = (q: Quality) => (q.ocr_mean_conf == null ? "—" : `${Math.round(q.ocr_mean_conf * 100)}%`);
  const better = (a: number, b: number) => (b > a + 0.005 ? "text-emerald-700" : b < a - 0.005 ? "text-amber-700" : "text-brand");
  return (
    <div className="ml-auto flex items-center gap-2 text-[11px]" title="Quality (0-100) combines local ink-to-paper contrast, evenness of lighting and paper noise. A page that was already clean will not improve much - that is expected. OCR confidence is the engine's mean word confidence on the enhanced page.">
      <span className="rounded bg-white border border-sand-line px-1.5 py-0.5">Quality <strong>{before.overall}</strong> → <strong className={better(before.overall, after.overall)}>{after.overall}</strong></span>
      <span className="rounded bg-white border border-sand-line px-1.5 py-0.5">Ink contrast {before.contrast.toFixed(2)} → <strong className={better(before.contrast, after.contrast)}>{after.contrast.toFixed(2)}</strong></span>
      <span className="rounded bg-white border border-sand-line px-1.5 py-0.5">Evenness {before.uniformity.toFixed(2)} → <strong className={better(before.uniformity, after.uniformity)}>{after.uniformity.toFixed(2)}</strong></span>
      <span className="rounded bg-white border border-sand-line px-1.5 py-0.5">OCR conf. <strong>{conf(after)}</strong> ({after.ocr_words ?? 0} words)</span>
      <span className="text-brand/50">{engine}</span>
    </div>
  );
}

function PageImage({ page, step, label, highlight, facts = [], onPick }: {
  page: PageDetail; step: string; label?: string; highlight?: Fact | null; facts?: Fact[]; onPick?: (id: number) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!highlight || !box.current) return;
    const el = box.current.querySelector(`[data-fact="${highlight.id}"]`);
    el?.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
  }, [highlight]);
  return (
    <div className="bg-white rounded shadow-sm">
      {label && <div className="text-[11px] font-semibold text-brand px-2 py-1 border-b border-sand-line">{label}</div>}
      <div ref={box} className="relative">
        <img src={authUrl(`/api/rescue/pages/${page.id}/image/${step}`)} alt={label} className="block w-full h-auto select-none" draggable={false} />
        <svg viewBox={`0 0 ${page.width} ${page.height}`} className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
          {facts.map((f) => {
            const [x, y, w, h] = f.bbox;
            const on = highlight?.id === f.id;
            const c = FACT_TYPE_COLOUR[f.type] || "#B7791F";
            return (
              <rect key={f.id} data-fact={f.id} x={x - 4} y={y - 4} width={w + 8} height={h + 8} rx={4}
                fill={on ? `${c}55` : "transparent"} stroke={c} strokeWidth={on ? 6 : 2} strokeOpacity={on ? 1 : 0.45}
                className="cursor-pointer" onClick={() => onPick?.(f.id)}>
                <title>{FACT_TYPE_LABEL[f.type] || f.type}: {f.value}</title>
              </rect>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

function describeNorm(f: Fact): string | null {
  const n = f.normalized as Record<string, unknown>;
  if (f.type === "assay" && n.g_per_t != null && n.unit !== "g/t") return `≈ ${n.g_per_t} g/t${n.assumption ? ` (assumes ${n.assumption})` : ""}`;
  if (f.type === "assay" && n.element) return `element: ${n.element}`;
  if (f.type === "coordinate") return [n.lat != null ? `lat ${n.lat}` : null, n.lon != null ? `lon ${n.lon}` : null].filter(Boolean).join(", ");
  if (f.type === "location_desc") return `${n.distance_km} km, bearing ${n.bearing_deg}° from ${n.place}`;
  if (f.type === "drillhole" && n.depth_m != null) return `depth ${n.depth_m} m`;
  if ((f.type === "rock_unit" || f.type === "lithology") && n.class) return `class: ${n.class === "host" ? "favourable host rock" : n.class}`;
  return null;
}

function FactCard({ f, selected, onSelect, canReview, onReviewed }: {
  f: Fact; selected: boolean; onSelect: () => void; canReview: boolean; onReviewed: (f: Fact) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ value: f.value, units: f.units || "", lon: f.lon?.toString() || "", lat: f.lat?.toString() || "", comment: "" });
  const [err, setErr] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (selected) ref.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selected]);
  const colour = FACT_TYPE_COLOUR[f.type] || "#B7791F";
  const norm = useMemo(() => describeNorm(f), [f]);

  async function act(action: "approve" | "reject" | "edit") {
    setErr(null);
    try {
      const body: Record<string, unknown> = { action, comment: form.comment };
      if (action === "edit") {
        body.value = form.value;
        body.units = form.units || null;
        if (form.lon && form.lat) {
          body.lon = Number(form.lon);
          body.lat = Number(form.lat);
        }
      }
      const r = await api.post<Fact>(`/api/rescue/facts/${f.id}/review`, body);
      onReviewed(r);
      setEditing(false);
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  const statusCls = { pending: "bg-gray-100 text-gray-700", approved: "bg-emerald-100 text-emerald-800", edited: "bg-sky-100 text-sky-800", rejected: "bg-red-100 text-red-700 line-through" }[f.status];
  return (
    <div ref={ref} onClick={onSelect}
      className={`rounded-md border p-2 cursor-pointer transition-colors ${selected ? "border-ochre bg-ochre/10" : "border-sand-line hover:bg-sand/60"}`}>
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded text-white" style={{ background: colour }}>
          {FACT_TYPE_LABEL[f.type] || f.type}
        </span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded ${statusCls}`}>{f.status}</span>
        <span className="ml-auto flex items-center gap-1 text-[10px] text-brand/70" title="Confidence: rule specificity × OCR word confidence">
          <span className="inline-block w-12 h-1.5 bg-sand-dark rounded overflow-hidden">
            <span className="block h-full" style={{ width: `${Math.round(f.confidence * 100)}%`, background: f.confidence > 0.75 ? "#2f855a" : f.confidence > 0.5 ? "#B7791F" : "#c53030" }} />
          </span>
          {Math.round(f.confidence * 100)}%
        </span>
      </div>
      <div className="mt-1 font-semibold text-brand">{f.value}{f.units && f.type !== "coordinate" ? <span className="text-brand/60 font-normal"> ({f.units})</span> : null}</div>
      {norm && <div className="text-[11px] text-brand/70">{norm}</div>}
      <div className="text-[11px] mt-0.5">
        {f.lon != null ? (
          <span className={f.location_uncertain ? "text-amber-700" : "text-emerald-700"}>
            {f.location_uncertain ? "⚠ Location uncertain: " : "Located: "}{f.geocode_method}
          </span>
        ) : <span className="text-brand/50">Not located{f.geocode_method && f.geocode_method !== "not located" ? ` (${f.geocode_method})` : ""} - add coordinates with Edit</span>}
      </div>
      {selected && (
        <div className="mt-1 text-[10px] text-brand/50">Method: {f.method} · page box {f.bbox.join(", ")}</div>
      )}
      {selected && f.reviews.length > 0 && (
        <div className="mt-1 text-[10px] text-brand/60">
          {f.reviews.map((r, i) => <div key={i}>{r.action} by {r.username} {new Date(r.at).toLocaleString("en-GB")}{r.comment ? ` - “${r.comment}”` : ""}</div>)}
        </div>
      )}
      {selected && canReview && (
        <div className="mt-2" onClick={(e) => e.stopPropagation()}>
          {editing ? (
            <div className="space-y-1">
              <div className="grid grid-cols-2 gap-1">
                <input className="input py-1 text-xs col-span-2" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} placeholder="Value" />
                <input className="input py-1 text-xs" value={form.units} onChange={(e) => setForm({ ...form, units: e.target.value })} placeholder="Units" />
                <input className="input py-1 text-xs" value={form.comment} onChange={(e) => setForm({ ...form, comment: e.target.value })} placeholder="Comment" />
                <input className="input py-1 text-xs" value={form.lat} onChange={(e) => setForm({ ...form, lat: e.target.value })} placeholder="Latitude (e.g. -17.8)" />
                <input className="input py-1 text-xs" value={form.lon} onChange={(e) => setForm({ ...form, lon: e.target.value })} placeholder="Longitude (e.g. 31.1)" />
              </div>
              <div className="flex gap-1">
                <button className="btn-primary py-1 text-xs" onClick={() => act("edit")}>Save edit</button>
                <button className="btn-ghost py-1 text-xs" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </div>
          ) : (
            <div className="flex gap-1">
              <button className="btn py-1 text-xs bg-emerald-700 text-white hover:bg-emerald-800" onClick={() => act("approve")}><Icon name="check" size={12} /> Approve</button>
              <button className="btn-ghost py-1 text-xs" onClick={() => setEditing(true)}><Icon name="edit" size={12} /> Edit</button>
              <button className="btn py-1 text-xs bg-red-700 text-white hover:bg-red-800" onClick={() => act("reject")}><Icon name="x" size={12} /> Reject</button>
            </div>
          )}
          {err && <div className="text-[11px] text-red-700 mt-1">{err}</div>}
        </div>
      )}
    </div>
  );
}
