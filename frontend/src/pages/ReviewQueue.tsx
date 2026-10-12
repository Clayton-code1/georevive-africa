import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { FACT_TYPE_COLOUR, FACT_TYPE_LABEL, type Fact } from "../api/rescueTypes";
import { ErrorBox, Loading, PageHeader, Stat } from "../components/ui";

export function ReviewQueue() {
  const [data, setData] = useState<{ counts: Record<string, number>; facts: Fact[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.get<{ counts: Record<string, number>; facts: Fact[] }>("/api/rescue/queue").then(setData).catch((e) => setError(e.message));
  }, []);
  if (error) return <div className="p-6"><ErrorBox error={error} /></div>;
  if (!data) return <Loading />;
  const c = data.counts;
  return (
    <div className="p-6">
      <PageHeader title="Review Queue" subtitle="Facts waiting for the geologist. Open a fact to see it highlighted on its page, then approve, edit or reject it. Every decision is logged." />
      <div className="grid grid-cols-4 gap-3 mb-4">
        <Stat label="To review" value={c.pending ?? 0} />
        <Stat label="Approved" value={c.approved ?? 0} />
        <Stat label="Edited" value={c.edited ?? 0} />
        <Stat label="Rejected" value={c.rejected ?? 0} />
      </div>
      {data.facts.length === 0 ? <div className="card p-4 text-sm text-brand/70">Nothing waiting for review.</div> : (
        <div className="card overflow-x-auto">
          <table className="w-full">
            <thead><tr><th className="th">Fact</th><th className="th">Confidence</th><th className="th">Location</th><th className="th">Document</th><th className="th"></th></tr></thead>
            <tbody>
              {data.facts.map((f) => (
                <tr key={f.id} className="hover:bg-sand/50">
                  <td className="td">
                    <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded text-white mr-2" style={{ background: FACT_TYPE_COLOUR[f.type] || "#B7791F" }}>{FACT_TYPE_LABEL[f.type] || f.type}</span>
                    <span className="font-semibold text-brand">{f.value}</span>
                  </td>
                  <td className="td text-xs">{Math.round(f.confidence * 100)}%</td>
                  <td className="td text-xs">{f.lon != null ? (f.location_uncertain ? "uncertain" : "located") : "—"}</td>
                  <td className="td text-xs">{f.document_title} · p.{f.page_no}</td>
                  <td className="td"><Link className="btn-ghost py-1 text-xs" to={`/rescue/${f.document_id}?page=${f.page_no}&fact=${f.id}`}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
