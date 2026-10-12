export interface Contribution {
  feature: string;
  label: string;
  contribution: number;
  text: string;
  weight: number | null;
}

export interface TargetInfo {
  id: number;
  rank: number;
  lon: number;
  lat: number;
  score: number;
  polygon: GeoJSON.Polygon;
  contributions: Contribution[];
  context: { known_within_km?: number; nearest_known_km?: number; radius_km?: number; district?: string | null };
  explanation: string;
}

export interface EvidenceSummary {
  available: { id: string; label: string; unit: string; from_layers: string[]; note?: string | null }[];
  unavailable: { id: string; label: string; reason: string }[];
  grid: { cell_size_m: number; width: number; height: number; crs: string };
}

export interface RunInfo {
  id: number;
  commodity: string;
  method: string;
  weights: Record<string, number>;
  metrics: {
    auc?: number | null;
    fold_aucs?: number[];
    auc_note?: string;
    validation?: string;
    success_rate?: { area: number; captured: number }[];
    captured_top10pct?: number | null;
    captured_top20pct?: number | null;
    n_known_occurrences?: number;
    n_positive_cells?: number;
    n_background?: number;
    coefficients?: Record<string, number>;
    limitations?: string[];
    evidence?: EvidenceSummary;
  };
  username: string;
  created_at: string;
  overlay_bounds: [number, number, number, number];
  disclaimer: string;
  targets?: TargetInfo[];
}

export interface ProspectConfig {
  evidence: EvidenceSummary;
  weights: Record<string, number>;
  default_weights: Record<string, number>;
  weights_last_edited: { username: string; at: string; comment: string } | null;
  memberships: Record<string, string>;
  labels: Record<string, string>;
  methods: { id: string; label: string; description: string }[];
  disclaimer: string;
}

// Validated (dataviz validator, light surface): raises score / lowers score
export const POS_COLOUR = "#C0841F";
export const NEG_COLOUR = "#4A7DB5";
