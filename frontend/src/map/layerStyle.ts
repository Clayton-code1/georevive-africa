import type { LayerSpecification } from "maplibre-gl";

export interface LayerInfo {
  id: string;
  name: string;
  group: string;
  kind: "vector" | "raster";
  geometry_type: string | null;
  feature_count: number | null;
  attribution: string;
  legend: Legend;
  style: Record<string, unknown>;
  description: string;
  overlay_bounds: [number, number, number, number] | null;
  has_overlay: boolean;
  source: { source_id: string; name: string; publisher: string; url: string; licence: string; accessed_at: string | null };
  source_status: string;
}

export interface Legend {
  type?: "continuous" | "categorical";
  min?: number;
  max?: number;
  colors?: string[];
  items?: { label?: string; value?: number; color: string }[];
  note?: string;
  unit?: string;
}

export const GROUP_ORDER: { id: string; label: string }[] = [
  { id: "prospectivity", label: "Prospectivity" },
  { id: "rescued", label: "Rescued facts" },
  { id: "occurrences", label: "Known occurrences" },
  { id: "geology", label: "Geology" },
  { id: "structure", label: "Faults & structure" },
  { id: "satellite", label: "Sentinel-2 indicators" },
  { id: "terrain", label: "Terrain (DEM)" },
  { id: "context", label: "Roads, places, rivers" },
  { id: "base", label: "Base map" },
];

// Earthy categorical palette for unit codes (original; no external palette)
const PALETTE = ["#2f855a", "#c05621", "#6b46c1", "#b7791f", "#2c7a7b", "#9b2c2c", "#4a5568", "#d69e2e", "#38a169",
  "#805ad5", "#dd6b20", "#319795", "#e53e3e", "#718096", "#975a16", "#276749"];

export function colourFor(value: string): string {
  let h = 0;
  for (let i = 0; i < value.length; i++) h = (h * 31 + value.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

/** Build MapLibre layer specs for a vector layer from its stored style. */
export function vectorLayers(info: LayerInfo, sourceId: string, categories: string[] = []): LayerSpecification[] {
  const st = info.style as Record<string, unknown>;
  const type = (st.type as string) || (info.geometry_type?.includes("Point") ? "circle" : info.geometry_type?.includes("Line") ? "line" : "fill");
  const color = (st.color as string) || "#1E3A5F";
  if (type === "fill") {
    const field = st.field as string | undefined;
    const colors = (st.colors as Record<string, string>) || {};
    let fillColor: unknown = color;
    if (field && categories.length) {
      const pairs: unknown[] = [];
      for (const c of categories) pairs.push(c, colors[c] || colourFor(c));
      fillColor = ["match", ["to-string", ["get", field]], ...pairs, (st.default as string) || "#d6cfc0"];
    }
    return [
      { id: `${sourceId}-fill`, type: "fill", source: sourceId, paint: { "fill-color": fillColor as never, "fill-opacity": (st.opacity as number) ?? 0.5 } },
      { id: `${sourceId}-outline`, type: "line", source: sourceId, paint: { "line-color": "#4b5563", "line-width": 0.4 } },
    ];
  }
  if (type === "line") {
    return [{
      id: `${sourceId}-line`, type: "line", source: sourceId,
      paint: {
        "line-color": color,
        "line-width": (st.width as number) ?? 1.2,
        ...(st.dash ? { "line-dasharray": [3, 2] } : {}),
      },
    }];
  }
  const hl = st.highlight_field as string | undefined;
  const circleColor: unknown = hl ? ["case", ["==", ["to-number", ["get", hl]], 1], color, "#9ca3af"] : color;
  // Text labels need glyph files from a server, so for offline use names are shown in the click panel instead.
  return [{
    id: `${sourceId}-circle`, type: "circle", source: sourceId,
    paint: {
      "circle-color": circleColor as never,
      "circle-radius": (st.radius as number) ?? 4,
      "circle-stroke-color": (st.stroke as string) || "#ffffff",
      "circle-stroke-width": 1,
    },
  }];
}
