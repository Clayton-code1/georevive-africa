import { NEG_COLOUR, POS_COLOUR, type Contribution } from "../api/prospectTypes";

/** Diverging bar list: each factor's push up (ochre) or down (blue) relative to the area average. */
export function Contributions({ items, compact = false }: { items: Contribution[]; compact?: boolean }) {
  const max = Math.max(1e-9, ...items.map((c) => Math.abs(c.contribution)));
  const shown = compact ? items.filter((c) => c.contribution > 0).slice(0, 4) : items;
  return (
    <div className="space-y-1" role="table" aria-label="Factor contributions">
      {shown.map((c) => {
        const w = (Math.abs(c.contribution) / max) * 50;
        const pos = c.contribution >= 0;
        return (
          <div key={c.feature} role="row" className="grid grid-cols-[1fr_7rem] items-center gap-2 text-[11px]"
            title={`${c.label}: ${pos ? "+" : ""}${c.contribution.toFixed(3)}`}>
            <span role="cell" className="text-ink leading-tight">{c.text}</span>
            <span role="cell" className="relative h-2.5 bg-sand-dark/60 rounded">
              <span className="absolute top-0 bottom-0 left-1/2 w-px bg-brand/30" />
              <span
                className="absolute top-0 bottom-0"
                style={{
                  background: pos ? POS_COLOUR : NEG_COLOUR,
                  left: pos ? "50%" : `${50 - w}%`,
                  width: `${w}%`,
                  borderRadius: pos ? "0 4px 4px 0" : "4px 0 0 4px",
                }}
              />
            </span>
          </div>
        );
      })}
      {!compact && (
        <div className="flex gap-3 text-[10px] text-brand/60 pt-0.5">
          <span className="flex items-center gap-1"><span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: POS_COLOUR }} /> raises the score</span>
          <span className="flex items-center gap-1"><span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: NEG_COLOUR }} /> lowers the score</span>
          <span>(relative to the area average)</span>
        </div>
      )}
    </div>
  );
}
