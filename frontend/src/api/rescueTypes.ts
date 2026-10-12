import type { Source } from "./types";

export interface Quality {
  contrast: number;
  sharpness: number;
  uniformity: number;
  noise?: number;
  overall: number;
  ocr_mean_conf?: number | null;
  ocr_words?: number;
}

export interface FactReview {
  username: string;
  action: string;
  at: string;
  comment: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}

export interface Fact {
  id: number;
  page_id: number;
  type: string;
  value: string;
  units: string | null;
  normalized: Record<string, unknown>;
  context: string;
  bbox: [number, number, number, number];
  confidence: number;
  method: string;
  lon: number | null;
  lat: number | null;
  geocode_method: string | null;
  location_uncertain: boolean;
  status: "pending" | "approved" | "rejected" | "edited";
  reviews: FactReview[];
  document_id?: string;
  document_title?: string;
  page_no?: number;
}

export interface PageSummary {
  id: number;
  document_id: string;
  page_no: number;
  width: number;
  height: number;
  processed: boolean;
  ocr_engine: string | null;
  quality_before: Quality;
  quality_after: Quality;
  steps: { name: string; params: Record<string, unknown>; info: Record<string, unknown> }[];
  fact_counts: Record<string, number>;
}

export interface PageDetail extends PageSummary {
  facts: Fact[];
  ocr_text: string | null;
  document: { id: string; title: string; page_count: number };
  source: Source | null;
}

export interface DocumentInfo {
  id: string;
  title: string;
  original_filename: string;
  page_count: number;
  uploaded_by: string;
  created_at: string;
  sha256: string;
  source: Source | null;
  pages: PageSummary[];
}

export interface Sample {
  id: string;
  title: string;
  source_id: string;
  source_name: string;
  page: number;
  licence: string;
  url: string;
  description: string;
}

export const FACT_TYPE_LABEL: Record<string, string> = {
  rock_unit: "Rock unit",
  lithology: "Rock type",
  commodity: "Mineral occurrence",
  mineral: "Mineral",
  fault: "Fault / shear",
  structure: "Structure",
  assay: "Assay",
  coordinate: "Coordinates",
  grid_ref: "Grid reference",
  location_desc: "Location description",
  drillhole: "Drill hole",
  mine: "Mine / claim",
  farm: "Farm",
};

export const FACT_TYPE_COLOUR: Record<string, string> = {
  rock_unit: "#2f855a",
  lithology: "#38a169",
  commodity: "#B7791F",
  mineral: "#c05621",
  fault: "#b91c1c",
  structure: "#9b2c2c",
  assay: "#6b46c1",
  coordinate: "#1E3A5F",
  grid_ref: "#2c5282",
  location_desc: "#2b6cb0",
  drillhole: "#4a5568",
  mine: "#975a16",
  farm: "#744210",
};
