import type { LayerInfo } from "./layerStyle";
import { colourFor } from "./layerStyle";

function fmt(v: number | undefined): string {
  if (v == null || !isFinite(v)) return "";
  const a = Math.abs(v);
  return a >= 100 ? v.toFixed(0) : a >= 1 ? v.toFixed(2) : v.toFixed(3);
}

export function LegendItem({ info, categories }: { info: LayerInfo; categories?: string[] }) {
  const lg = info.legend || {};
  const st = info.style as Record<string, unknown>;
  return (
    <div className="mb-2 last:mb-0">
      <div className="text-xs font-semibold text-brand leading-tight">{info.name}</div>
      {lg.type === "continuous" && lg.colors && (
        <div>
          <div className="h-2.5 rounded mt-1" style={{ background: `linear-gradient(to right, ${lg.colors.join(",")})` }} />
          <div className="flex justify-between text-[10px] text-brand/70">
            <span>{fmt(lg.min)}{lg.unit ? ` ${lg.unit}` : ""} low</span>
            <span>high {fmt(lg.max)}{lg.unit ? ` ${lg.unit}` : ""}</span>
          </div>
        </div>
      )}
      {lg.type === "categorical" && lg.items && (
        <div className="mt-1 space-y-0.5">
          {lg.items.slice(0, 8).map((it, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[11px]">
              <span className="inline-block w-3 h-3 rounded-sm border border-black/10" style={{ background: it.color }} />
              {it.label ?? it.value}
            </div>
          ))}
        </div>
      )}
      {!lg.type && categories && categories.length > 0 && (
        <div className="mt-1 space-y-0.5 max-h-24 overflow-y-auto">
          {categories.slice(0, 12).map((c) => (
            <div key={c} className="flex items-center gap-1.5 text-[11px]">
              <span className="inline-block w-3 h-3 rounded-sm" style={{ background: colourFor(c) }} />
              {c}
            </div>
          ))}
        </div>
      )}
      {!lg.type && !categories?.length && (
        <div className="flex items-center gap-1.5 text-[11px] mt-0.5">
          {st.type === "line" ? (
            <span className="inline-block w-5 h-0.5" style={{ background: (st.color as string) || "#1E3A5F" }} />
          ) : (
            <span className="inline-block w-3 h-3 rounded-full border border-white" style={{ background: (st.color as string) || "#1E3A5F" }} />
          )}
          {info.feature_count != null ? `${info.feature_count.toLocaleString()} features` : ""}
        </div>
      )}
      {lg.note && <div className="text-[10px] text-brand/60 mt-0.5">{lg.note}</div>}
    </div>
  );
}
