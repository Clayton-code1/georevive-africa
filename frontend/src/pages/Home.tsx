import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { Disclaimer, PageHeader } from "../components/ui";
import { NAV } from "../nav";

const DESCRIPTIONS: Record<string, string> = {
  "/sources": "Every dataset we obtained, from where, under what licence, and what still needs action.",
  "/rescue": "Upload a scanned page: clean it, read it, extract rock units, occurrences, assays and locations.",
  "/review": "Approve, edit or reject extracted facts. Only approved facts enter the geodatabase.",
  "/map": "Interactive map of the pilot area: geology, faults, known occurrences, satellite indicators, terrain and rescued facts.",
  "/prospectivity": "Rank gold targets with explainable models and see why each area scored highly - with honest validation.",
  "/claims": "Draw or enter a claim and get a plain-language PDF check for small-scale miners.",
  "/dataroom": "Share datasets with investors under access control; downloads are watermarked and logged.",
  "/audit": "Who viewed, downloaded, approved or ran what, and when.",
  "/help": "Step-by-step instructions for each role, and what each status means.",
};

export function Home() {
  const { user, meta, can } = useAuth();
  const steps = NAV.filter((n) => n.path !== "/" && (!n.permission || can(n.permission)));
  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        title={`Welcome, ${user?.display_name ?? ""}`}
        subtitle={
          <>
            GeoRevive rescues paper-based geological records and turns them into ranked, explainable exploration
            targets. Pilot area: <strong>{meta?.pilot_area.name}</strong>.
          </>
        }
      />
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {steps.map((n) => (
          <Link key={n.path} to={n.path} className="card p-4 hover:border-ochre group">
            <div className="flex items-center gap-2 text-brand">
              <span className="rounded-md bg-brand-pale p-1.5 group-hover:bg-ochre group-hover:text-white">
                <Icon name={n.icon} />
              </span>
              <span className="font-semibold">{n.label}</span>
              {n.step && <span className="ml-auto text-xs text-brand/50">Step {n.step}</span>}
            </div>
            <p className="text-sm text-brand/70 mt-2">{DESCRIPTIONS[n.path]}</p>
          </Link>
        ))}
      </div>
      {meta && (
        <div className="mt-6">
          <Disclaimer text={meta.disclaimer} />
        </div>
      )}
    </div>
  );
}
