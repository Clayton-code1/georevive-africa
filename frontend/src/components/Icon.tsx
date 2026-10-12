// Minimal inline line icons (original, no external icon set).
const PATHS: Record<string, string> = {
  home: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  database: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zm0 0v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
  scan: "M4 7V4h3M17 4h3v3M20 17v3h-3M7 20H4v-3M7 9h10M7 12h10M7 15h6",
  map: "M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2zm0 0v14m6-12v14",
  target: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm0 4a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0 4a1 1 0 1 0 0 2 1 1 0 0 0 0-2z",
  report: "M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7M9 9h3",
  lock: "M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4",
  list: "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
  help: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01",
  present: "M3 4h18v12H3zM8 20h8M12 16v4",
  chevronLeft: "M15 18l-6-6 6-6",
  chevronRight: "M9 18l6-6-6-6",
  back: "M19 12H5M12 19l-7-7 7-7",
  logout: "M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l-5-5 5-5M5 12h12",
  check: "M5 13l4 4L19 7",
  x: "M6 6l12 12M18 6L6 18",
  edit: "M4 20h4L19 9l-4-4L4 16zM14 6l4 4",
  external: "M14 4h6v6M20 4l-9 9M18 14v6H4V6h6",
  download: "M12 4v12m0 0l-5-5m5 5l5-5M4 20h16",
  upload: "M12 20V8m0 0l-5 5m5-5l5 5M4 4h16",
  layers: "M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5",
  play: "M7 4l13 8-13 8z",
  reset: "M4 4v6h6M20 20v-6h-6M5 15a7 7 0 0 0 13 2M19 9A7 7 0 0 0 6 7",
};

export function Icon({ name, size = 18, className = "" }: { name: keyof typeof PATHS | string; size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d={PATHS[name] || PATHS.help} />
    </svg>
  );
}
