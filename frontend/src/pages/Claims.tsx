import "maplibre-gl/dist/maplibre-gl.css";
import type { GeoJSONSource, Map as MlMap, MapMouseEvent } from "maplibre-gl";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, authUrl } from "../api/client";
import { Icon } from "../components/Icon";
import { Disclaimer, ErrorBox, fmtDate } from "../components/ui";
import { useAuth } from "../auth/AuthContext";
import type { LayerInfo } from "../map/layerStyle";
import { createMap, useLayerManager } from "../map/useLayerManager";

interface Report {
  id: number;
  name: string;
  username: string;
  created_at: string;
  polygon: GeoJSON.Polygon;
  summary: {
    area_ha?: number;
    district?: string | null;
    province?: string | null;
    geology?: { unit: string; class: string; share_pct: number }[];
    geology_scale?: string | null;
    occurrences?: { name: string; dist_km: number; commod1?: string }[];
    nearest_road?: { name: string; km: number } | null;
    prospectivity?: { mean?: number; max?: number; area_percentile?: number; explanation?: string; method?: string } | null;
  };
}

type Mode = "draw" | "point" | "corners";
const BASE = ["dem_hillshade", "admin_adm2", "osm_roads", "osm_places", "geology", "regional_geology", "mrds_occurrences", "prospectivity_gold"];

