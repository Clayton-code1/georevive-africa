import maplibregl, { type Map as MlMap } from "maplibre-gl";
import { useCallback, useMemo, useRef } from "react";
import { api, authUrl } from "../api/client";
import { GROUP_ORDER, vectorLayers, type LayerInfo } from "./layerStyle";

// Draw order (bottom -> top) by group and geometry
const GROUP_RANK: Record<string, number> = {
  base: 0, terrain: 1, satellite: 2, prospectivity: 3, geology: 4, context: 5, structure: 6, occurrences: 7, rescued: 8,
};

function rank(info: LayerInfo): number {
  const g = GROUP_RANK[info.group] ?? 5;
  const geomBoost = info.kind === "raster" ? 0 : info.geometry_type?.includes("Point") ? 0.6 : info.geometry_type?.includes("Line") ? 0.4 : 0.2;
  // base vectors (boundaries) sit above all rasters
  if (info.group === "base" && info.kind === "vector") return 5.5;
  return g + geomBoost;
}

export const BLANK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "background", type: "background", paint: { "background-color": "#efe9dc" } }],
};

export function createMap(container: HTMLElement, bbox: [number, number, number, number]): MlMap {
  const map = new maplibregl.Map({
    container,
    style: BLANK_STYLE,
    bounds: [[bbox[0], bbox[1]], [bbox[2], bbox[3]]],
    fitBoundsOptions: { padding: 20 },
    attributionControl: false,
    maxZoom: 17,
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
  return map;
}

/** Adds/removes GeoRevive layers on a map in a stable draw order. */
export function useLayerManager() {
  const added = useRef<Map<string, { info: LayerInfo; mlIds: string[] }>>(new Map());
  const data = useRef<Map<string, GeoJSON.FeatureCollection>>(new Map());
  const wanted = useRef<Map<string, boolean>>(new Map()); // latest requested visibility per layer

  const beforeIdFor = useCallback((map: MlMap, info: LayerInfo): string | undefined => {
    const r = rank(info);
    let best: { r: number; id: string } | null = null;
    for (const { info: other, mlIds } of added.current.values()) {
      const ro = rank(other);
      if (ro > r && mlIds.length && map.getLayer(mlIds[0]) && (!best || ro < best.r)) best = { r: ro, id: mlIds[0] };
    }
    return best?.id;
  }, []);

  const show = useCallback(async (map: MlMap, info: LayerInfo, visible: boolean, opts?: { fc?: GeoJSON.FeatureCollection }) => {
    wanted.current.set(info.id, visible);
    const existing = added.current.get(info.id);
    if (existing) {
      for (const id of existing.mlIds) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
      if (opts?.fc) {
        const src = map.getSource(`gr-${info.id}`) as maplibregl.GeoJSONSource | undefined;
        src?.setData(opts.fc);
        data.current.set(info.id, opts.fc);
      }
      return;
    }
    if (!visible) return;
    const sid = `gr-${info.id}`;
    let mlIds: string[] = [];
    if (info.kind === "raster" && info.overlay_bounds) {
      const [w, s, e, n] = info.overlay_bounds;
      map.addSource(sid, {
        type: "image",
        url: authUrl(`/api/layers/${info.id}/overlay.png`),
        coordinates: [[w, n], [e, n], [e, s], [w, s]],
      });
      const lid = `${sid}-raster`;
      map.addLayer({ id: lid, type: "raster", source: sid, paint: { "raster-opacity": info.group === "base" ? 1 : 0.8, "raster-fade-duration": 0 } }, beforeIdFor(map, info));
      mlIds = [lid];
    } else {
      const fc = opts?.fc ?? (await api.get<GeoJSON.FeatureCollection>(`/api/layers/${info.id}/geojson`));
      data.current.set(info.id, fc);
      if (map.getSource(sid)) return; // raced with another toggle
      map.addSource(sid, { type: "geojson", data: fc });
      const field = (info.style as Record<string, unknown>).field as string | undefined;
      let cats: string[] = [];
      if (field) {
        const vals = new Set<string>();
        for (const f of fc.features) {
          const v = f.properties?.[field] ?? f.properties?.["LEX_RCS"] ?? f.properties?.["lith"];
          if (v != null) vals.add(String(v));
        }
        cats = [...vals].slice(0, 200);
      }
      const before = beforeIdFor(map, info);
      for (const spec of vectorLayers(info, sid, cats)) map.addLayer(spec, before);
      mlIds = vectorLayers(info, sid, cats).map((l) => l.id);
    }
    added.current.set(info.id, { info, mlIds });
    // The layer may have been switched off while its data was loading: apply the latest wish.
    if (wanted.current.get(info.id) === false) {
      for (const id of mlIds) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", "none");
    }
  }, [beforeIdFor]);

  const interactiveIds = useCallback((map: MlMap): string[] => {
    const ids: string[] = [];
    for (const { info, mlIds } of added.current.values()) {
      if (info.kind !== "vector") continue;
      for (const id of mlIds) if (map.getLayer(id) && map.getLayoutProperty(id, "visibility") !== "none") ids.push(id);
    }
    return ids;
  }, []);

  const layerForMlId = useCallback((mlId: string): LayerInfo | undefined => {
    for (const { info, mlIds } of added.current.values()) if (mlIds.includes(mlId)) return info;
    return undefined;
  }, []);

  const reset = useCallback(() => {
    added.current.clear();
    data.current.clear();
    wanted.current.clear();
  }, []);

  // Stable identity: pages use the manager in effect dependencies (a new object each render
  // would tear the map down and rebuild it on every render).
  return useMemo(
    () => ({ show, interactiveIds, layerForMlId, reset, data }),
    [show, interactiveIds, layerForMlId, reset],
  );
}

export function groupLabel(id: string): string {
  return GROUP_ORDER.find((g) => g.id === id)?.label ?? id;
}
