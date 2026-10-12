import type { ReactNode } from "react";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-4">
      <div>
        <h1 className="text-2xl font-bold text-brand">{title}</h1>
        {subtitle && <p className="text-sm text-brand/70 mt-1 max-w-3xl">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </div>
  );
}

export const STATUS_STYLES: Record<string, { label: string; cls: string; help: string }> = {
  downloaded: {
    label: "Downloaded",
    cls: "bg-emerald-100 text-emerald-800 border-emerald-300",
    help: "Obtained and checked. Ready to use.",
  },
  partial: {
    label: "Partial",
    cls: "bg-amber-100 text-amber-800 border-amber-300",
    help: "Some of the data was obtained; see the note for what is missing.",
  },
  failed: {
    label: "Failed",
    cls: "bg-red-100 text-red-800 border-red-300",
    help: "The download failed. The reason is recorded; nothing was substituted.",
  },
  needs_manual_request: {
    label: "Needs manual request",
    cls: "bg-sky-100 text-sky-800 border-sky-300",
    help: "Not openly downloadable. Request it from the publisher (see How to obtain).",
  },
  needs_credentials: {
    label: "Needs credentials",
    cls: "bg-violet-100 text-violet-800 border-violet-300",
    help: "Free, but needs a login. Add credentials to .env and re-run ingestion.",
  },
};

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLES[status] || { label: status, cls: "bg-gray-100 text-gray-700 border-gray-300", help: "" };
  return (
    <span title={s.help} className={`inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-semibold ${s.cls}`}>
      {s.label}
    </span>
  );
}

export function Disclaimer({ text }: { text: string }) {
  return (
    <div className="rounded-md border border-ochre/40 bg-ochre/10 px-3 py-2 text-sm text-ochre-dark font-medium">
      {text}
    </div>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="p-6 text-brand/60 text-sm animate-pulse">{label}</div>;
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card px-4 py-3" title={hint}>
      <div className="text-xs uppercase tracking-wide text-brand/60 font-semibold">{label}</div>
      <div className="text-2xl font-bold text-brand mt-1">{value}</div>
    </div>
  );
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}

export function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}
