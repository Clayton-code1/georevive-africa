import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { POS_COLOUR } from "../api/prospectTypes";

/** Success-rate curve: share of known occurrences captured vs share of area ranked most prospective. */
export function SuccessCurve({ data }: { data: { area: number; captured: number }[] }) {
  if (!data.length) return <p className="text-xs text-brand/60">No validation curve (no known occurrences in the area).</p>;
  const rows = data.map((d) => ({ area: Math.round(d.area * 100), model: Math.round(d.captured * 100), random: Math.round(d.area * 100) }));
  return (
    <div className="h-44">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 6, right: 10, bottom: 14, left: -12 }}>
          <CartesianGrid stroke="#e5ddca" strokeDasharray="0" vertical={false} />
          <XAxis dataKey="area" type="number" domain={[0, 100]} ticks={[0, 20, 40, 60, 80, 100]} tick={{ fontSize: 10, fill: "#4b5563" }}
            label={{ value: "% of area (highest scores first)", position: "insideBottom", offset: -6, fontSize: 10, fill: "#4b5563" }} stroke="#c9bfa8" />
          <YAxis domain={[0, 100]} ticks={[0, 50, 100]} tick={{ fontSize: 10, fill: "#4b5563" }} stroke="#c9bfa8" unit="%" />
          <Tooltip
            formatter={(v: number, name: string) => [`${v}%`, name === "model" ? "Occurrences captured" : "Random ranking"]}
            labelFormatter={(a) => `Top ${a}% of area`}
            contentStyle={{ fontSize: 11 }}
          />
          <Legend verticalAlign="top" height={18} iconType="plainline" wrapperStyle={{ fontSize: 10 }}
            formatter={(v) => (v === "model" ? "This model" : "Random (no skill)")} />
          <Line dataKey="random" stroke="#9ca3af" strokeDasharray="4 4" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          <Line dataKey="model" stroke={POS_COLOUR} strokeWidth={2} dot={false} activeDot={{ r: 4, stroke: "#fff", strokeWidth: 2 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
