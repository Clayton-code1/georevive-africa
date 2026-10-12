import "maplibre-gl/dist/maplibre-gl.css";
import maplibregl, { type Map as MlMap, type MapMouseEvent } from "maplibre-gl";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, authUrl } from "../api/client";
import type { Contribution, ProspectConfig, RunInfo } from "../api/prospectTypes";
import { useAuth } from "../auth/AuthContext";
import { Contributions } from "../components/Contributions";
import { Icon } from "../components/Icon";
import { SuccessCurve } from "../components/SuccessCurve";
import { Disclaimer, ErrorBox, Loading } from "../components/ui";
import type { LayerInfo } from "../map/layerStyle";
import { createMap, useLayerManager } from "../map/useLayerManager";

const CONTEXT_LAYERS = ["dem_hillshade", "admin_adm2", "faults", "osm_roads"];

interface CellInfo {
  score: number | null;
  percentile?: number;
  contributions: Contribution[];
  explanation: string;
  lngLat: [number, number];
}

export function Prospectivity() {
  const { can } = useAuth();
  const [cfg, setCfg] = useState<ProspectConfig | null>(null);
  const [run, setRun] = useState<RunInfo | null>(null);
  const [method, setMethod] = useState("fuzzy");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"targets" | "validation" | "weights">("targets");
  const [selected, setSelected] = useState<number | null>(null);
  const [cell, setCell] = useState<CellInfo | null>(null);
  const [showOcc, setShowOcc] = useState(false);
  const [layers, setLayers] = useState<LayerInfo[]>([]);
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const [ready, setReady] = useState(false);
  const mgr = useLayerManager();

  useEffect(() => {
    api.get<ProspectConfig>("/api/prospect/config").then(setCfg).catch((e) => setError(e.message));
    api.get<RunInfo>("/api/prospect/runs/latest").then((r) => { setRun(r); setMethod(r.method); }).catch(() => setRun(null));
    api.get<{ layers: LayerInfo[]; bbox: [number, number, number, number] }>("/api/layers").then((r) => {
      setLayers(r.layers);
      if (container.current && !mapRef.current) {
        const map = createMap(container.current, r.bbox);
        mapRef.current = map;
        map.on("load", () => setReady(true));
      }
    }).catch((e) => setError(e.message));
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
      mgr.reset();
    };
  }, [mgr]);

  // context layers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    for (const l of layers) {
      if (CONTEXT_LAYERS.includes(l.id)) mgr.show(map, l, true).catch(() => undefined);
      if (l.id === "mrds_occurrences") mgr.show(map, l, showOcc).catch(() => undefined);
    }
  }, [ready, layers, showOcc, mgr]);

  // heat map + target markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !run) return;
    const sid = "prospect-heat";
    if (map.getLayer(sid)) map.removeLayer(sid);
    if (map.getSource(sid)) map.removeSource(sid);
    const [w, s, e, n] = run.overlay_bounds;
    map.addSource(sid, { type: "image", url: authUrl(`/api/prospect/runs/${run.id}/overlay.png`), coordinates: [[w, n], [e, n], [e, s], [w, s]] });
    const before = map.getStyle().layers.find((l) => l.id.startsWith("gr-admin_adm2"))?.id;
    map.addLayer({ id: sid, type: "raster", source: sid, paint: { "raster-opacity": 0.72, "raster-fade-duration": 0 } }, before);
    markers.current.forEach((m) => m.remove());
    markers.current = (run.targets || []).map((t) => {
      const el = document.createElement("button");
      el.className = "w-6 h-6 rounded-full bg-brand text-white text-[11px] font-bold border-2 border-white shadow";
      el.textContent = String(t.rank);
      el.title = `Target ${t.rank} - score ${t.score}`;
      el.onclick = (ev) => {
        ev.stopPropagation();
        setSelected(t.rank);
        setTab("targets");
        setCell(null);
      };
      return new maplibregl.Marker({ element: el }).setLngLat([t.lon, t.lat]).addTo(map);
    });
  }, [ready, run]);

  const onClick = useCallback(async (e: MapMouseEvent) => {
    if (!run) return;
    try {
      const r = await api.get<Omit<CellInfo, "lngLat">>(`/api/prospect/runs/${run.id}/cell?lon=${e.lngLat.lng}&lat=${e.lngLat.lat}`);
      setCell({ ...r, lngLat: [e.lngLat.lng, e.lngLat.lat] });
      setSelected(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [run]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.on("click", onClick);
    return () => {
      map.off("click", onClick);
    };
  }, [ready, onClick]);

  useEffect(() => {
    const t = run?.targets?.find((x) => x.rank === selected);
    if (t && mapRef.current) mapRef.current.flyTo({ center: [t.lon, t.lat], zoom: Math.max(mapRef.current.getZoom(), 11), duration: 600 });
  }, [selected, run]);

  async function runModel() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.post<RunInfo>("/api/prospect/run", { method, commodity: "gold" });
      setRun(r);
      setSelected(1);
      setTab("targets");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !cfg) return <div className="p-6"><ErrorBox error={error} /></div>;
  if (!cfg) return <Loading />;
  const attributions = [...new Set(layers.filter((l) => CONTEXT_LAYERS.includes(l.id) || (showOcc && l.id === "mrds_occurrences")).map((l) => l.attribution))];

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 bg-white border-b border-sand-line flex items-center gap-3 flex-wrap">
        <h1 className="font-bold text-brand">Prospectivity - gold</h1>
        <select className="input w-auto py-1 text-sm" value={method} onChange={(e) => setMethod(e.target.value)} title={cfg.methods.find((m) => m.id === method)?.description}>
          {cfg.methods.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
        </select>
        {can("model.run") && (
          <button className="btn-accent" onClick={runModel} disabled={busy}>
            <Icon name="play" size={14} /> {busy ? "Running…" : "Run model for gold"}
          </button>
        )}
        {run && <span className="text-xs text-brand/60">Showing run {run.id} ({run.method}) by {run.username}, {new Date(run.created_at).toLocaleString("en-GB")}</span>}
        <label className="ml-auto flex items-center gap-1.5 text-xs">
          <input type="checkbox" className="accent-ochre" checked={showOcc} onChange={(e) => setShowOcc(e.target.checked)} />
          Show known occurrences (validation only)
        </label>
      </div>
      <div className="px-4 pt-2"><Disclaimer text={cfg.disclaimer} /></div>
      {error && <div className="px-4 pt-2"><ErrorBox error={error} /></div>}
      <div className="flex-1 flex min-h-0 pt-2">
        <div className="flex-1 relative min-w-0">
          <div ref={container} className="absolute inset-0" />
          {!run && <div className="absolute inset-0 flex items-center justify-center pointer-events-none"><div className="card p-4 text-sm text-brand pointer-events-auto">No model run yet. Choose a method and press <strong>Run model for gold</strong>.</div></div>}
          {run && (
            <div className="absolute left-2 bottom-10 card p-2 w-48 text-[11px]">
              <div className="font-semibold text-brand">Relative prospectivity</div>
              <div className="h-2.5 rounded mt-1" style={{ background: "linear-gradient(to right,#ffffcc,#feb24c,#fd8d3c,#e31a1c,#800026)" }} />
              <div className="flex justify-between text-brand/70"><span>lower</span><span>higher</span></div>
              <div className="mt-1 flex items-center gap-1"><span className="w-4 h-4 rounded-full bg-brand text-white text-[9px] flex items-center justify-center">1</span> ranked target</div>
              <div className="text-brand/60 mt-1">Click anywhere for that cell's explanation.</div>
            </div>
          )}
          <div className="absolute right-0 bottom-0 max-w-[80%] bg-white/90 text-[10px] text-brand/80 px-2 py-0.5 rounded-tl">
            Prospectivity: GeoRevive prototype · {attributions.join(" · ")}
          </div>
        </div>
        <div className="w-[27rem] flex-shrink-0 flex flex-col min-h-0 bg-white border-l border-sand-line">
          <div className="flex border-b border-sand-line">
            {(["targets", "validation", "weights"] as const).map((t) => (
              <button key={t} onClick={() => setTab(t)} className={`flex-1 py-2 text-sm font-semibold ${tab === t ? "text-ochre-dark border-b-2 border-ochre" : "text-brand/60"}`}>
                {t === "targets" ? "Top 10 targets" : t === "validation" ? "Validation" : "Evidence & weights"}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {cell && (
              <div className="card p-2 mb-3 border-ochre">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-brand text-sm">Cell at {cell.lngLat[1].toFixed(4)}, {cell.lngLat[0].toFixed(4)}</div>
                  <button className="btn-ghost px-1" onClick={() => setCell(null)}><Icon name="x" size={12} /></button>
                </div>
                {cell.score == null ? <p className="text-xs">{cell.explanation}</p> : (
                  <>
                    <div className="text-xs text-brand/70">Score {cell.score} / 100 · higher than {cell.percentile}% of the area</div>
                    <p className="text-xs mt-1">{cell.explanation}</p>
                    <div className="mt-2"><Contributions items={cell.contributions} /></div>
                  </>
                )}
              </div>
            )}
            {tab === "targets" && (run ? <TargetList run={run} selected={selected} onSelect={setSelected} /> : <p className="text-sm text-brand/60">Run the model to see ranked targets.</p>)}
            {tab === "validation" && (run ? <Validation run={run} /> : <p className="text-sm text-brand/60">Run the model to see validation metrics.</p>)}
            {tab === "weights" && <Weights cfg={cfg} canEdit={can("model.edit_weights")} onSaved={(w) => setCfg({ ...cfg, weights: w })} />}
          </div>
        </div>
      </div>
    </div>
  );
}

function TargetList({ run, selected, onSelect }: { run: RunInfo; selected: number | null; onSelect: (n: number) => void }) {
  return (
    <div className="space-y-2">
      {(run.targets || []).map((t) => (
        <div key={t.rank} onClick={() => onSelect(t.rank)} className={`rounded-md border p-2 cursor-pointer ${selected === t.rank ? "border-ochre bg-ochre/10" : "border-sand-line hover:bg-sand/50"}`}>
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-brand text-white text-xs font-bold flex items-center justify-center">{t.rank}</span>
            <span className="font-semibold text-brand">Score {t.score}</span>
            <span className="text-[11px] text-brand/60">{t.context.district ? `${t.context.district} district · ` : ""}{t.lat.toFixed(4)}, {t.lon.toFixed(4)}</span>
          </div>
          <p className="text-xs mt-1 text-ink">{t.explanation}</p>
          {selected === t.rank && (
            <div className="mt-2">
              <Contributions items={t.contributions} />
              <div className="mt-2 flex gap-2">
                <Link to={`/claims?lon=${t.lon}&lat=${t.lat}&name=Target%20${t.rank}`} className="btn-ghost py-1 text-xs"><Icon name="report" size={12} /> Claim check report here</Link>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Validation({ run }: { run: RunInfo }) {
  const m = run.metrics;
  const pct = (v?: number | null) => (v == null ? "—" : `${Math.round(v * 100)}%`);
  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-3 gap-2">
        <div className="card p-2"><div className="label">AUC</div><div className="text-xl font-bold text-brand">{m.auc == null ? "—" : m.auc.toFixed(2)}</div></div>
        <div className="card p-2"><div className="label">Top 10% area</div><div className="text-xl font-bold text-brand">{pct(m.captured_top10pct)}</div><div className="text-[10px] text-brand/60">of known occurrences</div></div>
        <div className="card p-2"><div className="label">Top 20% area</div><div className="text-xl font-bold text-brand">{pct(m.captured_top20pct)}</div><div className="text-[10px] text-brand/60">of known occurrences</div></div>
      </div>
      <p className="text-xs text-brand/70">{m.validation} {m.auc_note}</p>
      {m.fold_aucs && m.fold_aucs.length > 0 && <p className="text-xs">AUC per held-out spatial fold: {m.fold_aucs.join(", ")}</p>}
      <p className="text-xs">Known gold occurrences in the pilot area: <strong>{m.n_known_occurrences}</strong> ({m.n_positive_cells} grid cells){m.n_background ? `, ${m.n_background} random background cells` : ""}.</p>
      <div>
        <div className="label">Success-rate curve</div>
        <SuccessCurve data={m.success_rate || []} />
      </div>
      {m.coefficients && (
        <div>
          <div className="label">Logistic regression coefficients (standardised)</div>
          <table className="w-full text-xs">
            <tbody>{Object.entries(m.coefficients).map(([k, v]) => <tr key={k}><td className="py-0.5">{k}</td><td className="text-right font-mono">{v}</td></tr>)}</tbody>
          </table>
        </div>
      )}
      <div>
        <div className="label">Limitations - read before using these targets</div>
        <ul className="list-disc pl-4 text-xs space-y-1">{(m.limitations || []).map((l, i) => <li key={i}>{l}</li>)}</ul>
      </div>
    </div>
  );
}

function Weights({ cfg, canEdit, onSaved }: { cfg: ProspectConfig; canEdit: boolean; onSaved: (w: Record<string, number>) => void }) {
  const [w, setW] = useState<Record<string, number>>(cfg.weights);
  const [comment, setComment] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const avail = cfg.evidence.available;
  const total = avail.reduce((s, a) => s + (w[a.id] || 0), 0) || 1;
  async function save() {
    try {
      await api.put("/api/prospect/weights", { weights: w, comment });
      onSaved(w);
      setMsg("Saved. Run the knowledge-driven model again to apply the new weights.");
    } catch (e) {
      setMsg((e as Error).message);
    }
  }
  return (
    <div className="space-y-3 text-sm">
      <p className="text-xs text-brand/70">Evidence layers used by the models. Weights apply to the knowledge-driven (fuzzy) model and are normalised to sum to 100%. {canEdit ? "As geologist you can edit them; every change is logged." : "Only the geologist can edit weights."}</p>
      {cfg.weights_last_edited && <p className="text-[11px] text-brand/60">Last edited by {cfg.weights_last_edited.username}, {new Date(cfg.weights_last_edited.at).toLocaleString("en-GB")}{cfg.weights_last_edited.comment ? ` - “${cfg.weights_last_edited.comment}”` : ""}</p>}
      {avail.map((a) => (
        <div key={a.id} className="border border-sand-line rounded-md p-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-brand text-xs">{a.label}</span>
            <span className="text-xs font-mono">{Math.round(((w[a.id] || 0) / total) * 100)}%</span>
          </div>
          <input type="range" min={0} max={1} step={0.05} value={w[a.id] || 0} disabled={!canEdit} className="w-full accent-ochre"
            onChange={(e) => setW({ ...w, [a.id]: Number(e.target.value) })} aria-label={`Weight for ${a.label}`} />
          <div className="text-[11px] text-brand/60">{cfg.memberships[a.id]}</div>
          <div className="text-[10px] text-brand/50">From layer(s): {a.from_layers.join(", ")}</div>
          {a.note && <div className="text-[11px] text-amber-700 mt-0.5">{a.note}</div>}
        </div>
      ))}
      {cfg.evidence.unavailable.length > 0 && (
        <div>
          <div className="label">Not available (no data obtained)</div>
          <ul className="text-xs list-disc pl-4">{cfg.evidence.unavailable.map((u) => <li key={u.id}><strong>{u.label}</strong>: {u.reason}</li>)}</ul>
        </div>
      )}
      <p className="text-[11px] text-brand/60">Known occurrences are never an input: they are used only to train the data-driven models and to validate all models.</p>
      {canEdit && (
        <div className="space-y-1">
          <input className="input" placeholder="Reason for the change (logged)" value={comment} onChange={(e) => setComment(e.target.value)} />
          <div className="flex gap-2">
            <button className="btn-primary" onClick={save}>Save weights</button>
            <button className="btn-ghost" onClick={() => setW(cfg.default_weights)}>Restore defaults</button>
          </div>
        </div>
      )}
      {msg && <p className="text-xs text-emerald-700">{msg}</p>}
    </div>
  );
}
