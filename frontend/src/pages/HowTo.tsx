import { Link } from "react-router-dom";
import { PageHeader, STATUS_STYLES, StatusBadge } from "../components/ui";

const ROLES: { role: string; can: string }[] = [
  { role: "Admin", can: "Everything: shares datasets in the data room, reads the audit log, resets the demo." },
  { role: "Geologist", can: "Reviews extracted facts (approve / edit / reject) and edits the prospectivity weights." },
  { role: "Analyst", can: "Sees all data, uploads scans, runs models and makes claim reports." },
  { role: "Investor", can: "Sees and downloads only the datasets shared with them (downloads are watermarked)." },
  { role: "Miner", can: "Makes claim check reports only." },
];

const SECTIONS: { title: string; link?: string; steps: string[] }[] = [
  {
    title: "Read the Data Sources page",
    link: "/sources",
    steps: [
      "Open Data Sources. The boxes at the top count datasets by status.",
      "Each row shows the dataset, its licence, when we accessed it and how much we obtained.",
      "Click a row to see the files and their SHA-256 checksums, the URLs we tried, what failed and how to obtain missing data.",
      "Use 'View on map' to see a layer on the Map Explorer.",
    ],
  },
  {
    title: "Add your own scans",
    link: "/rescue",
    steps: [
      "Open Data Rescue and choose a PDF or image in 'Upload a scan'.",
      "Enter the title, the publisher (e.g. Zimbabwe Geological Survey), where it came from, and the licence or permission (e.g. 'permission by email from ZGS, 1 Oct 2026').",
      "Tick the permission box - GeoRevive only processes documents we are allowed to use.",
      "Or drop files into the data/inbox/ folder and run ingestion with --source inbox: it asks for the same details.",
    ],
  },
  {
    title: "Review extracted facts (geologist)",
    link: "/review",
    steps: [
      "Open a document page (or the Review Queue). Click a fact: its box lights up on the page.",
      "Check the value against the page. Approve if right, Edit to correct the value, units or location, Reject if wrong.",
      "Only approved or edited facts with a location go into the geodatabase and onto the map. Every decision is logged.",
    ],
  },
  {
    title: "Use the Map Explorer",
    link: "/map",
    steps: [
      "Tick layers on the left: geology, faults, known occurrences, Sentinel-2 indices, terrain, roads and rescued facts.",
      "The legend shows what the colours mean; the bottom bar shows the attribution of every visible layer.",
      "Click any feature (or any point on a satellite/terrain layer) to see its attributes and source. Rescued facts link to their original page.",
      "The base map is local hillshade and boundaries, so it works without internet.",
    ],
  },
  {
    title: "Run and read the prospectivity model",
    link: "/prospectivity",
    steps: [
      "Choose the knowledge-driven (fuzzy) model or a data-driven model and press 'Run model for gold'.",
      "Red areas score higher. The numbered markers are the top 10 targets (at least 1.5 km apart).",
      "Click a target to read why it scored highly; bars show which factors raised or lowered the score.",
      "The Validation tab shows AUC and the success-rate curve, and lists the limitations. Known occurrences are only used to train and test, never as an input.",
      "Limits: the results are only as good as the input maps; coarse geology or missing faults weaken them. All targets need field verification by a qualified geologist.",
    ],
  },
  {
    title: "Produce a claim check report",
    link: "/claims",
    steps: [
      "Open Claim Check. Draw the claim on the map, enter a centre point, or paste corner coordinates.",
      "Press 'Generate PDF report' and open the PDF. It is watermarked with your name and the time.",
      "Read the disclaimer: the report is a desk study, not a resource estimate or a title search.",
    ],
  },
  {
    title: "Share data and read the audit log (admin)",
    link: "/dataroom",
    steps: [
      "Open Data Room and choose 'Share with…' for a dataset. Datasets whose licence is unclear ask you to confirm first.",
      "The investor then sees only those datasets; each download is a zip with a watermark and the licence.",
      "Open the Audit Log to see who viewed, downloaded, approved, shared or ran what, and when.",
    ],
  },
  {
    title: "Request missing data",
    link: "/sources",
    steps: [
      "On Data Sources, filter by 'Needs manual request' or 'Needs credentials' and open the row.",
      "Follow 'How to obtain' (contacts and steps), or read reports/DATA_SOURCES.md.",
      "When the data arrives, put it where the instructions say and re-run ingestion.",
    ],
  },
];

export function HowTo() {
  return (
    <div className="p-6 max-w-5xl">
      <PageHeader title="How to use GeoRevive" subtitle="A short version of USER_GUIDE.md. Each section has numbered steps." />
      <div className="card p-4 mb-4">
        <h2 className="font-semibold text-brand mb-2">Roles</h2>
        <table className="w-full text-sm"><tbody>
          {ROLES.map((r) => <tr key={r.role}><td className="py-1 pr-3 font-semibold text-brand w-28">{r.role}</td><td className="py-1">{r.can}</td></tr>)}
        </tbody></table>
      </div>
      <div className="card p-4 mb-4">
        <h2 className="font-semibold text-brand mb-2">What the statuses mean</h2>
        <div className="grid sm:grid-cols-2 gap-2 text-sm">
          {Object.entries(STATUS_STYLES).map(([k, v]) => <div key={k} className="flex items-start gap-2"><StatusBadge status={k} /><span>{v.help}</span></div>)}
        </div>
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        {SECTIONS.map((s) => (
          <div key={s.title} className="card p-4">
            <h2 className="font-semibold text-brand mb-2">{s.link ? <Link to={s.link} className="hover:text-ochre">{s.title}</Link> : s.title}</h2>
            <ol className="list-decimal pl-5 text-sm space-y-1">{s.steps.map((x) => <li key={x}>{x}</li>)}</ol>
          </div>
        ))}
      </div>
      <div className="card p-4 mt-4 text-sm">
        <h2 className="font-semibold text-brand mb-1">Presenter Mode</h2>
        Press <strong>Presenter</strong> in the top bar. Use <kbd className="px-1 border rounded">→</kbd> for the next step,
        <kbd className="px-1 border rounded ml-1">←</kbd> to go back, <kbd className="px-1 border rounded ml-1">R</kbd> to reset the demo,
        <kbd className="px-1 border rounded ml-1">Esc</kbd> to minimise the guide. 'Load complete' jumps to the finished end state if something fails live.
      </div>
    </div>
  );
}
