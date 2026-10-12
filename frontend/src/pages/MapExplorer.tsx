import "maplibre-gl/dist/maplibre-gl.css";
import type { Map as MlMap, MapMouseEvent } from "maplibre-gl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { Icon } from "../components/Icon";
import { ErrorBox, Loading, StatusBadge, fmtDate } from "../components/ui";
import { LegendItem } from "../map/Legend";
import { GROUP_ORDER, type LayerInfo } from "../map/layerStyle";
import { createMap, useLayerManager } from "../map/useLayerManager";

const DEFAULT_ON = ["dem_hillshade", "admin_adm2", "geology", "regional_geology", "faults", "mrds_occurrences", "osm_roads", "rescued_facts"];

interface Selection {
  layer: LayerInfo;
  properties: Record<string, unknown>;
  lngLat: [number, number];
  rasterValue?: { value: number | null; label: string } | null;
}

export function MapExplorer() {
  const [params] = useSearchParams();
  const focus = params.get("layer");
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [layers, setLayers] = useState<LayerInfo[] | null>(null);
  const [bbox, setBbox] = useState<[number, number, number, number] | null>(null);
  const [visible, setVisible] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [sel, setSel] = useState<Selection | null>(null);
  const [ready, setReady] = useState(false);
  const mgr = useLayerManager();

  useEffect(() => {
    api
      .get<{ layers: LayerInfo[]; bbox: [number, number, number, number] }>("/api/layers")
      .then((r) => {
        setLayers(r.layers);
        setBbox(r.bbox);
        const ids = new Set(r.layers.map((l) => l.id));
        const on = new Set(DEFAULT_ON.filter((id) => ids.has(id)));
        if (focus && ids.has(focus)) on.add(focus);
        setVisible(on);
      })
      .catch((e) => setError(e.message));
  }, [focus]);

  // create the map once we know the pilot bbox
  useEffect(() => {
    if (!bbox || !container.current || mapRef.current) return;
    const map = createMap(container.current, bbox);
    mapRef.current = map;
    map.on("load", () => setReady(true));
    return () => {
      map.remove();
      mapRef.current = null;
      mgr.reset();
      setReady(false);
    };
  }, [bbox, mgr]);

  // sync visibility. A newer run (the user ticked/unticked while data was loading) cancels the older one,
  // so a stale run can never re-show a layer that has since been switched off.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !layers) return;
    let cancelled = false;
    (async () => {
      for (const l of layers) {
        if (cancelled) return;
        try {
          await mgr.show(map, l, visible.has(l.id));
        } catch (e) {
          if (!cancelled) setError(`Could not load ${l.name}: ${(e as Error).message}`);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [visible, ready, layers, mgr]);

  const onClick = useCallback(
    async (e: MapMouseEvent) => {
      const map = mapRef.current;
      if (!map || !layers) return;
      const ids = mgr.interactiveIds(map);
      const feats = ids.length ? map.queryRenderedFeatures(e.point, { layers: ids }) : [];
      if (feats.length) {
        const f = feats[0];
        const info = mgr.layerForMlId(f.layer.id);
        if (info) {
          setSel({ layer: info, properties: f.properties as Record<string, unknown>, lngLat: [e.lngLat.lng, e.lngLat.lat] });
          return;
        }
      }
      // otherwise sample the top visible raster with values
      const rasters = layers.filter((l) => l.kind === "raster" && visible.has(l.id) && l.group !== "base" && l.id !== "s2_true_colour");
      const top = rasters[rasters.length - 1];
      if (top) {
        try {
          const v = await api.get<{ value: number | null; label: string }>(
            `/api/layers/${top.id}/value?lon=${e.lngLat.lng}&lat=${e.lngLat.lat}`,
          );
          setSel({ layer: top, properties: {}, lngLat: [e.lngLat.lng, e.lngLat.lat], rasterValue: v });
        } catch {
          setSel(null);
        }
      } else setSel(null);
    },
    [layers, visible, mgr],
  );

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    map.on("click", onClick);
    return () => {
      map.off("click", onClick);
    };
  }, [ready, onClick]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const move = (e: MapMouseEvent) => {
      const ids = mgr.interactiveIds(map);
      const hit = ids.length > 0 && map.queryRenderedFeatures(e.point, { layers: ids }).length > 0;
      map.getCanvas().style.cursor = hit ? "pointer" : "";
    };
    map.on("mousemove", move);
    return () => {
      map.off("mousemove", move);
    };
  }, [ready, mgr]);

  const toggle = (id: string) =>
    setVisible((v) => {
      const n = new Set(v);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const grouped = useMemo(() => {
    const g: Record<string, LayerInfo[]> = {};
    for (const l of layers || []) (g[l.group] ||= []).push(l);
    return g;
  }, [layers]);

  const visibleLayers = (layers || []).filter((l) => visible.has(l.id));
  const attributions = [...new Set(visibleLayers.map((l) => l.attribution).filter(Boolean))];

  if (error && !layers) return <div className="p-6"><ErrorBox error={error} /></div>;
  if (!layers) return <Loading label="Loading map layers…" />;

  return (
    <div className="flex h-full">
      {/* layer panel */}
      <div className="w-64 flex-shrink-0 border-r border-sand-line bg-white overflow-y-auto">
        <div className="px-3 py-2 border-b border-sand-line">
          <h1 className="font-bold text-brand">Map Explorer</h1>
          <p className="text-[11px] text-brand/60">Tick layers to show them. Click any feature for its attributes and source.</p>
        </div>
        {layers.length === 0 && (
          <div className="p-3 text-sm text-brand/70">No layers yet. Run ingestion first (README step 4).</div>
        )}
        {GROUP_ORDER.filter((g) => grouped[g.id]?.length).map((g) => (
          <div key={g.id} className="px-3 py-2 border-b border-sand-line/60">
            <div className="label">{g.label}</div>
            {grouped[g.id].map((l) => (
              <label key={l.id} className="flex items-start gap-2 py-0.5 text-sm cursor-pointer" title={l.description}>
                <input type="checkbox" className="mt-1 accent-ochre" checked={visible.has(l.id)} onChange={() => toggle(l.id)} />
                <span className={`leading-snug ${focus === l.id ? "font-semibold text-ochre-dark" : ""}`}>{l.name}</span>
              </label>
            ))}
          </div>
        ))}
        {error && <div className="p-3"><ErrorBox error={error} /></div>}
      </div>

      {/* map */}
      <div className="flex-1 relative min-w-0">
        <div ref={container} className="absolute inset-0" />
        {visibleLayers.length > 0 && (
          <div className="absolute left-2 bottom-10 w-56 max-h-[45%] overflow-y-auto card p-2 text-xs shadow-md">
            <div className="label">Legend</div>
            {[...visibleLayers].reverse().map((l) => <LegendItem key={l.id} info={l} />)}
          </div>
        )}
        <div className="absolute right-0 bottom-0 max-w-[70%] bg-white/90 text-[10px] text-brand/80 px-2 py-0.5 rounded-tl">
          {attributions.length ? attributions.join(" · ") : "No layers shown"}
        </div>
      </div>

      {/* selection panel */}
      {sel && (
        <div className="w-80 flex-shrink-0 border-l border-sand-line bg-white overflow-y-auto">
          <div className="flex items-center justify-between px-3 py-2 border-b border-sand-line">
            <div className="font-semibold text-brand text-sm">{sel.layer.name}</div>
            <button className="btn-ghost px-1.5" onClick={() => setSel(null)} title="Close"><Icon name="x" size={14} /></button>
          </div>
          <div className="p-3 text-xs space-y-3">
            <div className="text-brand/60">{sel.lngLat[1].toFixed(5)}, {sel.lngLat[0].toFixed(5)}</div>
            {sel.rasterValue && (
              <div className="text-sm"><span className="label">Value at this point</span>{sel.rasterValue.label}</div>
            )}
            {Object.keys(sel.properties).length > 0 && (
              <table className="w-full">
                <tbody>
                  {Object.entries(sel.properties)
                    .filter(([k, v]) => k !== "_fid" && v !== null && v !== "" && v !== "null")
                    .map(([k, v]) => (
                      <tr key={k} className="border-b border-sand-line/60">
                        <td className="py-1 pr-2 font-semibold text-brand/70 align-top">{k}</td>
                        <td className="py-1 break-words">{
                          typeof v === "string" && v.startsWith("http") ? (
                            <a href={v} target="_blank" rel="noreferrer" className="text-ochre-dark hover:underline break-all">{v}</a>
                          ) : String(v)
                        }</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
            <SourceBox layer={sel.layer} properties={sel.properties} />
          </div>
        </div>
      )}
    </div>
  );
}

function SourceBox({ layer, properties }: { layer: LayerInfo; properties: Record<string, unknown> }) {
  const s = layer.source;
  const docLink = properties["document_id"] && properties["page_no"]
    ? `/rescue/${properties["document_id"]}?page=${properties["page_no"]}&fact=${properties["fact_id"] ?? ""}`
    : null;
  return (
    <div className="rounded-md bg-sand p-2 space-y-1">
      <div className="label">Source</div>
      <div className="font-semibold text-brand">{s.name}</div>
      <div>{s.publisher}</div>
      <div>Licence: {s.licence}</div>
      <div>Accessed: {fmtDate(s.accessed_at)}</div>
      <div><StatusBadge status={layer.source_status} /></div>
      <a href={s.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-ochre-dark hover:underline break-all">
        <Icon name="external" size={12} /> {s.url}
      </a>
      {docLink && (
        <Link to={docLink} className="flex items-center gap-1 text-ochre-dark hover:underline font-semibold">
          <Icon name="scan" size={12} /> Open the original scanned page
        </Link>
      )}
      <Link to="/sources" className="block text-brand/70 hover:underline">See this source in the Data Sources registry</Link>
    </div>
  );
}
