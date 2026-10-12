// Original GeoRevive wordmark: a stylised outcrop (ochre) under a rising sun, with the name.

export function Mark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="6" fill="#1E3A5F" />
      <path d="M5 23 L12 12 L17 19 L21 14 L27 23 Z" fill="#B7791F" />
      <path d="M5 23 L27 23" stroke="#F7F3EA" strokeWidth="1.5" />
      <circle cx="22" cy="9" r="3" fill="#F7F3EA" />
    </svg>
  );
}

export function Wordmark({ collapsed = false, light = true }: { collapsed?: boolean; light?: boolean }) {
  return (
    <div className="flex items-center gap-2 select-none" aria-label="GeoRevive Africa">
      <Mark />
      {!collapsed && (
        <div className="leading-none">
          <div className={`text-lg font-bold tracking-tight ${light ? "text-white" : "text-brand"}`}>
            Geo<span className="text-ochre-light">Revive</span>
          </div>
          <div className={`text-[10px] uppercase tracking-[0.2em] ${light ? "text-sand/70" : "text-brand/60"}`}>
            Africa
          </div>
        </div>
      )}
    </div>
  );
}