export function Claims() {
  const { meta } = useAuth();
  const [params] = useSearchParams();
  const [mode, setMode] = useState<Mode>(params.get("lon") ? "point" : "draw");
  const [name, setName] = useState(params.get("name") || "My claim");
  const [lat, setLat] = useState(params.get("lat") || "");
  const [lon, setLon] = useState(params.get("lon") || "");
  const [side, setSide] = useState("500");
  const [corners, setCorners] = useState("");
  const [verts, setVerts] = useState<[number, number][]>([]);
  const [closed, setClosed] = useState(false);
  const [technical, setTechnical] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [history, setHistory] = useState<Report[]>([]);
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [ready, setReady] = useState(false);
  const [layers, setLayers] = useState<LayerInfo[]>([]);
  const mgr = useLayerManager();

  const loadHistory = () => api.get<{ reports: Report[] }>("/api/claims").then((r) => setHistory(r.reports)).catch(() => undefined);
  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    api.get<{ layers: LayerInfo[]; bbox: [number, number, number, number] }>("/api/layers").then((r) => {
      setLayers(r.layers);
      if (container.current && !mapRef.current) {
        const map = createMap(container.current, r.bbox);
        mapRef.current = map;
        map.on("load", () => {
          map.addSource("draw", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addLayer({ id: "draw-fill", type: "fill", source: "draw", filter: ["==", "$type", "Polygon"], paint: { "fill-color": "#1E3A5F", "fill-opacity": 0.15 } });
          map.addLayer({ id: "draw-line", type: "line", source: "draw", paint: { "line-color": "#1E3A5F", "line-width": 2.5 } });
          map.addLayer({ id: "draw-pts", type: "circle", source: "draw", filter: ["==", "$type", "Point"], paint: { "circle-radius": 5, "circle-color": "#B7791F", "circle-stroke-color": "#fff", "circle-stroke-width": 1.5 } });
          setReady(true);
        });
      }
    }).catch((e) => setError(e.message));
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
      mgr.reset();
    };
  }, [mgr]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (async () => {
      for (const l of layers) if (BASE.includes(l.id)) await mgr.show(map, l, true).catch(() => undefined);
      // keep the drawing on top
      for (const id of ["draw-fill", "draw-line", "draw-pts"]) if (map.getLayer(id)) map.moveLayer(id);
    })();
  }, [ready, layers, mgr]);

  // geometry being edited, as GeoJSON
  const currentPolygon = useCallback((): GeoJSON.Polygon | null => {
    if (mode === "draw") return closed && verts.length >= 3 ? { type: "Polygon", coordinates: [[...verts, verts[0]]] } : null;
    if (mode === "corners") {
      const pts = corners.split(/\n+/).map((l) => l.split(/[,;\s]+/).filter(Boolean).map(Number)).filter((p) => p.length >= 2 && p.every(isFinite));
      if (pts.length < 3) return null;
      const ring = pts.map(([la, lo]) => [lo, la] as [number, number]);
      return { type: "Polygon", coordinates: [[...ring, ring[0]]] };
    }
    return null;
  }, [mode, closed, verts, corners]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const src = map.getSource("draw") as GeoJSONSource | undefined;
    const feats: GeoJSON.Feature[] = [];
    const poly = currentPolygon();
    if (poly) feats.push({ type: "Feature", properties: {}, geometry: poly });
    else if (mode === "draw" && verts.length) {
      feats.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: verts } });
      for (const v of verts) feats.push({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: v } });
    }
    if (mode === "point" && isFinite(parseFloat(lat)) && isFinite(parseFloat(lon))) {
      feats.push({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [parseFloat(lon), parseFloat(lat)] } });
    }
    if (report) feats.push({ type: "Feature", properties: {}, geometry: report.polygon });
    src?.setData({ type: "FeatureCollection", features: feats });
  }, [ready, verts, closed, mode, lat, lon, corners, report, currentPolygon]);

  useEffect(() => {
    if (mode === "point" && mapRef.current && ready && isFinite(parseFloat(lat)) && isFinite(parseFloat(lon)) && params.get("lon")) {
      mapRef.current.flyTo({ center: [parseFloat(lon), parseFloat(lat)], zoom: 12 });
    }
  }, [ready]); // eslint-disable-line react-hooks/exhaustive-deps

  const onClick = useCallback((e: MapMouseEvent) => {
    if (mode === "draw" && !closed) setVerts((v) => [...v, [e.lngLat.lng, e.lngLat.lat]]);
    if (mode === "point") {
      setLat(e.lngLat.lat.toFixed(5));
      setLon(e.lngLat.lng.toFixed(5));
    }
  }, [mode, closed]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.on("click", onClick);
    map.getCanvas().style.cursor = mode === "draw" && !closed ? "crosshair" : "";
    return () => {
      map.off("click", onClick);
    };
  }, [ready, onClick, mode, closed]);

  async function generate() {
    setBusy(true);
    setError(null);
    setReport(null);
    try {
      const body: Record<string, unknown> = { name, technical };
      if (mode === "point") {
        body.lat = parseFloat(lat);
        body.lon = parseFloat(lon);
        body.side_m = parseFloat(side);
      } else {
        const p = currentPolygon();
        if (!p) throw new Error(mode === "draw" ? "Click at least 3 corners on the map, then press Finish." : "Enter at least 3 corners (one 'latitude, longitude' per line).");
        body.polygon = p;
      }
      const r = await api.post<Report>("/api/claims", body);
      setReport(r);
      loadHistory();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const canGenerate = mode === "point" ? isFinite(parseFloat(lat)) && isFinite(parseFloat(lon)) : !!currentPolygon();

  return (
    <div className="flex h-full">
      <div className="w-80 flex-shrink-0 bg-white border-r border-sand-line overflow-y-auto p-3 space-y-3">
        <div>
          <h1 className="font-bold text-brand text-lg">Claim Check Report</h1>
          <p className="text-xs text-brand/70">A low-cost desk check of a claim: location, rocks, nearby known gold, satellite hints and the GeoRevive score - in plain language, as a PDF.</p>
        </div>
        <div>
          <label className="label">Claim name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex gap-1">
          {([["draw", "Draw on map"], ["point", "Enter coordinates"], ["corners", "Paste corners"]] as [Mode, string][]).map(([m, l]) => (
            <button key={m} onClick={() => setMode(m)} className={`btn flex-1 px-1 py-1 text-xs ${mode === m ? "bg-brand text-white" : "bg-white border border-sand-line text-brand"}`}>{l}</button>
          ))}
        </div>
        {mode === "draw" && (
          <div className="text-xs space-y-2">
            <p>Click the corners of the claim on the map ({verts.length} so far), then press Finish.</p>
            <div className="flex gap-1">
              <button className="btn-primary py-1 text-xs" disabled={verts.length < 3 || closed} onClick={() => setClosed(true)}>Finish</button>
              <button className="btn-ghost py-1 text-xs" disabled={!verts.length || closed} onClick={() => setVerts((v) => v.slice(0, -1))}>Undo</button>
              <button className="btn-ghost py-1 text-xs" onClick={() => { setVerts([]); setClosed(false); }}>Clear</button>
            </div>
          </div>
        )}
        {mode === "point" && (
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div><label className="label">Latitude</label><input className="input" value={lat} onChange={(e) => setLat(e.target.value)} placeholder="-17.75" /></div>
            <div><label className="label">Longitude</label><input className="input" value={lon} onChange={(e) => setLon(e.target.value)} placeholder="31.20" /></div>
            <div className="col-span-2"><label className="label">Square claim, side (m)</label><input className="input" value={side} onChange={(e) => setSide(e.target.value)} /></div>
            <p className="col-span-2 text-brand/60">Or click the map to set the centre.</p>
          </div>
        )}
        {mode === "corners" && (
          <div className="text-xs">
            <label className="label">Corners: one “latitude, longitude” per line</label>
            <textarea className="input h-28 font-mono" value={corners} onChange={(e) => setCorners(e.target.value)} placeholder={"-17.750, 31.200\n-17.750, 31.210\n-17.760, 31.210\n-17.760, 31.200"} />
          </div>
        )}
        <label className="flex items-center gap-2 text-xs"><input type="checkbox" className="accent-ochre" checked={technical} onChange={(e) => setTechnical(e.target.checked)} /> Include technical appendix</label>
        <button className="btn-accent w-full" onClick={generate} disabled={!canGenerate || busy}>
          <Icon name="report" size={14} /> {busy ? "Preparing report…" : "Generate PDF report"}
        </button>
        <ErrorBox error={error} />
        {meta && <Disclaimer text={meta.disclaimer} />}
        {history.length > 0 && (
          <div>
            <div className="label">Previous reports</div>
            <ul className="text-xs space-y-1">
              {history.slice(0, 8).map((h) => (
                <li key={h.id} className="flex items-center gap-2">
                  <a className="text-ochre-dark hover:underline truncate" href={authUrl(`/api/claims/${h.id}/pdf`)} target="_blank" rel="noreferrer">{h.name}</a>
                  <span className="text-brand/50 whitespace-nowrap ml-auto">{fmtDate(h.created_at)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <div className="flex-1 relative min-w-0">
        <div ref={container} className="absolute inset-0" />
        <div className="absolute right-0 bottom-0 max-w-[80%] bg-white/90 text-[10px] text-brand/80 px-2 py-0.5 rounded-tl">
          {[...new Set(layers.filter((l) => BASE.includes(l.id)).map((l) => l.attribution))].join(" · ")}
        </div>
        {report && (
          <div className="absolute top-3 left-3 w-96 card p-3 shadow-lg text-sm space-y-1.5">
            <div className="flex items-center justify-between">
              <div className="font-bold text-brand">{report.name}</div>
              <button className="btn-ghost px-1" onClick={() => setReport(null)}><Icon name="x" size={12} /></button>
            </div>
            <div className="text-xs text-brand/70">{report.summary.area_ha} ha · {report.summary.district ?? "—"} district, {report.summary.province ?? "—"}</div>
            {report.summary.geology?.[0] && <div className="text-xs"><strong>Main rock:</strong> {report.summary.geology[0].unit} - {report.summary.geology[0].class} ({report.summary.geology_scale})</div>}
            <div className="text-xs"><strong>Known occurrences within 5 km:</strong> {report.summary.occurrences?.length ?? 0}</div>
            {report.summary.prospectivity?.mean != null && (
              <div className="text-xs"><strong>Prospectivity:</strong> average {Math.round(report.summary.prospectivity.mean)} / 100 (higher than {Math.round(report.summary.prospectivity.area_percentile ?? 0)}% of the area)
                {report.summary.prospectivity.explanation && <div className="text-brand/70 mt-0.5">{report.summary.prospectivity.explanation}</div>}
              </div>
            )}
            <a className="btn-primary w-full mt-1" href={authUrl(`/api/claims/${report.id}/pdf`)} target="_blank" rel="noreferrer"><Icon name="download" size={14} /> Open the PDF report</a>
            <p className="text-[10px] text-brand/50">The PDF is watermarked with your name and the time.</p>
          </div>
        )}
      </div>
    </div>
  );
}
